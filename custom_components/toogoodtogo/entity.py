"""TGTG Entity."""

from homeassistant.const import CONF_EMAIL
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CANCEL_UNTIL,
    ATTR_COVER_URL,
    ATTR_ITEM_ID,
    ATTR_ITEM_URL,
    ATTR_LOGO_URL,
    ATTR_ORDERS_PLACED,
    ATTR_PICKUP_END,
    ATTR_PICKUP_START,
    ATTR_PICKUP_WINDOW_CHANGED,
    ATTR_PRICE,
    ATTR_SOLDOUT_TIMESTAMP,
    ATTR_TOTAL_QUANTITY_ORDERED,
    ATTR_VALUE
)
from .coordinator import TGTGUpdateCoordinator

class TGTGEntity(CoordinatorEntity[TGTGUpdateCoordinator]):
    """Entity for TGTG."""

    _email = None
    _item_id = None

    def __init__(self, coordinator, item_id: int):
        """Init a TGTG Entity."""
        super().__init__(coordinator)
        self._email = coordinator.config_entry.data[CONF_EMAIL]
        self._item_id = item_id

    @property
    def unique_id(self) -> str:
        """Generate a unique ID for this entity."""
        return f"{self._item_id}_{self.name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={("tgtg", self._email)},
            manufacturer="Too Good To Go",
            name=self._email
        )

    @property
    def tgtg_answer(self) -> dict | None:
        """Return the item."""
        for item in self.coordinator.items:
            if item["item"]["item_id"] == self._item_id:
                return item
        return None

    @property
    def store_name(self) -> str:
        """Return the store name."""
        return self.tgtg_answer["display_name"]

    @property
    def item_qty(self) -> int:
        """Return available qty."""
        return self.tgtg_answer["items_available"]

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra state attributes."""
        if not self.tgtg_answer:
            return None
        data = {}
        if "item" in self.tgtg_answer:
            if "item_id" in self.tgtg_answer["item"]:
                data[ATTR_ITEM_ID] = self.tgtg_answer["item"]["item_id"]
                data[ATTR_ITEM_URL] = "https://share.toogoodtogo.com/item/" + str(
                    self.tgtg_answer["item"]["item_id"]
                )
            if "item_price" in self.tgtg_answer["item"]:
                data[ATTR_PRICE] = (
                    str(
                        int(
                            self.tgtg_answer["item"]["item_price"][
                                "minor_units"
                            ]
                        )
                        / pow(
                            10,
                            int(
                                self.tgtg_answer["item"]["item_price"][
                                    "decimals"
                                ]
                            ),
                        )
                    )
                    + " "
                    + self.tgtg_answer["item"]["item_price"]["code"]
                )
            if "item_value" in self.tgtg_answer["item"]:
                data[ATTR_VALUE] = (
                    str(
                        int(
                            self.tgtg_answer["item"]["item_value"][
                                "minor_units"
                            ]
                        )
                        / pow(
                            10,
                            int(
                                self.tgtg_answer["item"]["item_value"][
                                    "decimals"
                                ]
                            ),
                        )
                    )
                    + " "
                    + self.tgtg_answer["item"]["item_value"]["code"]
                )

            if "logo_picture" in self.tgtg_answer["item"]:
                data[ATTR_LOGO_URL] = self.tgtg_answer["item"]["logo_picture"]["current_url"]
            if "cover_picture" in self.tgtg_answer["item"]:
                data[ATTR_COVER_URL] = self.tgtg_answer["item"]["cover_picture"]["current_url"]

        if "pickup_interval" in self.tgtg_answer:
            if "start" in self.tgtg_answer["pickup_interval"]:
                data[ATTR_PICKUP_START] = self.tgtg_answer["pickup_interval"]["start"]
            if "end" in self.tgtg_answer["pickup_interval"]:
                data[ATTR_PICKUP_END] = self.tgtg_answer["pickup_interval"]["end"]
        if "sold_out_at" in self.tgtg_answer:
            data[ATTR_SOLDOUT_TIMESTAMP] = self.tgtg_answer["sold_out_at"]

        orders_placed = 0
        total_quantity_ordered = 0
        for order in self.coordinator.tgtg_orders:
            if "item_id" in order:
                if order["item_id"] == str(self._item_id):
                    orders_placed += 1
                    if "quantity" in order:
                        total_quantity_ordered += order["quantity"]
                    if "pickup_window_changed" in order:
                        data[ATTR_PICKUP_WINDOW_CHANGED] = order["pickup_window_changed"]
                    if "cancel_until" in order:
                        data[ATTR_CANCEL_UNTIL] = order["cancel_until"]
        data[ATTR_ORDERS_PLACED] = orders_placed
        if total_quantity_ordered > 0:
            data[ATTR_TOTAL_QUANTITY_ORDERED] = total_quantity_ordered
        return data
