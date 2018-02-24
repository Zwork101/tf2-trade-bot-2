import enum

import aiohttp


class ListingResp(enum.Enum):
    OK = 0
    ItemNotInInventory = 1
    InvalidItem = 2
    ItemNotListable = 3
    ItemNotTradable = 4
    MarketplaceItemNotPriced = 5
    RelistTimeout = 6
    ListingCapExceeded = 7
    CurrenciesNotSpecified = 8
    CyclicCurrency = 9
    PriceNotSpecified = 10
    UnknownIntent = 11


async def check_banned(steamid, manager, key):
    async with manager.session.get("https://backpack.tf/api/users/info/v1",
                                   data={'key': key, 'steamids': steamid}) as resp:
        resp_json = await resp.json()
        if "bans" in resp_json['users'][steamid]:
            if "steamrep_caution" in resp_json['users'][steamid]['bans'] or \
                    "steamrep_scammer" in resp_json['users'][steamid]['bans'] or \
                    "all" in resp_json['users'][steamid]['bans']:
                return True
    return False


item_qualities = {
    "Normal": 0,
    "Genuine": 1,
    "Vintage": 3,
    "Unusual": 5,
    "Unique": 6,
    "Community": 7,
    "Valve": 8,
    "Self-Made": 9,
    "Strange": 11,
    "Haunted": 13,
    "Collector's": 14,
    "Decorated Weapon": 15
}


async def heartbeat(token):
    async with aiohttp.ClientSession() as sess:
        resp = await sess.post(
            "https://backpack.tf/api/aux/heartbeat/v1",
            data={"token": token, "automatic": "all"}
        )
        return await resp.json()
