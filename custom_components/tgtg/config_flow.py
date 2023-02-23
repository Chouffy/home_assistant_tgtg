import voluptuous as vol
import logging
import json

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers.selector import selector

from .const import DOMAIN, CONF_FAVOURITES, CONF_USER_ID, CONF_COOKIE, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, CONF_ITEM, CONF_ITEM_ID
from .client import Client

LOGGER = logging.getLogger(__name__)

class TGTGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """TGTG config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]

            # use email as unique_id
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()

            try:
                # Get credentials
                tgtg = Client(hass=self.hass, email=email)
                data = await tgtg.fetch_credentials()

                credentials = {
                    CONF_EMAIL: email,
                    CONF_ACCESS_TOKEN: data["access_token"],
                    CONF_REFRESH_TOKEN: data["refresh_token"],
                    CONF_USER_ID: data["user_id"],
                    CONF_COOKIE:  data["cookie"]
                }

                return self.async_create_entry(title=f"TGTG {email}", data=credentials)

            except Exception as e:
                errors["base"] = "Error: {}".format(e)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL, default="manuel.richarz.tgtgtest@nysoft.de"): str
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    def map_favourites_for_selector(self, item):
        return {
            "label": item["display_name"],
            "value": item[CONF_ITEM][CONF_ITEM_ID]
        }

    async def async_step_init(self, user_input=None):
        errors = {}
        """Manage the options."""
        if not user_input:
            tgtg = Client(
                hass=self.hass,
                email=self.config_entry.data.get(CONF_EMAIL),
                access_token=self.config_entry.data.get(CONF_ACCESS_TOKEN),
                refresh_token=self.config_entry.data.get(CONF_REFRESH_TOKEN),
                user_id=self.config_entry.data.get(CONF_USER_ID),
                cookie=self.config_entry.data.get(CONF_COOKIE)
            )

            try:
                result = await tgtg.fetch_items()

                selectorValues = list(map(self.map_favourites_for_selector, result))

                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({
                        vol.Optional(CONF_FAVOURITES): selector({
                            "select": {
                                "options": selectorValues,
                                "multiple": True
                            }
                        })
                    }),
                    errors=errors)
            except Exception as e:
                statusCode, body = e.args
                if(statusCode == 403):
                    data = json.loads(body)
                    return self.async_external_step(
                        step_id="user",
                        url=data["url"],
                    )
                else:
                    errors["base"] = "Error: {}".format(e)
                    LOGGER.error(statusCode)
                    LOGGER.error(body)

        else:
            return self.async_create_entry(
                title="Selected favourites",
                data={CONF_FAVOURITES: user_input['favourites']},
            )

        return