import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL

from .const import DOMAIN, CONF_USER_ID, CONF_COOKIE, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN
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

                config = {
                    CONF_EMAIL: email,
                    CONF_ACCESS_TOKEN: data["access_token"],
                    CONF_REFRESH_TOKEN: data["refresh_token"],
                    CONF_USER_ID: data["user_id"],
                    CONF_COOKIE:  data["cookie"]
                }

                return self.async_create_entry(title=f"TGTG {email}", data=config)

            except Exception as e:
                errors["base"] = "Error: {}".format(e)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str
            }),
            errors=errors
        )