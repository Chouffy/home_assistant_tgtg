"""The tgtg component."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import Client
from .const import (
    DOMAIN,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    CONF_COOKIE,
    TGTG_NAME,
    TGTG_CLIENT,
    TGTG_COORDINATOR,
    DEFAULT_SCAN_INTERVAL
)

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up TGTG as config entry."""

    LOGGER.info(f"Initializing {DOMAIN}")

    # Load values from settings
    email = entry.data.get(CONF_EMAIL)
    access_token = entry.data.get(CONF_ACCESS_TOKEN)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
    user_id = entry.data.get(CONF_USER_ID)
    cookie = entry.data.get(CONF_COOKIE)

    # Log in with tokens
    tgtg_client = Client(hass=hass, email=email, access_token=access_token, refresh_token=refresh_token, user_id=user_id, cookie=cookie)

    tgtg_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"{DOMAIN} Coordinator for {user_id}",
        update_method=tgtg_client.update,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    # Fetch initial data so we have data when entities subscribe
    await tgtg_coordinator.async_refresh()

    # Save the data
    tgtg_hass_data = hass.data.setdefault(DOMAIN, {})
    tgtg_hass_data[entry.entry_id] = {
        TGTG_CLIENT: tgtg_client,
        TGTG_COORDINATOR: tgtg_coordinator,
        TGTG_NAME: user_id,
    }

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)
    )

    return True
