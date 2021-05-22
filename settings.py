import linecache
import sys

# TOKEN = '1715716309:AAFXmXSldg1jpB-gGzdB7yOdX8ruGYrzacY'
TOKEN = '1736058357:AAF3OmRx7bLczhcsHJTJN6AHBruW1TSxzgw'
DELAY = 5
api_id = 5066297
api_hash = 'adafd7c34ac0199fba4a7e81630208ff'
phone = '+380661774708'
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    exc = 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
    print(exc)
    return exc


channels_links = {'девушки': '-1001470907718',  # right
                  'видео': '-1001294452856',  # right
                  'мемы': '-1001252485999',  # right
                  'животные': '-1001367691516',  # right
                  'АйДаЮзеры': '-1001420568474',  # right
                  'позалипать': '-1001222952410',  # right
                  'жизненно': '-1001464760193',  # right
                  'отношения': '-1001351980116',  # right
                  }

test_id = '-1001304448917'
#test_id = '396247215'
favorite_id = '-1001467928277'
