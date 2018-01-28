import csv

import aiohttp


class ItemManager:
    currencies = {'Scrap Metal': .11, 'Reclaimed Metal': .33, 'Refined Metal': 1.00}

    def __init__(self, price_file):
        self.price_file = price_file
        self.items = {}
        reader = csv.DictReader(price_file)
        fields = ['market_name', 'price', 'intent', 'stock', 'craftable', 'effect']
        for name in reader.fieldnames:
            if name in fields:
                fields.remove(name)
        if fields:
            raise AttributeError("Not all fields required were found in file")
        for row in reader:
            row = {key: value.strip() for key, value in row.items()}
            if row['market_name'] not in self.items:
                self.items[row['market_name']] = [
                    {'price': float(row['price']), 'intent': int(row['intent']), 'current_stock': 0,
                     'stock': int(row['stock']), 'craftable': int(row['craftable']), 'effect': row['effect']}]
            else:
                self.items[row['market_name']].append(
                    {'price': float(row['price']), 'intent': int(row['intent']), 'current_stock': 0,
                     'stock': int(row['stock']), 'craftable': int(row['craftable']), 'effect': row['effect']})

    def update_stock_trade(self, trade):
        for item in trade.items_to_give:
            if not item.market_name in self.items:
                continue
            craftable, effect = self.craftable_or_effect(item).values()
            for i, inst in enumerate(self.items[item.market_name]):
                if craftable == inst['craftable'] and effect == inst['effect']:
                    self.items[item.market_name][i]['current_stock'] -= 1
        for item in trade.items_to_receive:
            if not item.market_name in self.items:
                continue
            craftable, effect = self.craftable_or_effect(item).values()
            for i, inst in enumerate(self.items[item.market_name]):
                if craftable == inst['craftable'] and effect == inst['effect']:
                    self.items[item.market_name][i]['current_stock'] += 1

    def update_stock_inv(self, items):
        for item in items:
            if not item.market_name in self.items:
                continue
            craftable, effect = self.craftable_or_effect(item).values()
            for i, inst in enumerate(self.items[item.market_name]):
                if craftable == inst['craftable'] and effect == inst['effect']:
                    self.items[item.market_name][i]['current_stock'] += 1

    def filter(self, item_name, intent: int = None, craftable: int = None, effect: str = None):
        """
        Filter through the items, to file the one (or multiple) requested
        :param item_name:
        :param intent:
        :param craftable:
        :param effect:
        :return:
        """
        selected = []
        for item in self.items.get(item_name, []):
            if intent is not None and intent != int(item['intent']):
                continue
            if craftable is not None and craftable != item['craftable']:
                continue
            if effect is not None and effect != item['effect']:
                continue
            selected.append(item)
        return selected

    def calculate_trade(self, trade):
        """
        Check if a trade is in our interest
        :param trade:
        :return bool:
        """

        # Get the values of the items in the trade
        our_value = 0
        their_value = 0
        if self.flow_stock(trade.items_to_receive, 0):
            return False
        if self.flow_stock(trade.items_to_give, 1):
            return False

        for item in trade.items_to_give:
            if item.market_name in ItemManager.currencies:
                our_value = self.add_ref(float(our_value), ItemManager.currencies[item.market_name])
                continue
            item_stats = self.craftable_or_effect(item)
            item_resp = self.filter(item.market_name, 1, item_stats['craftable'], item_stats['effect'])
            if not item_resp:
                return False
            our_value = self.add_ref(float(our_value), item_resp[0]['price'])

        for item in trade.items_to_receive:
            if item.market_name in ItemManager.currencies:
                their_value = self.add_ref(float(their_value), ItemManager.currencies[item.market_name])
                continue
            item_stats = self.craftable_or_effect(item)
            item_resp = self.filter(item.market_name, 0, item_stats['craftable'], item_stats['effect'])
            their_value = self.add_ref(float(their_value), item_resp[0]['price'])

        if our_value <= their_value:
            return True
        return False

    @staticmethod
    def craftable_or_effect(item):
        values = {'craftable': 1, 'effect': '-'}
        if 'Unusual' in item.market_name:
            for desc in item.descriptions:
                if desc['value'].startswith("★ Unusual Effect: "):
                    values['effect'] = desc['value'][18:]
        for desc in item.descriptions:
            if desc['value'] == "( Not Usable in Crafting )":
                values['craftable'] = 0
        return values

    @staticmethod
    def add_ref(v1, v2):
        v1_rem, v2_rem = int(str(v1).split('.')[1]), int(str(v2).split('.')[1])
        ref = int(v1) + int(v2)

        v1_rec, v2_rec = v1_rem // 33, v2_rem // 33
        v1_rem, v2_rem = v1_rem - v1_rec * 33, v2_rem - v2_rec * 33

        srp_added = v1_rem + v2_rem
        v1_rec += srp_added // 33
        srp_added -= (srp_added // 33) * 33

        rec_added = v1_rec + v2_rec
        ref += rec_added // 3
        rec_added -= (rec_added // 3) * 3

        return float(str(ref) + '.' + str(rec_added * 33 + srp_added))

    @staticmethod
    async def update_key_price(key):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://backpack.tf/api/IGetCurrencies/v1', params={'key': key}) as resp:
                data = await resp.json()
                data = data['response']
                if data['success']:
                    key_value = float(data['currencies']['keys']['price']['value'])
                    ItemManager.currencies['Mann Co. Supply Crate Key'] = key_value
                    session.close()
                    return True
                session.close()
                return False

    def flow_stock(self, items, intent):
        item_instance = {}
        for item in items:
            item_inst = '_'.join([str(i) for i in self.craftable_or_effect(item).values()])
            item_inst += f'_{item.market_name}'
            if item_inst in item_instance:
                item_instance[item_inst] += 1
                continue
            item_instance[item_inst] = 1
        for inst, amount in item_instance.items():
            crafts, effect, name = inst.split('_')
            item_listing = self.filter(name, intent, int(crafts), effect)
            if not item_listing: continue
            if intent and item_listing[0]['stock'] > item_listing[0]['current_stock'] - amount:
                return True
            elif not intent and item_listing[0]['stock'] < item_listing[0]['current_stock'] + amount:
                return True
        return False
