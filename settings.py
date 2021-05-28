import linecache
import sys
import my_data

# TOKEN = '1715716309:AAFXmXSldg1jpB-gGzdB7yOdX8ruGYrzacY' # testBot
TOKEN = '1736058357:AAF3OmRx7bLczhcsHJTJN6AHBruW1TSxzgw'  # Memes_bot
DELAY = 60 * 3

api_id = 5066297
api_hash = 'adafd7c34ac0199fba4a7e81630208ff'

phone = my_data.my_phone
personal_id = my_data.my_id
test_id = my_data.my_test_id

channels_links = {'девушки': '-1001470907718',  # right
                  'видео': '-1001294452856',  # right
                  'мемы': '-1001252485999',  # right
                  'животные': '-1001367691516',  # right
                  'АйДаЮзеры': '-1001420568474',  # right
                  'позалипать': '-1001222952410',  # right
                  'жизненно': '-1001464760193',  # right
                  'отношения': '-1001351980116',  # right
                  'featured': '-1001467928277'
                  }
channels_info = {
    'девушки': {'telegram': '-1001470907718', 'api_id': None},
    'видео': {'telegram': '-1001294452856', 'api_id': None},
    'мемы': {'telegram': '-1001252485999', 'api_id': None},
    'животные': {'telegram': '-1001367691516', 'api_id': None},
    'АйДаЮзеры': {'telegram': '-1001420568474', 'api_id': None},
    'позалипать': {'telegram': '-1001222952410', 'api_id': None},  # right
    'жизненно': {'telegram': '-1001464760193', 'api_id': None},  # right
    'отношения': {'telegram': '-1001351980116', 'api_id': None},  # right
    'featured': {'telegram': '-1001467928277', 'api_id': None},  # right
}

favorite_id = '-1001467928277'
DT_FORMAT = '%Y-%m-%d %H:%M:%S'


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    exc = f'Exception in ({filename}, at line: {lineno} "{line.strip()}"): {exc_obj}'
    return exc


def key_by_value(dictionary, value):
    try:
        result = list(dictionary.keys())[list(dictionary.values()).index(value)]
    except ValueError:
        result = 'key_by_value_exception'
    return result

