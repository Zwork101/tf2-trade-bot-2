import asyncio
import json
import logging

from pytrade import login, client

from listings import ListingManager
from price import ItemManager
from utils import check_banned

# Declare global variables
logging.basicConfig(format='[%(levelname)s]: %(message)s', level=logging.DEBUG)
settings = {}
steamguard = {}
PriceHolder = None

# Load the settings from file
logging.info('Fetching for settings in file: settings.json')
try:
    with open('settings.json') as file:
        settings = json.load(file)
except FileNotFoundError:
    logging.warning("ERROR: settings.json file not found")
    input()
    exit(1)

# Load the secrets from guard.json
logging.info('Reading secrets from file: guard.json')
try:
    with open('guard.json') as file:
        steamguard = json.load(file)
        logging.info("Read guard.json file")
except FileNotFoundError:
    logging.warning("Guard file not found, will ask for code")

# Read input data for item prices and stock
logging.info('Reading prices from file: prices.csv')
try:
    with open('prices.csv') as prices:
        PriceHolder = ItemManager(prices)
except FileNotFoundError:
    logging.warning("ERROR: prices.csv file not found")
    input()
    exit(1)

# Create client and manager
if steamguard:
    steam_client = login.AsyncClient(settings['username'], settings['password'],
                                     shared_secret=steamguard['shared_secret'])
    manager = client.TradeManager(settings['steamid'], settings['steam-apikey'],
                                  identity_secret=steamguard['identity_secret'])
else:
    code = input("One Time Code: ")
    steam_client = login.AsyncClient(settings['username'], settings['password'], one_time_code=code)
    manager = client.TradeManager(settings['steamid'], settings['steam-apikey'])

bptf = ListingManager(manager, PriceHolder, settings['backpacktf-token'],
                      settings.get("description", "{name} for\n{ref} ref and {keys} keys"))


@manager.on('logged_on')
async def login():
    print('|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|')
    print(f'|+| Name: {settings["username"][:21]}{" " * (22 - len(settings["username"]))}|+|')
    print(f'|+| SteamID: {settings["steamid"][:21]}{" " * (19 - len(settings["steamid"]))}|+|')
    print('|+| Status: Logged in!          |+|')
    print('|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|+|')

    try_again = False
    inv = await manager.get_inventory(manager.steamid, 440)
    if inv[0]:
        PriceHolder.update_stock_inv(inv[1])
    else:
        logging.warning("Unable to get backpack, trying again.")
        try_again = True
    if not PriceHolder.filter('Mann Co. Supply Crate Key'):
        logging.info("Mann Co. Supply Crate Key was not priced, getting value from bp.tf")
        await PriceHolder.update_key_price(settings['backpacktf-apikey'])
    print("Got key price!")
    if try_again:
        inv = await manager.get_inventory(manager.steamid, 440)
        if inv[0]:
            PriceHolder.update_stock_inv(inv[1])
        else:
            logging.fatal("Unable to get inventory: Attempting to continue.")


@manager.on('new_trade')
async def new_trade(trade):
    print(f"Trade Offer Received: {trade.tradeofferid} From {trade.steamid_other.toString()}")
    if PriceHolder.calculate_trade(trade):
        print(f'[{trade.tradeofferid}]: Trade looks good, checking for scammer')
        steamid = trade.steamid_other.toString()
        if await check_banned(steamid, manager, settings['backpacktf-apikey']):
            logging.info(f"{steamid} is a scammer, declining")
            resp = await trade.decline()
            if resp[0]:
                return
            else:
                logging.warning(f"Failed to decline trade: {resp[1]}")
                return
        print(f"[{trade.tradeofferid}]: Trade and Partner looks good! Accepting")
        resp = await trade.accept()
        if not resp[0]:
            logging.fatal("Failed to accept trade: {resp[1]}")
    else:
        print(f"[{trade.tradeofferid}]: This trade is bad, declining")
        resp = await trade.decline()
        if not resp[0]:
            logging.warning(f"Failed to decline trade: {resp[1]}")


@manager.on('trade_accepted')
async def trade_passed(trade):
    print(f"[{trade.tradeofferid}]: Accepted Trade!")
    print(trade.items_to_receive)
    print(trade.items_to_give)
    PriceHolder.update_stock_trade(trade)
    for item in trade.items_to_give:
        craft, effect = PriceHolder.craftable_or_effect(item).values()
        item_data = PriceHolder.filter(item.market_name, 1, craft, effect)[0]
        if item_data['stock'] > item_data['current_stock']:
            bptf.make_buy_listing(item.market_name, item_data)
    for item in trade.items_to_receive:
        craft, effect = PriceHolder.craftable_or_effect(item).values()
        item_data = PriceHolder.filter(item.market_name, craft, effect)[0]
        if item_data['stock'] < item_data['current_stock']:
            bptf.make_sell_listing(item, item_data['price'])
    bptf.send_listings()
    bptf.remove_old()


@manager.on('error')
async def exception(exc):
    logging.fatal(f"({exc.__name__}): {exc}")


@manager.on('poll_error')
async def poll_error(problem):
    logging.error(f"There was an issue when polling: {problem}")
    loop.run_until_complete(asyncio.ensure_future(manager.login(steam_client)))
    manager.run_forever()


loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.ensure_future(manager.login(steam_client)))
manager.run_forever()
