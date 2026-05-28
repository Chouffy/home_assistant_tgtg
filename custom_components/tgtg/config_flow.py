"""Too Good To Go config flow."""

import asyncio
import datetime
import logging
import time
from http import HTTPStatus
from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_ACCESS_TOKEN

from tgtg import (
    AUTH_POLLING_ENDPOINT,
    MAX_POLLING_TRIES,
    POLLING_WAIT_TIME,
    TgtgAPIError,
    TgtgClient,
    TgtgLoginError,
    TgtgPollingError,
)

from .const import DOMAIN, CONF_COOKIE, CONF_REFRESH_TOKEN, CONF_ITEM_IDS

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
        )
    }
)

ITEM_IDS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ITEM_IDS): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[],
                custom_value=True,
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    }
)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Represent a TGTG config flow."""

    VERSION = 1
    MINOR_VERSION = 0
    _config = {}
    _login_task = None
    _tgtg = None

    def _tgtg_start_polling_without_pin(self, polling_id: str):
        """Use non-interactive polling auth because Home Assistant has no stdin."""
        for _ in range(MAX_POLLING_TRIES):
            response = self._tgtg._post(
                self._tgtg._get_url(AUTH_POLLING_ENDPOINT),
                json={
                    "device_type": self._tgtg.device_type,
                    "email": self._tgtg.email,
                    "request_polling_id": polling_id,
                },
            )
            if response.status_code == HTTPStatus.ACCEPTED:
                time.sleep(POLLING_WAIT_TIME)
                continue
            if response.status_code == HTTPStatus.OK:
                login_response = response.json()
                self._tgtg.access_token = login_response["access_token"]
                self._tgtg.refresh_token = login_response["refresh_token"]
                self._tgtg.last_time_token_refreshed = datetime.datetime.now()
                self._tgtg.cookie = response.headers["Set-Cookie"]
                return
            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                raise TgtgAPIError(response.status_code, "Too many requests. Try again later.")
            raise TgtgLoginError(response.status_code, response.content)

        raise TgtgPollingError(
            f"Max retries ({MAX_POLLING_TRIES * POLLING_WAIT_TIME} seconds) reached. Try again."
        )

    async def _tgtg_login(self):
        """Handled in the background to check the login status."""
        while True:
            await self.hass.async_add_executor_job(self._tgtg.login)
            if self._tgtg.access_token is not None:
                break
            await asyncio.sleep(5)  # attempt to prevent captcha

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Initial config flow step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()
            self._config = user_input
            self._tgtg = TgtgClient(email=user_input[CONF_EMAIL])
            self._tgtg.start_polling = self._tgtg_start_polling_without_pin
            return await self.async_step_login()
        return self.async_show_form(
            step_id="user", data_schema=LOGIN_SCHEMA, errors=errors
        )

    async def async_step_login(self, user_input: dict[str, Any] | None = None):
        """User login step."""
        if self._login_task is None:
            ## Start login check sequence
            self._login_task = self.hass.async_create_background_task(
                self._tgtg_login(), f"Logging into account {self._config[CONF_EMAIL]}"
            )
        if self._login_task.done():
            if err := self._login_task.exception():
                _LOGGER.error("Unexpected error during login: %s", err)
                return self.async_show_progress_done(next_step_id="failed")
            return self.async_show_progress_done(next_step_id="login_complete")
        return self.async_show_progress(
            step_id="login", progress_action="login", progress_task=self._login_task
        )

    async def async_step_login_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step after login has succeeded."""
        return await self.async_step_item_ids()

    async def async_step_item_ids(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step to collect item ids."""
        errors = {}
        if user_input is not None:
            self._config[CONF_ITEM_IDS] = user_input.get(CONF_ITEM_IDS, [])
            return await self.async_step_finished()
        return self.async_show_form(
            step_id="item_ids", data_schema=ITEM_IDS_SCHEMA, errors=errors
        )

    async def async_step_finished(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step after login has succeeded."""
        self._config[CONF_ACCESS_TOKEN] = self._tgtg.access_token
        self._config[CONF_REFRESH_TOKEN] = self._tgtg.refresh_token
        self._config[CONF_COOKIE] = self._tgtg.cookie
        return self.async_create_entry(
            title=self._config[CONF_EMAIL],
            data=self._config,
        )

    async def async_step_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step after login has failed."""
        reason = "unknown_login_error"
        _exc = self._login_task.exception()
        if isinstance(_exc, TgtgLoginError):
            if _exc.args[0] == 403:
                reason = "captcha"
        return self.async_abort(reason=reason)

    async def async_step_reauth(
        self, entry_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        errors = {}
        if entry_data is not None:
            self._config = entry_data
            self._tgtg = TgtgClient(
                email=entry_data[CONF_EMAIL],
                access_token=entry_data[CONF_ACCESS_TOKEN],
                refresh_token=entry_data[CONF_REFRESH_TOKEN],
                cookie=entry_data[CONF_COOKIE],
            )
            self._tgtg.start_polling = self._tgtg_start_polling_without_pin
            return await self.async_step_login()
        return self.async_show_form(
            step_id="reauth",
            data_schema=self.add_suggested_values_to_schema(LOGIN_SCHEMA, entry_data),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import configuration from YAML."""
        _LOGGER.info("Importing TGTG configuration from YAML")

        # Email is required for import
        if CONF_EMAIL not in import_data or not import_data[CONF_EMAIL]:
            _LOGGER.error("Cannot import YAML config without email")
            return self.async_abort(reason="import_missing_email")

        # Check if already configured
        await self.async_set_unique_id(import_data[CONF_EMAIL])
        self._abort_if_unique_id_configured()

        # Create config entry with imported data
        # Token validation is skipped - if expired, reauth flow will handle it
        return self.async_create_entry(
            title=f"{import_data[CONF_EMAIL]} (imported)",
            data={
                CONF_EMAIL: import_data[CONF_EMAIL],
                CONF_ACCESS_TOKEN: import_data[CONF_ACCESS_TOKEN],
                CONF_REFRESH_TOKEN: import_data[CONF_REFRESH_TOKEN],
                CONF_COOKIE: import_data[CONF_COOKIE],
                CONF_ITEM_IDS: import_data.get(CONF_ITEM_IDS, []),
            },
        )
