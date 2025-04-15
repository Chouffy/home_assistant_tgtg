"""Too Good To Go config flow."""

import asyncio
import logging
import json
from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_ACCESS_TOKEN

from tgtg import TgtgClient, TgtgLoginError

from .const import DOMAIN, CONF_COOKIE, CONF_REFRESH_TOKEN, CONF_ITEM_IDS

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.EMAIL
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

    async def _tgtg_login(self):
        """Handled in the background to check the login status."""
        while True:
            await self.hass.async_add_executor_job(self._tgtg.login)
            if self._tgtg.access_token is not None:
                break
            await asyncio.sleep(5) # attempt to prevent captcha

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ):
        """Initial config flow step."""
        errors = {}
        if user_input is not None:
            self._config = user_input
            self._tgtg = TgtgClient(email=user_input[CONF_EMAIL])
            return await self.async_step_login()
        return self.async_show_form(
            step_id="user",
            data_schema=LOGIN_SCHEMA,
            errors=errors
        )

    async def async_step_captcha(
        self, user_input: dict[str, Any] | None = None
    ):
        """Captcha required step."""
        if user_input is not None:
            self._login_task = None
            return await self.async_step_login()
        return self.async_show_form(
            step_id="captcha",
            description_placeholders={
                "url": json.loads(
                    self._login_task.exception().args[1]
                ).get("url", "")
            }
        )

    async def async_step_login(
            self, user_input: dict[str, Any] | None = None
    ):
        """User login step."""
        if self._login_task is None:
            ## Start login check sequence
            self._login_task = self.hass.async_create_background_task(
                self._tgtg_login(),
                f"Logging into account {self._config[CONF_EMAIL]}"
            )
        if self._login_task.done():
            if err := self._login_task.exception():
                _LOGGER.error("Unexpected error during login: %s", err)
                return self.async_show_progress_done(next_step_id="failed")
            return self.async_show_progress_done(next_step_id="item_ids")
        return self.async_show_progress(
            step_id="login",
            progress_action="login",
            progress_task=self._login_task
        )

    async def async_step_item_ids(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step to collect item ids."""
        if user_input is not None:
            self._config[CONF_ITEM_IDS] = user_input[CONF_ITEM_IDS]
            return await self.async_step_finished()
        return self.async_show_form(
            step_id="item_ids",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ITEM_IDS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            custom_value=True,
                            mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            )
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
                return await self.async_step_captcha()
        return self.async_abort(reason=reason)
