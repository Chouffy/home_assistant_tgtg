"""Update coordinator for tgtg."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_ACCESS_TOKEN
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from tgtg import TgtgClient

from .const import CONF_COOKIE, CONF_REFRESH_TOKEN, CONF_ITEM_IDS

_LOGGER = logging.getLogger(__name__)

class TGTGUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for TGTG."""

    _tgtg: TgtgClient = None
    items: list = None
    item_ids: list = None
    tgtg_orders: dict = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Init DUC."""
        super().__init__(
            hass,
            _LOGGER,
            name="TGTG Coordinator",
            update_interval=timedelta(minutes=15),
            always_update=True
        )
        self.config_entry = entry
        self.item_ids = entry.data.get(CONF_ITEM_IDS, [])
        self._tgtg = TgtgClient(
            email=entry.data[CONF_EMAIL],
            access_token=entry.data[CONF_ACCESS_TOKEN],
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            cookie=entry.data[CONF_COOKIE]
        )

    def has_item(self, item_id) -> bool:
        """Returns true if the item has been retrieved and is in the cache."""
        for item in self.items:
            if item["item"]["item_id"] == item_id:
                return True
        return False

    async def _async_setup(self):
        """Setup and login."""
        await self.hass.async_add_executor_job(self._tgtg.login)
        return await super()._async_setup()

    async def _async_update_data(self):
        """Update data."""
        self.items = await self.hass.async_add_executor_job(self._tgtg.get_items)
        for item in self.item_ids:
            if self.has_item(item):
                continue
            self.items.append(await self.hass.async_add_executor_job(self._tgtg.get_item, item))
        self.tgtg_orders = await self.hass.async_add_executor_job(self._tgtg.get_active)
        self.tgtg_orders = self.tgtg_orders["orders"]
