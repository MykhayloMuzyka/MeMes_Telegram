import asyncio
import logging
import sys
import time
# from MeMes_Telegram.db.localbase import DataBase, TABLES
from datetime import datetime
from datetime import timedelta
import requests
import aiogram
import pytz
from aiogram import Dispatcher, Bot
from telethon import errors
from telethon import functions
from telethon.sync import TelegramClient
from telethon.tl.types import InputPeerEmpty
from telethon.tl.types import PeerChannel, MessageMediaPhoto, MessageMediaDocument

from MeMes_Telegram.confgis.settings import *
from MeMes_Telegram.memes import Api, ImageReader, Post
from MeMes_Telegram.utils import scheldue_difference

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s', filename='logging.log')

logging.warning('Script was Started')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
Api = Api()
# DataBase = DataBase()
# DataBase.create_tables(TABLES)
channels = Api.get_channels()
id_to_link = dict()
id_to_name = dict()

for ch_id, ch_name in channels:
    id_to_name[ch_id] = ch_name
    for name in channels_info:
        if name in ch_name:
            id_to_link[ch_id] = channels_info[name]['telegram']
            channels_info[name]['api_id'] = ch_id
            # DataBase.WriteChannels(ch_id, ch_name, channels_info[name]['telegram'])
channels_info['featured']['api_id'] = 'featured'
id_to_name['featured'] = 'featured'
id_to_link['featured'] = favorite_id
# DataBase.WriteChannels('featured', 'featured', favorite_id)

links = [i for i in channels_links.values()][:len(channels_links) - 1]


# channelsLatTimePublications = dict()
# for channel in channelsLatTimePublications


def key_by_value(dictionary, value):
    """
    Поиск ключа словаря по значению
    :param dictionary: словарь в котором производится поиск
    :param value: значения которое нужно найти
    :return: Ключ под которым лежит значение = value
    """
    try:
        result = list(dictionary.keys())[list(dictionary.values()).index(value)]
    except ValueError:
        result = 'key_by_value_exception'
    return result


async def lastChannelsPublicationTime(client: TelegramClient) -> dict:
    """
    Определяет время последнего поста в каждом канале
    :client: авторизированный клиент
    :channels: список ссылок на нужные каналы
    :return: словарь, где ключем являеться ссылка на канал, а значением - время последней публикации в нем
    """
    res = dict()
    # собираем все диалоги пользователя
    dialogs = await client.get_dialogs()
    for d in dialogs:
        peer_id = d.message.peer_id
        if isinstance(peer_id, PeerChannel):
            # проверка, являеться ли диалог каналом
            cid = f"-100{peer_id.channel_id}"
            if cid in links:
                # собираем последние 100 сообщений канала
                messages = await client.get_messages(peer_id.channel_id, limit=100)
                for m in messages:
                    if m.media:
                        # проверяем, присутствует ли в сообщении медиа
                        if isinstance(m.media, MessageMediaPhoto):
                            # проверка, являеться ли медиа фото
                            res[str(cid)] = (m.media.photo.date.astimezone(pytz.timezone('Europe/Kiev')) - timedelta(
                                days=100)).astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
                        if isinstance(m.media, MessageMediaDocument):
                            # проверка, являеться ли медиа файлом
                            res[str(cid)] = (m.media.document.date.astimezone(pytz.timezone('Europe/Kiev')) - timedelta(
                                days=100)).astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
                        break
                    elif m == messages[-1]:
                        res[str(cid)] = None
    return res


def strToDatetime(strDate: str) -> datetime:
    """
    Функция конвертации строки типа 'yyyy:mm:dd hh:mm:ss' в формат datetime
    :strDate: строка типа 'yyyy:mm:dd hh:mm:ss'
    :return: datetime формат заданой строки
    """
    year = int(strDate[:4])
    month = int(strDate[5:7])
    day = int(strDate[8:10])
    hour = int(strDate[11:13])
    minute = int(strDate[14:16])
    second = int(strDate[17:])
    return datetime(year=year, month=month, day=day,
                    hour=hour, minute=minute, second=second)


async def send_post(channel_id: str, chat: int, post: Post, client: TelegramClient, send_time=0):
    """
    :param channel_id: ID канала из апи для текцщего поста
    :param chat: Telegram ID канала телеграмм для постов этой категории
    :param post: экземпляр класса Post() который нужно отправить в телеграм
    :param client: авторизованный клиент
    :param send_time: время вызова функции, по умолчанию 0
    :return: True при успешной отправке поста, False в ином случае
    """
    post_filetype = post.url.strip()[-3:]
    # print(post_filetype, id_to_name[channel_id])
    if send_time != 0:
        timeout = abs(2 - float(time.time() - send_time).__round__(2))
        if float(time.time() - send_time).__round__(2) < 2:
            time.sleep(timeout)
            logging.info(f'#{post.id}: Timeout before sending =  {timeout}')

    to_send_time = time.time()
    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            try:
                message = await client.send_file(chat, image.crop())
            except Exception as e:
                logging.info('Cant send', e)
                return False
        else:
            logging.info(f'№{post.id} Don`t have watermark (no need to crop image) {post.url}')
            try:
                message = await client.send_file(chat, post.url)
            except Exception as e:
                logging.info('Cant send', e)
                return False

    else:
        try:
            message = await client.send_file(chat, post.url, caption=post.title)
        except Exception as e:
            logging.info('Cant send', e)
            return False
    logging.info(f'№{post.id} send in {float((send_time - to_send_time) * 1000).__round__(2)} ms')
    # Есди пост был отправлен то добавить информацию о нем в БД
    # DataBase.add_post(message.message_id, post, key_by_value(channels_links, chat))
    # DataBase.last_id('set', channel_id, post.id)
    # DataBase.last_update('set', channel_id,
    #                      datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT))
    return True


async def fill_channels():
    """
    Функция заполнения всех имеющихся телеграм каналов тысячей лучших постов в каждом
    :return:
    """
    # client = TelegramClient('fill', api_id, api_hash)
    # client.flood_sleep_threshold = 0
    # is_connected = client.is_connected()
    # if not is_connected:
    #     await client.connect()
    # auth = await client.is_user_authorized()
    # if not auth:
    #     await client.send_code_request(phone)
    #     user = None
    #     while user is None:
    #         code = input('Enter the code you just received: ')
    #         try:
    #             user = await client.sign_in(phone, code)
    #         except errors.SessionPasswordNeededError:
    #             pw = input('Two step verification is enabled. Please enter your password: ')
    #             user = client.sign_in(password=pw)

    Api.result = dict()
    all_memes = Api.best_posts()
    all_new_posts = dict()
    best_new_posts = dict()
    # lastPostTimes = await lastChannelsPublicationTime(client)
    # print(lastPostTimes)
    # print(lastPostTimes)
    # print(lastPostTimes)
    # print(len(all_memes))
    for channel_id in all_memes:
        # print(id_to_name[channel_id])
        all_new_posts[channel_id] = []
        # try:
        if channel_id == 'featured':
            continue
        # print(channel_id, True)
        # print(lastPostTimes[id_to_link[channel_id]])
        # if lastPostTimes[id_to_link[channel_id]]:
        #     lastPostTime = strToDatetime(lastPostTimes[id_to_link[channel_id]])
        for post_num, post in enumerate(all_memes[channel_id]):
            # if post.publish_at > lastPostTime:
            all_new_posts[channel_id].append(post)
        sorted_by_time = sorted(all_new_posts[channel_id], key=lambda post: post.publish_at)
        print(f"{id_to_name[channel_id]}: {sorted_by_time[-1].publish_at.astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)}")

        # else:
        #     for post_num, post in enumerate(all_memes[channel_id]):
        #         all_new_posts[channel_id].append(post)
        # best_new_posts[channel_id] = sorted(all_new_posts[channel_id], key=lambda post: post.smiles)
        # if len(best_new_posts[channel_id]) > 100:
        #     best_new_posts[channel_id] = best_new_posts[channel_id][len(best_new_posts[channel_id]) - 100:]
        # print(len(all_memes[channel_id]), len(all_new_posts[channel_id]), len(best_new_posts[channel_id]))
        # except KeyError as e:
        #     print(e)
    # for channel_id in best_new_posts:
    #     # print(id_to_link[channel_id])
    #     for post_num, post in enumerate(best_new_posts[channel_id]):
    #         try:
    #             await send_post(channel_id, int(id_to_link[channel_id]), best_new_posts[channel_id][post_num], client)
    #             logging.info(f' № {post_num}: Send post ({post.url}) and update post_id in DB')
    #
    #         except aiogram.exceptions.RetryAfter as err:
    #             logging.warning(f'№{post_num}: CATCH FLOOD CONTROL for {err.timeout} seconds')
    #             time.sleep(err.timeout)
    #             await send_post(channel_id, int(id_to_link[channel_id]), best_new_posts[channel_id][post_num], client)
    #
    #         except aiogram.exceptions.BadRequest as err:
    #             logging.warning(f'№{post_num}: get Bad request: {err} ({post.url})')
    #             await send_post(channel_id, int(id_to_link[channel_id]), best_new_posts[channel_id][post_num], client)
    #
    #         except Exception as err:
    #             # print(err)
    #             logging.error(f'fill_channels unknown error : {err}')
    #         time.sleep(1)
    # await client.log_out()
    # if client.is_connected():
    #     await client.disconnect()


async def mail():
    """
    Функция розсылки сообщения по всем каналам
    :return:
    """
    client = TelegramClient('mail', api_id, api_hash)
    client.flood_sleep_threshold = 0
    is_connected = client.is_connected()
    if not is_connected:
        await client.connect()
    auth = await client.is_user_authorized()
    if not auth:
        await client.send_code_request(phone)
        user = None
        while user is None:
            entered_code = False
            while not entered_code:
                code = input('Enter the code you just received: ')
                try:
                    int(code)
                    entered_code = True
                except Exception:
                    print('\nCode must be the number!\n')
            try:
                user = await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                pw = input('Two step verification is enabled. Please enter your password: ')
                user = client.sign_in(password=pw)
            except errors.rpcerrorlist.PhoneCodeInvalidError:
                print('\nWrong code!\n')
                time.sleep(5)

    msg = input('Enter your message: ')
    try:
        for link in links:
            await client.send_message(int(link), msg)
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of this channel to send messages!\n')
    await client.log_out()
    if client.is_connected():
        await client.disconnect()


was_started = False


async def check_for_updates():
    if not Api.result:
        Api.best_posts()
    res = Api.get_last_posts(Api.result)
    print(res)


async def check_updates():
    """
    Проверка наличи новых постов в АПИ и отправка лучшего в каждий соответсвующий канал по расписанию
    :return:
    """
    global was_started
    dt_now = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
    dt_now = dt_now.replace(tzinfo=None)
    timer = dt_now.replace(hour=0, minute=3, second=0)
    at_start_update = datetime.strptime(dt_now.strftime(DT_FORMAT), DT_FORMAT)

    morning = datetime.strptime(datetime.now().replace(hour=9, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)
    day = datetime.strptime(datetime.now().replace(hour=12, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)
    evening = datetime.strptime(datetime.now().replace(hour=18, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)

    schedule = [morning, day, evening, at_start_update]
    for posting_time in schedule:
        # Вычислание разницы между нынешним временем и временем в расписании
        dif_hours, dif_minutes, dif_seconds = scheldue_difference.difference(dt_now=dt_now, posting_time=posting_time)
        difference = dt_now.replace(hour=dif_hours, minute=dif_minutes, second=dif_seconds)

        logging.info(f'Difference between {posting_time} and {dt_now} = {difference}| {difference <= timer:}')

        # Если разница между нужным для отправки временем и текущим меньше значения timer
        if difference <= timer:
            if posting_time == at_start_update:
                if was_started is False:
                    was_started = True
                else:
                    continue
            # all_channels = DataBase.ReadChannels()
            # for chName, chId in all_channels:
            #     try:
            #         lower_limit = DataBase.last_update('get', chId)
            #         lower_limit = datetime.strptime(lower_limit, DT_FORMAT)
            #     except TypeError:
            #         lower_limit = datetime.strptime(dt_now.replace(hour=9, minute=0, second=0).strftime(DT_FORMAT),
            #                                         DT_FORMAT)

            # logging.info(f'Search post since {lower_limit} for channel: {chName}')

            # channel_table = key_by_value(channels_info, {'telegram': id_to_link[chId], 'api_id': chId})
            # new_post = (Api.update_post(chId, channel_table, lower_limit, 0),)
            # if len(new_post) > 0 and new_post[0] is not None:
            #
            #     logging.info(f'Found a new post:  {new_post[0].id}, {new_post[0].publish_at}  {new_post[0].url}')
            #     send_time = time.time()
            #     for post_num in range(len(new_post)):
            #         post = new_post[post_num]
            #         try:
            #             await send_post(chId, my_test_id, post, send_time)
            #             logging.info(f'№{post_num}: Send post ({post.url}) and update post_id in DB')
            #
            #         except aiogram.exceptions.RetryAfter as err:
            #             logging.warning(f'№{post_num}: CATCH FLOOD CONTROL for {err.timeout} seconds')
            #             time.sleep(err.timeout)
            #             await send_post(chId, my_test_id, post, send_time)
            #
            #         except aiogram.exceptions.BadRequest as err:
            #             logging.warning(f'№{post_num}: get Bad request: {err} ({post.url})')
            #             try:
            #                 await send_post(chId, my_test_id, post, send_time)
            #             except aiogram.exceptions.BadRequest:
            #                 logging.warning(f'№{post_num}: get repeated Bad request: {err} to ({post.url})')
            #
            #                 continue
            #
            #     new_time = datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
            #     DataBase.last_update('set', chId, new_time)
            # else:
            #     logging.error(
            #         f"No content to send at {datetime.now().astimezone(pytz.timezone('Europe/Kiev'))} {new_post}")


async def clear_channel():
    """
    Очистка всех имеющихся каналов от всех сообщений
    :return:
    """
    client = TelegramClient('clear', api_id, api_hash)
    client.flood_sleep_threshold = 0
    if not client.is_connected():
        await client.connect()
    auth = await client.is_user_authorized()
    if not auth:
        await client.send_code_request(phone)
        user = None
        while user is None:
            code = input('Enter the code you just received: ')
            try:
                user = await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                pw = input('Two step verification is enabled. Please enter your password: ')
                user = client.sign_in(password=pw)

    dialogs = await client.get_dialogs()
    for d in dialogs:
        peer_id = d.message.peer_id
        if isinstance(peer_id, PeerChannel):
            cid = f"-100{peer_id.channel_id}"
            if cid in links:
                messages = [0, 0]
                while len(messages) > 1:
                    messages = await client.get_messages(peer_id.channel_id, limit=400)
                    await client.delete_messages(peer_id.channel_id, [m.id for m in messages])
                    time.sleep(1)
    await client.log_out()
    if client.is_connected():
        await client.disconnect()


async def is_new_posts():
    if not Api.result:
        Api.best_posts()
    print(Api.is_new_memes())
    # print(Api.result[channel_id])
    # if not Api.result:
    #     Api.best_posts()
    # posts = Api.result[channel_id]
    # post_id = posts[-1].id
    # print(post_id)
    # print(posts)
    # url = f"https://api.ifunny.mobi/v4/channels/{channel_id}/items?limit=1"

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        cmd = input('Вот список комманд:\n'
                    '\t1) /mailing :  Рассылка сообщения по всем чатам\n'
                    '\t2) /fill_channels :  начать заполенеие каналов по 1000 лучших постов\n'
                    '\t3) /clear_channels : очистить все сообщения из всех каналов\n'
                    '\t4) /autopost : начать монитроринг новых постов и их отправку по расписанию\n'
                    '\t\t - /exit: to stop the script\n'
                    'Введите вашу команду: ').strip().lower()
        if int(cmd.strip()) == 2:
            logging.info(f'/fill_channels is working')
            loop.run_until_complete(fill_channels())
        elif int(cmd.strip()) == 1:
            loop.run_until_complete(mail())
        elif int(cmd.strip()) == 4:
            logging.info(f'/autopost is working')
            logging.info(f"Start Monitoring at {datetime.now().astimezone(pytz.timezone('Europe/Kiev'))}")
            # while True:
            loop.run_until_complete(is_new_posts())
                # time.sleep(60 * 3)
        elif int(cmd.strip()) == 3:
            logging.info(f'/clear_channels is working')
            loop.run_until_complete(clear_channel())
        elif cmd.strip() == '/exit':
            sys.exit()
