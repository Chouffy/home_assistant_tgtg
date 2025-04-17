"""Generate sensors for TGTG."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from .coordinator import TGTGUpdateCoordinator
from .entity import TGTGEntity

@dataclass(frozen=True, kw_only=True)
class TGTGEntityDescription(SensorEntityDescription):
    """TGTG Sensor Description."""
    name_fn: Callable[[TGTGEntity], None] = lambda: None
    value_fn: Callable[[TGTGEntity], None] = lambda: None

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
    """Setup the sensor platform."""
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
