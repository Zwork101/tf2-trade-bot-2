from listings import ListingManager
from loader import *
from price import ItemManager
import asyncio
import json
from pytrade import login, client
import logging

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
        guard = json.load(file)
        print("File not encrypted. Would you like to encrypt it?")
        yn = input('[y/n]: ')
        if yn[0].lower() == 'y':
            print('Please enter a string of characters, must be 8 characters long\nYOU MUST REMEMBER THIS: WRITE IT DOWN')
            key = input('[8 char long string]: ')
            encrypt_file('guard.json', key)
            print("File Encrypted!")
            logging.debug(f"File guard.json encrypted with key: {key}")
except (json.JSONDecodeError, UnicodeDecodeError):
    print("File encrypted / json is invalid\nPlease enter your key (8 characters long)")
    key = input('[8 char long string]: ')
    steamguard = decrypt_file('guard.json', key)
    logging.debug('guard.json file decrypted')
    try:
        steamguard = json.loads(steamguard)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logging.warning('Invalid json saved in guard.json file, or key was invalid')
        print(f"JSON is invalid, got {steamguard}")
        input()
        exit(1)
except FileNotFoundError:
    logging.warning("Guard file not found, will ask for code")

#Read input data for item prices and stock
logging.info('Reading prices from file: prices.csv')
try:
    with open('prices.csv') as prices:
        PriceHolder = ItemManager(prices)
except FileNotFoundError:
    logging.warning("ERROR: prices.csv file not found")
    input()
    exit(1)

#Create client and manager
if steamguard:
    steam_client = login.AsyncClient(settings['username'], settings['password'], shared_secret=steamguard['shared_secret'])
    manager = client.TradeManager(settings['steamid'], settings['steam-apikey'], identity_secret=steamguard['identity_secret'])
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
    PriceHolder.update_stock_inv(await manager.get_inventory(manager.steamid, 440))
    if not PriceHolder.filter('Mann Co. Supply Crate Key'):
        logging.info("Mann Co. Supply Crate Key was not priced, getting value from bp.tf")
        await PriceHolder.update_key_price(settings['backpacktf-apikey'])
    print("Got key price!")


@manager.on('new_trade')
async def new_trade(trade):
    print(f"Trade Offer Received: {trade.tradeofferid} From {trade.steamid_other.toString()}")
    if PriceHolder.calculate_trade(trade):
        steamid = trade.steamid_other.toString()
        print(f'[{trade.tradeofferid}]: Trade looks good, checking for scammer')
        async with manager.session.get("https://backpack.tf/api/users/info/v1",
                data={'key':settings['backpacktf-apikey'], 'steamids':steamid}) as resp:
            resp_json = await resp.json()
            if "bans" in resp_json['users'][steamid]:
                if "steamrep_caution" in resp_json['users'][steamid]['bans'] or \
                                "steamrep_scammer" in resp_json['users'][steamid]['bans'] or \
                                            "all" in resp_json['users'][steamid]['bans']:
                    print(f"WARNING: {steamid} is a scammer, declining")
                    await trade.decline()
                    return
        print(f"[{trade.tradeofferid}]: Trade and Partner looks good! Accepting")
        if not await trade.accept():
            print("There was an error accepting")
    else:
        print(f"[{trade.tradeofferid}]: This trade is bad, declining")

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
    # TODO test this function, and making listings

@manager.on('error')
async def exception(exc):
    print(f"ERROR: ({exc.__name__}): {exc}")

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.ensure_future(manager.login(steam_client)))
manager.run_forever()