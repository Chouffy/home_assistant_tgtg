"""Update coordinator for tgtg."""

import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
import logging
from random import uniform

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from tgtg import TgtgClient, TgtgLoginError, TgtgAPIError

from .captcha import dismiss_captcha, get_captcha_url, show_captcha
from .const import (
    CONF_COOKIE,
    CONF_REFRESH_TOKEN,
    CONF_ITEM_IDS,
    CONF_SCAN_INTERVAL,
    CONF_SALES_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SALES_SCAN_INTERVAL,
    POLLING_JITTER_SECONDS,
    TGTG_USER_AGENT,
)

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
            always_update=True,
        )
        self.config_entry = entry
        self._polling_options = dict(entry.options)
        self._api_retry_after = entry.data.get("api_retry_after") or 0
        self.item_ids = entry.data.get(CONF_ITEM_IDS, [])
        self._gone_item_ids = {
            str(item_id) for item_id in (entry.data.get("gone_item_ids") or [])
        }
        self._tgtg = None
        self._set_polling_interval()

    def _set_polling_interval(self):
        minutes = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        sales_minutes = self.config_entry.options.get(
            CONF_SALES_SCAN_INTERVAL, DEFAULT_SALES_SCAN_INTERVAL
        )
        if sales_minutes and self._any_item_in_sales_window():
            minutes = sales_minutes
        self.update_interval = timedelta(
            seconds=minutes * 60
            + uniform(-POLLING_JITTER_SECONDS, POLLING_JITTER_SECONDS)
        )

    def has_item(self, item_id) -> bool:
        """Returns true if the item has been retrieved and is in the cache."""
        return item_id in self.item_id_set

    async def _async_setup(self):
        """Setup and login."""
        self._check_retry_delay()
        if self._tgtg is None:
            self._tgtg = await self.hass.async_add_executor_job(
                partial(
                    TgtgClient,
                    email=self.config_entry.data[CONF_EMAIL],
                    access_token=self.config_entry.data[CONF_ACCESS_TOKEN],
                    refresh_token=self.config_entry.data[CONF_REFRESH_TOKEN],
                    cookie=self.config_entry.data[CONF_COOKIE],
                    user_agent=TGTG_USER_AGENT,
                )
            )
        try:
            await self.hass.async_add_executor_job(self._tgtg.login)
        except TgtgLoginError as err:
            self._handle_api_error(err, login=True)
        except TgtgAPIError as err:
            self._handle_api_error(err)
        finally:
            self._save_credentials()
        dismiss_captcha(self.hass, f"tgtg_captcha_{self.config_entry.entry_id}")
        return await super()._async_setup()

    def _save_credentials(self):
        data = dict(self.config_entry.data)
        data["gone_item_ids"] = sorted(self._gone_item_ids)
        for key, value in (
            (CONF_ACCESS_TOKEN, self._tgtg.access_token),
            (CONF_REFRESH_TOKEN, self._tgtg.refresh_token),
            (CONF_COOKIE, self._tgtg.cookie),
        ):
            if value:
                data[key] = value
        if data != self.config_entry.data:
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    def _check_retry_delay(self):
        if datetime.now(timezone.utc).timestamp() < self._api_retry_after:
            retry_time = (
                datetime.fromtimestamp(self._api_retry_after, timezone.utc)
                .astimezone()
                .isoformat(timespec="minutes")
            )
            raise UpdateFailed(
                f"TGTG is paused after a CAPTCHA or rate limit until {retry_time}. "
                "It will retry automatically. To renew the session manually, "
                "open the integration menu and choose Reconfigure."
            )

    def _handle_api_error(self, err, login=False):
        status = err.args[0] if err.args else None
        captcha_url = get_captcha_url(err)
        if captcha_url:
            show_captcha(
                self.hass, captcha_url, f"tgtg_captcha_{self.config_entry.entry_id}"
            )
        if status in (403, 429):
            self._api_retry_after = datetime.now(timezone.utc).timestamp() + 3600
            self.update_interval = timedelta(hours=1)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "api_retry_after": self._api_retry_after,
                },
            )
            self._check_retry_delay()
        if status == 401 or login:
            raise ConfigEntryAuthFailed(
                "TGTG session expired; reauthentication required"
            ) from err
        raise UpdateFailed(f"TGTG API request failed (HTTP {status})") from err

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
        _LOGGER.info(
            "Fetched %d total favorites across %d pages", len(all_items), page - 1
        )
        return all_items

    def _is_during_sales_window(self, item: dict) -> bool:
        """Check if item is currently in its sales window."""
        if "next_sales_window_purchase_start" not in item:
            return False

        try:
            current_time = datetime.now(timezone.utc)
            sales_window_str = item["next_sales_window_purchase_start"]
            sales_window = datetime.fromisoformat(
                sales_window_str.replace("Z", "+00:00")
            )
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
        self._check_retry_delay()
        try:
            # Fetch all favorites with pagination
            self.items = await self._fetch_all_favorites()
            self.item_id_set = {item["item"]["item_id"] for item in self.items}

            # Fetch any additional configured item IDs not in favorites
            for item_id in self.item_ids:
                if self.has_item(item_id):
                    self._gone_item_ids.discard(str(item_id))
                    continue
                if str(item_id) in self._gone_item_ids:
                    continue
                try:
                    item = await self.hass.async_add_executor_job(
                        self._tgtg.get_item, item_id
                    )
                    self.items.append(item)
                    self.item_id_set.add(item_id)
                except TgtgAPIError as err:
                    if err.args and err.args[0] in (401, 403, 429):
                        raise
                    if err.args and err.args[0] == 410:
                        self._gone_item_ids.add(str(item_id))
                        _LOGGER.info(
                            "TGTG item %s is gone (HTTP 410); skipping future individual requests",
                            item_id,
                        )
                    else:
                        _LOGGER.warning(
                            "Failed to fetch item %s (HTTP %s)",
                            item_id,
                            err.args[0] if err.args else None,
                        )
                await asyncio.sleep(API_RATE_LIMIT_DELAY)

            # Fetch active orders (non-critical, don't fail if this errors)
            await asyncio.sleep(API_RATE_LIMIT_DELAY)
            try:
                orders_response = await self.hass.async_add_executor_job(
                    self._tgtg.get_active
                )
                self.tgtg_orders = orders_response.get("orders", [])
            except TgtgAPIError as err:
                if err.args and err.args[0] in (401, 403, 429):
                    raise
                _LOGGER.warning(
                    "Failed to fetch orders (HTTP %s)",
                    err.args[0] if err.args else None,
                )
                self.tgtg_orders = []

            # Reset error counter on success
            self._consecutive_api_errors = 0

            dismiss_captcha(self.hass, f"tgtg_captcha_{self.config_entry.entry_id}")
            return True
        except TgtgLoginError as err:
            self._handle_api_error(err, login=True)
        except TgtgAPIError as err:
            self._handle_api_error(err)
        finally:
            self._save_credentials()
            if datetime.now(timezone.utc).timestamp() >= self._api_retry_after:
                self._set_polling_interval()
