import linecache
import sys
import my_data


TOKEN = '1837010234:AAFv_KXX2Y3d5E1fnG1fPDOfN0-p1ttb7yg'  # Memes_bot

api_id = 5066297
api_hash = 'adafd7c34ac0199fba4a7e81630208ff'

phone = my_data.my_phone
personal_id = my_data.my_id
test_id = my_data.my_test_id

channels_links = {'девушки': '-1001470907718',
                  'видео': '-1001294452856',
                  'мемы': '-1001252485999',
                  'животные': '-1001367691516',
                  'АйДаЮзеры': '-1001420568474',
                  'позалипать': '-1001222952410',
                  'жизненно': '-1001464760193',
                  'отношения': '-1001351980116',
                  'featured': '-1001467928277'
                  }

channels_info = {
    'девушки': {'telegram': '-1001470907718', 'api_id': None},
    'видео': {'telegram': '-1001294452856', 'api_id': None},
    'мемы': {'telegram': '-1001252485999', 'api_id': None},
    'животные': {'telegram': '-1001367691516', 'api_id': None},
    'АйДаЮзеры': {'telegram': '-1001420568474', 'api_id': None},
    'позалипать': {'telegram': '-1001222952410', 'api_id': None},
    'жизненно': {'telegram': '-1001464760193', 'api_id': None},
    'отношения': {'telegram': '-1001351980116', 'api_id': None},
    'featured': {'telegram': '-1001467928277', 'api_id': None},
}

favorite_id = '-1001467928277'
DT_FORMAT = '%Y-%m-%d %H:%M:%S'

