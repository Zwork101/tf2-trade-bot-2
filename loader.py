from Cryptodome.Cipher import DES
import enum

def _pad(text):
    while len(text) % 8 != 0:
        text += ' '
    return text

def _encrypt(key, text):
    if len(key) != 8:
        raise ValueError("Key must be length of eight")
    des = DES.new(key.encode(), DES.MODE_ECB)
    return des.encrypt(_pad(text).encode())

def _decrypt(key, text):
    if len(key) != 8:
        raise ValueError("Key must be length of eight")
    des = DES.new(key.encode(), DES.MODE_ECB)
    return des.decrypt(text)

def encrypt_file(filename, key):
    with open(filename, 'r') as file:
        file_txt = _encrypt(key, file.read())
    with open(filename, 'wb') as file:
        file.write(file_txt)

def decrypt_file(filename, key):
    with open(filename, 'rb') as file:
        file_txt = file.read()
        return _decrypt(key, file_txt).decode().strip()

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