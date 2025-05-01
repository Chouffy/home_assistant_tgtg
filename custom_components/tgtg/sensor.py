"""Platform for sensor integration."""
import logging

from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA

from .const import (
    DOMAIN,
    CONF_ITEM,
    CONF_ITEM_ID,
    CONF_PRICE_INCL_TAX,
    CONF_VALUE_INCL_TAX,
    CONF_ITEM_END,
    CONF_ITEM_START,
    CONF_ITEM_LOGO_PICTURE,
    CONF_PICKUP_INTERVAL,
    CONF_NEXT_SALES_WINDOW,
    CONF_SOLD_OUT_AT,
    CONF_STORE,
    CONF_STORE_ID,
    ATTR_ITEM_ID,
    ATTR_ITEM_ID_URL,
    ATTR_PRICE,
    ATTR_VALUE,
    ATTR_PICKUP_START,
    ATTR_PICKUP_STOP,
    ATTR_SOLDOUT_DATE,
    ATTR_NEXT_SALES_WINDOW_DATE,
    ATTR_LOGO_PICTURE,
    ATTR_STORE_ID,
    TGTG_NAME,
    TGTG_CLIENT,
    TGTG_COORDINATOR,
    DEFAULT_SHORT_NAME
)

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistantType, entry: ConfigType, async_add_entities
) -> None:
    """Set up the TGTG sensor platform."""
    LOGGER.info("Setting up TGTG sensor platform.")

    hass_data = hass.data[DOMAIN][entry.entry_id]
    LOGGER.debug(hass.data[DOMAIN])
    items = hass_data[TGTG_CLIENT].items

    for item_id in items:
        async_add_entities([
            TGTGItemSensor(hass_data, item_id)
        ])

class TGTGItemSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, hass_data, item_id):
        """Initialize the sensor."""
        self._client = hass_data[TGTG_CLIENT]
        self._coordinator = hass_data[TGTG_COORDINATOR]

        self._name = f"{DEFAULT_SHORT_NAME} {item_id}"
        self._unique_id = f"{DOMAIN}_{hass_data[TGTG_NAME]}_store_{item_id}"
        self._icon = "mdi:storefront-outline"
        self._unit_of_measurement = "pcs"
        self.item_id = item_id

        LOGGER.info(f'Setting up TGTG Sensor {self._unique_id}.')

    def get_item(self):
        return self._client.get_item(self.item_id)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        item = self.get_item()  # Cache the result of get_item()
        store_name = item['store']['store_name']
        display_name = item['display_name']
        if display_name:
            return display_name
        if store_name:
            return store_name
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit_of_measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.get_item()['items_available']

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self.get_item()['items_available']

    async def async_added_to_hass(self) -> None:
        """Set up a listener and load data."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Schedule a custom update via the common entity update service."""
        await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the optional state attributes."""
        data = {}

        entry = self.get_item()

        item = entry[CONF_ITEM]
        if CONF_ITEM_ID in item:
            item_id = item[CONF_ITEM_ID]
            data[ATTR_ITEM_ID] = item_id
            data[ATTR_ITEM_ID_URL] = f"https://share.toogoodtogo.com/item/{item_id}"
        if CONF_PRICE_INCL_TAX in item:
            attr = item[CONF_PRICE_INCL_TAX]
            minor_units = attr["minor_units"]
            decimals = attr["decimals"]
            code = attr["code"]
            data[ATTR_PRICE] = f"{str( int(minor_units) / pow(10, int(decimals)) )} {code}"
        if CONF_VALUE_INCL_TAX in item:
            attr = item[CONF_VALUE_INCL_TAX]
            minor_units = attr["minor_units"]
            decimals = attr["decimals"]
            code = attr["code"]
            data[ATTR_VALUE] = f"{str( int(minor_units) / pow(10, int(decimals)) )} {code}"
        if CONF_ITEM_LOGO_PICTURE in item:
            data[ATTR_LOGO_PICTURE] = item[CONF_ITEM_LOGO_PICTURE]['current_url']

        store = entry[CONF_STORE]
        if CONF_STORE_ID in store:
            data[ATTR_STORE_ID] = store[CONF_STORE_ID]

        if CONF_PICKUP_INTERVAL in entry:
            if CONF_ITEM_START in entry[CONF_PICKUP_INTERVAL]:
                data[ATTR_PICKUP_START] = entry[CONF_PICKUP_INTERVAL][CONF_ITEM_START]
            if CONF_ITEM_END in entry[CONF_PICKUP_INTERVAL]:
                data[ATTR_PICKUP_STOP] = entry[CONF_PICKUP_INTERVAL][CONF_ITEM_END]
        if CONF_SOLD_OUT_AT in entry:
            data[ATTR_SOLDOUT_DATE] = entry[CONF_SOLD_OUT_AT]

        if CONF_NEXT_SALES_WINDOW in entry:
            data[ATTR_NEXT_SALES_WINDOW_DATE] = entry[CONF_NEXT_SALES_WINDOW]

        return data

    @property
    def available(self):
        """Return if state is available."""
        return self.get_item() is not None

    @property
    def should_poll(self) -> bool:
        """Entities do not individually poll."""
        return False

