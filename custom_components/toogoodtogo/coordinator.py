"""Update coordinator for tgtg."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_ACCESS_TOKEN
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from tgtg import TgtgClient, TgtgLoginError, TgtgAPIError

from .const import CONF_COOKIE, CONF_REFRESH_TOKEN, CONF_ITEM_IDS, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class TGTGUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for TGTG."""

    _consecutive_api_errors = 0
    _tgtg: TgtgClient = None
    items: list = None
    item_ids: list = None
    tgtg_orders: dict = None
    item_id_set = set()

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Init DUC."""
        super().__init__(
            hass,
            _LOGGER,
            name="TGTG Coordinator",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL),
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
        return item_id in self.item_id_set

    async def _async_setup(self):
        """Setup and login."""
        await self.hass.async_add_executor_job(self._tgtg.login)
        return await super()._async_setup()

    async def _async_update_data(self):
        """Update data."""
        try:
            self.items = await self.hass.async_add_executor_job(self._tgtg.get_items)
            self.item_id_set = {item["item"]["item_id"] for item in self.items}
            for item in self.item_ids:
                if self.has_item(item):
                    continue
                self.items.append(await self.hass.async_add_executor_job(self._tgtg.get_item, item))
                self.item_id_set.add(item)
            self.tgtg_orders = await self.hass.async_add_executor_job(self._tgtg.get_active)
            self.tgtg_orders = self.tgtg_orders["orders"]
            self._consecutive_api_errors = 0
            self.update_interval = timedelta(minutes=DEFAULT_SCAN_INTERVAL)
            return True
        except TgtgLoginError as err:
            _LOGGER.error("Error during login: %s", err)
            raise ConfigEntryAuthFailed() from err
        except TgtgAPIError as err:
            self._consecutive_api_errors += 1
            if err.args[0] == 403 and "captcha-delivery.com" in str(err.args[1]):
                if self._consecutive_api_errors > 4:
                    raise UpdateFailed(translation_key="too_many_requests") from err
                _LOGGER.warning("Too many API requests, delaying updates for 1 hour.")
                self.update_interval = timedelta(hours=1)
                return True
            _LOGGER.error("Error during API request: %s", err)
            raise UpdateFailed(translation_key="api_error") from err
