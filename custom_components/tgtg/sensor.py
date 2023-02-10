"""Platform for sensor integration."""
from __future__ import annotations
import logging
import voluptuous as vol

from tgtg import TgtgClient

from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_EMAIL
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers import config_validation as cv

DOMAIN = "tgtg"
CONF_ITEM = "item"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_USER_ID = "user_id"
CONF_COOKIE = "cookie"
CONF_USER_AGENT = "user_agent"
ATTR_ITEM_ID = "Item ID"
ATTR_ITEM_ID_URL = "Item URL"
ATTR_PRICE = "TGTG Price"
ATTR_VALUE = "Original value"
ATTR_PICKUP_START = "Pickup start"
ATTR_PICKUP_STOP = "Pickup stop"
ATTR_SOLDOUT_DATE = "Soldout date"
_LOGGER = logging.getLogger(DOMAIN)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
        vol.Required(CONF_REFRESH_TOKEN): cv.string,
        vol.Required(CONF_USER_ID): cv.string,
        vol.Required(CONF_COOKIE): cv.string,
        vol.Optional(CONF_EMAIL): vol.Email(),
        vol.Optional(CONF_ITEM, default=""): cv.ensure_list,
        vol.Optional(CONF_USER_AGENT, default=""): cv.string,
    }
)

global tgtg_client


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""

    email = config.get(CONF_EMAIL)
    item = config[CONF_ITEM]
    access_token = config[CONF_ACCESS_TOKEN]
    refresh_token = config[CONF_REFRESH_TOKEN]
    user_id = config[CONF_USER_ID]
    cookie = config[CONF_COOKIE]
    user_agent = config[CONF_USER_AGENT]

    global tgtg_client

    # Log in with tokens
    tgtg_client = TgtgClient(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        cookie=cookie,
        user_agent=user_agent,
    )

    # If item: isn't defined, use favorites - otherwise use defined items
    if item != [""]:
        for each_item_id in item:
            add_entities([TGTGSensor(each_item_id)])
    else:
        tgtgReply = tgtg_client.get_items()
        for item in tgtgReply:
            add_entities([TGTGSensor(item["item"]["item_id"])])


class TGTGSensor(SensorEntity):
    """Representation of a Sensor."""

    global tgtg_client

    tgtg_answer = None
    item_id = None
    store_name = None
    item_qty = None

    def __init__(self, item_id):
        """Initialize the sensor."""
        self.item_id = item_id
        self.update()

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"TGTG {self.store_name}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"tgtg_{self.item_id}"

    @property
    def icon(self):
        """Return an icon."""
        return "mdi:storefront-outline"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "pcs"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.item_qty

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the optional state attributes."""
        if not self.tgtg_answer:
            return None
        data = {}
        if "item" in self.tgtg_answer:
            if "item_id" in self.tgtg_answer["item"]:
                data[ATTR_ITEM_ID] = self.tgtg_answer["item"]["item_id"]
                data[ATTR_ITEM_ID_URL] = "https://share.toogoodtogo.com/item/" + str(
                    self.tgtg_answer["item"]["item_id"]
                )
            if "price_including_taxes" in self.tgtg_answer["item"]:
                data[ATTR_PRICE] = (
                    str(
                        int(
                            self.tgtg_answer["item"]["price_including_taxes"][
                                "minor_units"
                            ]
                        )
                        / pow(
                            10,
                            int(
                                self.tgtg_answer["item"]["price_including_taxes"][
                                    "decimals"
                                ]
                            ),
                        )
                    )
                    + " "
                    + self.tgtg_answer["item"]["price_including_taxes"]["code"]
                )
            if "value_including_taxes" in self.tgtg_answer["item"]:
                data[ATTR_VALUE] = (
                    str(
                        int(
                            self.tgtg_answer["item"]["value_including_taxes"][
                                "minor_units"
                            ]
                        )
                        / pow(
                            10,
                            int(
                                self.tgtg_answer["item"]["value_including_taxes"][
                                    "decimals"
                                ]
                            ),
                        )
                    )
                    + " "
                    + self.tgtg_answer["item"]["value_including_taxes"]["code"]
                )
        if "pickup_interval" in self.tgtg_answer:
            if "start" in self.tgtg_answer["pickup_interval"]:
                data[ATTR_PICKUP_START] = self.tgtg_answer["pickup_interval"]["start"]
            if "end" in self.tgtg_answer["pickup_interval"]:
                data[ATTR_PICKUP_STOP] = self.tgtg_answer["pickup_interval"]["end"]
        if "sold_out_at" in self.tgtg_answer:
            data[ATTR_SOLDOUT_DATE] = self.tgtg_answer["sold_out_at"]
        return data

    def update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        global tgtg_client
        self.tgtg_answer = tgtg_client.get_item(item_id=self.item_id)

        self.store_name = self.tgtg_answer["display_name"]
        self.item_qty = self.tgtg_answer["items_available"]
