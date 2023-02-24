import logging
import datetime

from tgtg import TgtgClient

from .const import CONF_NEXT_SALES_WINDOW, CONF_ITEM, CONF_ITEM_ID

LOGGER = logging.getLogger(__name__)

class Client:
    updateCycle = None
    items = None

    def __init__(self, hass, access_token=None, refresh_token=None, user_id=None, user_agent=None, email=None, cookie=None):
        self.hass = hass

        if email != "":
            self.email = email

        if access_token != "":
            self.access_token = access_token

        if refresh_token != "":
            self.refresh_token = refresh_token

        if user_id != "":
            self.user_id = user_id

        if user_agent != "":
            self.user_agent = user_agent

        if cookie != "":
            self.cookie = cookie

        if((self.access_token and self.refresh_token and self.user_id and self.user_agent) or self.email):
            self.tgtg = TgtgClient(
                email=self.email,
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                user_id=self.user_id,
                user_agent=self.user_agent,
                cookie=self.cookie
            )

    async def fetch_credentials(self):
        return await self.hass.async_add_executor_job(self.tgtg.get_credentials)

    async def fetch_favourites(self):
        return await self.hass.async_add_executor_job(self.tgtg.get_favourites)

    async def fetch_items(self):
        return await self.hass.async_add_executor_job(self.tgtg.get_items)

    async def fetch_item(self, item_id):
        return await self.hass.async_add_executor_job(self.tgtg.get_item, item_id)

    def get_item(self, item_id):
        return self.items.get(item_id)

    async def update_item_details(self, item_id):
        LOGGER.debug('Updating item details: %s', item_id)
        item = await self.fetch_item(item_id)
        # merge data
        self.items[item_id] = {**self.items[item_id], **item}

    async def update(self):
        # update all favourites every 15 minutes
        if self.updateCycle is None or self.updateCycle % 5 == 0:
            LOGGER.debug('Updating TGTG favourites ...')
            items = await self.fetch_items()
            self.items = {d[CONF_ITEM][CONF_ITEM_ID]: d for d in items}

        # update details of each item
        for item_id in self.items:
            # update item more often if item is in saleswindow
            if self.is_during_sales_window(self.items[item_id], 10):
                LOGGER.debug('Updating item details because in saleswindow...')
                self.update_item_details(item_id)
            # fetch item in detail to get more data (but not so often) = 40 * DEFAULT_SCAN_INTERVAL
            elif self.updateCycle is None or self.updateCycle >= 40:
                await self.update_item_details(item_id)

        # reset updateCycle
        if self.updateCycle is None or self.updateCycle >= 40:
            self.updateCycle = 0

        self.updateCycle += 1

    def is_during_sales_window(self, item, salesWindowMinutes):
        if CONF_NEXT_SALES_WINDOW in item:
            current_datetime = None
            sales_window = None

            try:
                current_datetime = datetime.datetime.now(datetime.timezone.utc)
            except ValueError as e:
                LOGGER.error('Current Date Error: %s', e)

            try:
                sales_window = datetime.datetime.strptime(item[CONF_NEXT_SALES_WINDOW], '%Y-%m-%dT%H:%M:%S%z')
            except ValueError as e:
                LOGGER.error('Current SalesWindow Date Error: %s', e)

            return sales_window <= current_datetime <= sales_window + datetime.timedelta(minutes=salesWindowMinutes)

        return False
