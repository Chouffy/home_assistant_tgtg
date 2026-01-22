"""Update coordinator for tgtg."""

import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
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

# Rate limiting delay between API calls (in seconds)
API_RATE_LIMIT_DELAY = 1.0

# Minutes after sales window start to use frequent polling
SALES_WINDOW_POLLING_MINUTES = 10

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
        try:
            await self.hass.async_add_executor_job(self._tgtg.login)
        except (TgtgLoginError, TgtgAPIError) as err:
            _LOGGER.error("Login failed, triggering reauth: %s", err)
            raise ConfigEntryAuthFailed("Login failed, reauthentication required") from err
        return await super()._async_setup()

    async def _fetch_all_favorites(self) -> list:
        """Fetch ALL pages of favorites, not just the first page."""
        all_items = []
        page = 1
        while True:
            _LOGGER.debug("Fetching favorites page %d", page)
            items = await self.hass.async_add_executor_job(
                partial(self._tgtg.get_items, page=page)
            )
            if not items:
                break
            all_items.extend(items)
            page += 1
            # Rate limiting between page fetches
            await asyncio.sleep(API_RATE_LIMIT_DELAY)
        _LOGGER.info("Fetched %d total favorites across %d pages", len(all_items), page - 1)
        return all_items

    def _is_during_sales_window(self, item: dict) -> bool:
        """Check if item is currently in its sales window."""
        if "next_sales_window_purchase_start" not in item:
            return False

        try:
            current_time = datetime.now(timezone.utc)
            sales_window_str = item["next_sales_window_purchase_start"]
            sales_window = datetime.fromisoformat(sales_window_str.replace("Z", "+00:00"))
            window_end = sales_window + timedelta(minutes=SALES_WINDOW_POLLING_MINUTES)
            return sales_window <= current_time <= window_end
        except (ValueError, TypeError) as err:
            _LOGGER.debug("Error parsing sales window: %s", err)
            return False

    def _any_item_in_sales_window(self) -> bool:
        """Check if any item is currently in its sales window."""
        if not self.items:
            return False
        return any(self._is_during_sales_window(item) for item in self.items)

    async def _async_update_data(self):
        """Update data."""
        try:
            # Fetch all favorites with pagination
            self.items = await self._fetch_all_favorites()
            self.item_id_set = {item["item"]["item_id"] for item in self.items}

            # Fetch any additional configured item IDs not in favorites
            for item_id in self.item_ids:
                if self.has_item(item_id):
                    continue
                try:
                    item = await self.hass.async_add_executor_job(
                        self._tgtg.get_item, item_id
                    )
                    self.items.append(item)
                    self.item_id_set.add(item_id)
                except TgtgAPIError as err:
                    _LOGGER.warning("Failed to fetch item %s: %s", item_id, err)
                await asyncio.sleep(API_RATE_LIMIT_DELAY)

            # Fetch active orders (non-critical, don't fail if this errors)
            await asyncio.sleep(API_RATE_LIMIT_DELAY)
            try:
                orders_response = await self.hass.async_add_executor_job(self._tgtg.get_active)
                self.tgtg_orders = orders_response.get("orders", [])
            except TgtgAPIError as err:
                _LOGGER.warning("Failed to fetch orders: %s", err)
                self.tgtg_orders = []

            # Reset error counter on success
            self._consecutive_api_errors = 0

            # Smart polling: more frequent updates during sales windows
            if self._any_item_in_sales_window():
                self.update_interval = timedelta(minutes=3)
                _LOGGER.debug("Item in sales window, using 3-minute polling interval")
            else:
                self.update_interval = timedelta(minutes=DEFAULT_SCAN_INTERVAL)

            return True
        except TgtgLoginError as err:
            _LOGGER.error("Error during login: %s", err)
            raise ConfigEntryAuthFailed() from err
        except TgtgAPIError as err:
            self._consecutive_api_errors += 1
            if err.args[0] == 403 and "://captcha-delivery.com" in str(err.args[1]):
                if self._consecutive_api_errors > 4:
                    raise UpdateFailed(translation_key="too_many_requests") from err
                _LOGGER.warning("Too many API requests, delaying updates for 1 hour.")
                self.update_interval = timedelta(hours=1)
                return True
            _LOGGER.error("Error during API request: %s", err)
            raise UpdateFailed(translation_key="api_error") from err
