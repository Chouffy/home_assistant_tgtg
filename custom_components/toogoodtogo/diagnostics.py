"""TGTG Diagnostics."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_EMAIL
from homeassistant.core import HomeAssistant

from .const import CONF_REFRESH_TOKEN, CONF_COOKIE

REDACTED_FIELDS = [
    CONF_EMAIL,
    CONF_ACCESS_TOKEN,
    CONF_COOKIE,
    CONF_REFRESH_TOKEN
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Get diagnostics for a config entry."""
    return {
        "config_entry": async_redact_data(config_entry.data, REDACTED_FIELDS),
        "options": async_redact_data(config_entry.options, REDACTED_FIELDS),
        "coordinator": {
            "items": config_entry.runtime_data.items,
            "item_ids": config_entry.runtime_data.item_ids,
            "tgtg_orders": config_entry.runtime_data.tgtg_orders,
            "item_id_set": config_entry.runtime_data.item_id_set,
        }
    }
