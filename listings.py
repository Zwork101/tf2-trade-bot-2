import asyncio

from utils import ListingResp, item_qualities


class ListingManager:

    def __init__(self, manager, item_manager, token, description):
        self.manager = manager
        self.item_manager = item_manager
        self.token = token
        self.description = description
        self.current_listings = asyncio.ensure_future(self.my_listings())
        self.listing_queue = []

    async def my_listings(self):
        async with self.manager.session.get("https://backpack.tf/api/classifieds/listings/v1",
                                            params={'token': self.token, 'item_names': 1}) as resp:
            listings = await resp.json()
            if resp.status != 200:
                print(f"ERROR: Unable to load new listings: {listings}")
                return self.current_listings
            self.current_listings = listings['listings']
            return self.current_listings

    def make_sell_listing(self, item, ref):
        keys = 0
        while ref > self.item_manager.currencies['Mann Co. Supply Crate Key']:
            keys += 1
            ref -= self.item_manager.currencies['Mann Co. Supply Crate Key']
        formatted_details = self.description.format(name=item.market_name, ref=ref, keys=keys)
        payload = {'id': item.id, 'indent': 1, 'currencies': {'metal': ref, 'keys': keys},
                   'promoted': 1, 'details': formatted_details, 'token': self.token}
        self.listing_queue.append(payload)

    def make_buy_listing(self, name, data):
        keys = 0
        ref = data['price']
        while ref > self.item_manager.currencies['Mann Co. Supply Crate Key']:
            keys += 1
            ref -= self.item_manager.currencies['Mann Co. Supply Crate Key']
        formatted_details = self.description.format(name=name, ref=ref, keys=keys)
        if 'Unusual' in name:
            name = name.replace('Unusual', data['effect'])
        qualities = ' '.join([str(item_qualities[q]) for q in name.split(' ') if q in item_qualities])
        payload = {'intent': 0, 'item': {'quality': qualities, 'item_name': name, 'craftable': data['craftable']},
                   'promoted': 1, 'details': formatted_details, 'currencies': {'metal': ref, 'keys': keys}}
        self.listing_queue.append(payload)

    async def send_listings(self):
        async with self.manager.post("https://backpack.tf/api/classifieds/list/v1",
                                     json={'token': self.token, 'listings': self.listing_queue}) as resp:
            data = await resp.json()
            if resp.status != 200:
                print(f'There was an issue creating the listings: {data["message"]}')
                return
            for name, status in data['listings'].items():
                if 'created' in status:
                    print(f"[{name}]: Listing Created!")
                else:
                    for enum in ListingResp:
                        if enum.value == int(status['error']):
                            print(f'[{name}]: Error: {enum.name}')
        self.listing_queue.clear()

    async def remove_old(self):
        payload = {'listings': [], 'token': self.token}
        for name, item in self.item_manager.items.items():
            if (not (item['stock'] <= item['current_stock'] and item['intent'] == 0)) or \
                    (not (item['stock'] >= item['current_stock'] and item['intent'] == 1)):
                continue
            if 'Unusual' in name:
                name = name.replace('Unusual', item['effect'])
            for listing in self.current_listings:
                if listing['item']['name'] == name:
                    payload['listings'].append(listing['id'])
                    break
        if payload['listings']:
            async with self.manager.session.delete('https://backpack.tf/api/classifieds/delete/v1',
                                                   json=payload) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    print(f"Error Deleting listings: {txt}")
                else:
                    print("Deleted Listings")
        await self.my_listings()
