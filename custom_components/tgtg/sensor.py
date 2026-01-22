"""Generate sensors for TGTG."""

from collections.abc import Callable
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import CONF_COOKIE, CONF_REFRESH_TOKEN, CONF_ITEM_IDS, DOMAIN
from .coordinator import TGTGUpdateCoordinator
from .entity import TGTGEntity

# YAML schema for import (deprecated)
CONF_ITEM = "item"
PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
        vol.Required(CONF_REFRESH_TOKEN): cv.string,
        vol.Required(CONF_COOKIE): cv.string,
        vol.Optional("user_id"): cv.string,
        vol.Optional(CONF_EMAIL): vol.Email(),
        vol.Optional(CONF_ITEM, default=""): cv.ensure_list,
    }
)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Import YAML config to config entry."""
    item_ids = [str(i) for i in config.get(CONF_ITEM, []) if i]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_EMAIL: config.get(CONF_EMAIL),
                CONF_ACCESS_TOKEN: config[CONF_ACCESS_TOKEN],
                CONF_REFRESH_TOKEN: config[CONF_REFRESH_TOKEN],
                CONF_COOKIE: config[CONF_COOKIE],
                CONF_ITEM_IDS: item_ids,
            },
        )
    )


@dataclass(frozen=True, kw_only=True)
class TGTGEntityDescription(SensorEntityDescription):
    """TGTG Sensor Description."""
    name_fn: Callable[[TGTGEntity], str] = lambda: None
    value_fn: Callable[[TGTGEntity], int] = lambda: None


ENTITY_DESCRIPTIONS = [
    TGTGEntityDescription(
        key="quantity",
        name="Quantity",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:storefront-outline",
        unit_of_measurement="pcs",
        name_fn=lambda entity: f"TGTG {entity.store_name}",
        value_fn=lambda entity: entity.item_qty
    )
]


async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    """Setup the sensor platform from config entry."""
    coordinator: TGTGUpdateCoordinator = config_entry.runtime_data
    if not isinstance(coordinator, TGTGUpdateCoordinator):
        return
    entities = []
    for item in coordinator.items:
        for description in ENTITY_DESCRIPTIONS:
            entities.append(
                TGTGSensor(coordinator, description, item["item"]["item_id"])
            )
    async_add_entities(
        entities
    )

class TGTGSensor(TGTGEntity, SensorEntity):
    """Represent a sensor."""

    def __init__(self, coordinator, description, item_id):
        super().__init__(coordinator=coordinator, item_id=item_id)
        self.coordinator = coordinator
        self.entity_description: TGTGEntityDescription = description

    @property
    def name(self) -> str:
        """Return entity name."""
        return self.entity_description.name_fn(self)

    @property
    def native_value(self) -> int:
        """Return sensor value."""
        return self.entity_description.value_fn(self)

    @property
    def entity_picture(self) -> str | None:
        """Return entity picture."""
        if "logo_picture" in self.tgtg_answer["item"]:
            return self.tgtg_answer["item"]["logo_picture"]["current_url"]
        return None
