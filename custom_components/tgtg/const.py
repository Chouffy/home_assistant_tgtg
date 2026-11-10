"""TGTG Constants."""

DOMAIN = "tgtg"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_COOKIE = "cookie"
CONF_ITEM_IDS = "item_ids"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SALES_SCAN_INTERVAL = "sales_scan_interval"

DEFAULT_SCAN_INTERVAL = 60  # 60 minutes default, 3 minutes during sales windows
DEFAULT_SALES_SCAN_INTERVAL = 3
POLLING_JITTER_SECONDS = 30
TGTG_USER_AGENT = (
    "TGTG/26.7.2 Dalvik/2.1.0 (Linux; U; Android 17; Pixel 8 Pro Build/CP2A.260705.006)"
)

ATTR_ITEM_ID = "item_id"
ATTR_ITEM_URL = "item_url"
ATTR_PRICE = "item_price"
ATTR_VALUE = "original_value"
ATTR_PICKUP_START = "pickup_start"
ATTR_PICKUP_END = "pickup_end"
ATTR_SOLDOUT_TIMESTAMP = "soldout_timestamp"
ATTR_ORDERS_PLACED = "orders_placed"
ATTR_TOTAL_QUANTITY_ORDERED = "total_quantity_ordered"
ATTR_PICKUP_WINDOW_CHANGED = "pickup_window_changed"
ATTR_CANCEL_UNTIL = "cancel_until"
ATTR_LOGO_URL = "logo_url"
ATTR_COVER_URL = "cover_url"
ATTR_PICKUP_LOCATION = "pickup_location"
ATTR_PICKUP_LONGITUDE = "longitude"
ATTR_PICKUP_LATITUDE = "latitude"
