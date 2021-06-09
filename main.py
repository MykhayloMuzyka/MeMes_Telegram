from datetime import datetime

import pytz
from telethon.tl.types import PeerChannel, InputPeerEmpty
from aiogram import executor, Dispatcher, Bot
from telethon.sync import TelegramClient
from localbase import DataBase, TABLES
from telethon import functions, errors
from memes import Api, ImageReader
from settings import *
import logging
import aiogram
import asyncio
import time

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s', filename='logging.log')

logging.warning('Script was Started')
Api = Api()
DataBase = DataBase()

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DataBase.createTables(TABLES)
channels = Api.getChannels()

# Определение существующих каналов, запись из в БД и установка доступа к имени по ID и к Telegram_ID по API_ID
id_to_link = dict()
id_to_name = dict()
for ch_id, ch_name in Api.getChannels():
    id_to_name[ch_id] = ch_name
    for name in channels_info:
        if name in ch_name:
            id_to_link[ch_id] = channels_info[name]['telegram']
            channels_info[name]['api_id'] = ch_id
            DataBase.WriteChannels(ch_id, ch_name, channels_info[name]['telegram'])
channels_info['featured']['api_id'] = 'featured'
id_to_name['featured'] = 'featured'
id_to_link['featured'] = favorite_id
DataBase.WriteChannels('featured', 'featured', favorite_id)


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


async def send_post(channel_id, chat, post, send_time):
    """
    :param channel_id: ID канала из апи для текцщего поста
    :param chat: Telegram ID канала телеграмм для постов этой категории
    :param post: экземпляр класса Post() который нужно отправить в телеграм
    :param send_time: время вызова функции
    :return: True при успешной отправке, иначе False
    """

    message = 0000
    success = True
    post_filetype = post.url.strip()[-3:]
    timeout = abs(2 - float(time.time() - send_time).__round__(2))

    # Если попытка отправиьт сообщение быстрее чем через 2 секунды подождать до этого срока
    if float(time.time() - send_time).__round__(2) < 2:
        time.sleep(timeout)
        logging.info(f'#{post.id}: Timeout before sending =  {timeout}')

    to_send_time = time.time()

    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            message = await bot.send_photo(chat, image.Crop())

        else:
            logging.info(f'№{post.id} Don`t have watermark (no need to crop image) {post.url}')
            message = await bot.send_photo(chat, post.url, post.title)

    elif post_filetype in ('mp4',):
        try:
            message = await bot.send_video(chat, post.url, caption=post.title)
        except:
            try:
                message = await bot.send_video(chat, post.url, caption=post.title)
            except:
                success = False

    elif post_filetype in ('gif',):
        try:
            message = await bot.send_animation(chat, post.url, caption=post.title)
        except:
            success = False
    else:
        logging.warning(f'Unknown Post.type ({post.type}) at {post.url}')
        success = False

    send_time = time.time()
    logging.info(f'№{post.id} send in {float((send_time - to_send_time) * 1000).__round__(2)} ms')

    if success:  # Есди пост был отправлен то добавить информацию о нем в БД
        DataBase.AddPost(message.message_id, post, key_by_value(channels_links, chat))
        DataBase.Last_id('set', channel_id, post.id)
        DataBase.lastUpdate('set', channel_id, datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT))
        return True
    return False


async def fill_channels():
    """
    Функция заполнения всех имеющихся телеграм каналов тысячей лучших постов в каждом
    :return:
    """

    best_memes = Api.BestPosts()

    for channel_id in best_memes:
        last_post_id = DataBase.Last_id('get', channel_id)

        # Если заполнение было прерввано то поиск поста с которого нужно продолжить
        for post_num, post in enumerate(best_memes[channel_id]):
            if post.id == last_post_id:
                best_memes[channel_id] = best_memes[channel_id][post_num + 1:]
                break

        for post_num, post in enumerate(best_memes[channel_id]):
            send_time = time.time()
            try:
                await send_post(channel_id, id_to_link[channel_id], best_memes[channel_id][post_num], send_time)
                logging.info(f' № {post_num}: Send post ({post.url}) and update post_id in DB')

            except aiogram.exceptions.RetryAfter as err:
                logging.warning(f'№{post_num}: CATCH FLOOD CONTROL for {err.timeout} seconds')
                time.sleep(err.timeout)
                await send_post(channel_id, id_to_link[channel_id], best_memes[channel_id][post_num], send_time)

            except aiogram.exceptions.BadRequest as err:
                logging.warning(f'№{post_num}: get Bad request: {err} ({post.url})')
                await send_post(channel_id, id_to_link[channel_id], best_memes[channel_id][post_num], send_time)

            except Exception as err:
                logging.error(f'fill_channels unknown error : {err}')
        last_time = datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
        DataBase.lastUpdate('set', channel_id, last_time)


was_started = False


async def CheckUpdates():
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
        diff = (dt_now - posting_time).__abs__().total_seconds()
        dif_hours = int(diff // 3600)
        dif_minutes = int((diff % 3600) // 60)
        dif_seconds = int(diff % 60)

        difference = dt_now.replace(hour=dif_hours, minute=dif_minutes, second=dif_seconds)
        logging.info(f'Difference between {posting_time} and {dt_now} = {difference}| {difference <= timer:}')

        # Если разница между нужным для отправки временем и текущим меньше значения timer
        if difference <= timer:

            if posting_time == at_start_update:
                if was_started is False:
                    was_started = True
                else:
                    continue
            all_channels = DataBase.ReadChannels()
            for chName, chId in all_channels:
                try:
                    lower_limit = DataBase.lastUpdate('get', chId)
                    lower_limit = datetime.strptime(lower_limit, DT_FORMAT)
                except TypeError:
                    lower_limit = datetime.strptime(dt_now.replace(hour=9, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)

                logging.info(f'Search post since {lower_limit} for channel: {chName}')

                channel_table = key_by_value(channels_info, {'telegram': id_to_link[chId], 'api_id': chId})
                new_post = (Api.UpdatePost(chId, channel_table, lower_limit, 0),)
                if len(new_post) > 0 and new_post[0] is not None:

                    logging.info(f'Found a new post:  {new_post[0].id}, {new_post[0].publish_at}  {new_post[0].url}')
                    send_time = time.time()
                    for post_num in range(len(new_post)):
                        post = new_post[post_num]
                        try:
                            await send_post(chId, id_to_link[chId], post, send_time)
                            logging.info(f'№{post_num}: Send post ({post.url}) and update post_id in DB')

                        except aiogram.exceptions.RetryAfter as err:
                            logging.warning(f'№{post_num}: CATCH FLOOD CONTROL for {err.timeout} seconds')
                            time.sleep(err.timeout)
                            await send_post(chId, id_to_link[chId], post, send_time)

                        except aiogram.exceptions.BadRequest as err:
                            logging.warning(f'№{post_num}: get Bad request: {err} ({post.url})')
                            try:
                                await send_post(chId, id_to_link[chId], post, send_time)
                            except aiogram.exceptions.BadRequest:
                                logging.warning(f'№{post_num}: get repeated Bad request: {err} to ({post.url})')

                                continue

                    new_time = datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
                    DataBase.lastUpdate('set', chId, new_time)
                else:
                    logging.error(f"No content to send at {datetime.now().astimezone(pytz.timezone('Europe/Kiev'))} {new_post}")


async def ClearChannel():
    """
    Очистка всех имеющихся каналов от всех сообщений
    :return:
    """
    all_chats = list(channels_links.values())
    all_chats.append(favorite_id)
    to_clear = list()

    # Создание сессии в Telegram_API
    client = TelegramClient('clear', api_id, api_hash)
    is_connected = client.is_connected()
    if not is_connected:
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
                user = await client.sign_in(password=pw)

    get_dialogs = functions.messages.GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=30,
        hash=0
    )
    # Узнать все каналы котороые есть
    dialogs = await client(get_dialogs)

    chats = {}

    for c in dialogs.chats:
        chats[c.id] = c

    for d in dialogs.dialogs:
        peer = d.peer
        if isinstance(peer, PeerChannel):
            # Есди канал один из тех что нам нужен добавиьт в список очистки
            peer_id = peer.channel_id
            channel = chats[peer_id]
            access_hash = channel.access_hash
            dialog_name = channel.title
            if dialog_name in channels_links.keys() or dialog_name in 'TikTok Приколы':
                to_clear.append([peer_id, access_hash])

        else:
            continue

    for chat_id, access_hash in to_clear:
        chat = PeerChannel(int(chat_id))
        # Отправить сообщение для отпределения посленего Message ID в канале
        start = await client.send_message(chat, 'Abraandelabra')

        to_delete = list(range(0, start.id + 1))
        to_delete.reverse()
        messages_count = len(to_delete)

        while True:
            try:
                chunk = to_delete[messages_count - 100:messages_count]
                if messages_count < 100:
                    chunk = to_delete[0:messages_count]

                await client.delete_messages(chat, chunk)
                if to_delete[0] in chunk or messages_count < 0:
                    break
                messages_count = messages_count - 100
            except Exception as err:
                logging.error(f'Cleaning chat: {chat}, {err}')
                break

        await client.delete_messages(chat, start.id)
    if client.is_connected():
        await client.disconnect()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        qes = input('Сделать отправку постов вне расписания при мониторинге?| y/n :\n').strip().lower()
        if qes == 'n':
            was_started = True
            break
        elif qes == 'y':
            break
        else:
            pass

    while True:
        cmd = input('Вот список комманд:\n'
                    '\t- /fill_channels :  начать заполенеие каналов по 1000 лучших постов\n'
                    '\t- /clear_channels : очистить все сообщения из всех каналов\n'
                    '\t- /autopost : начать монитроринг новых постов и их отправку по расписанию\n'
                    '\t\t - /exit: to stop the script\n'
                    'Введите вашу команду :').strip().lower()
        if cmd == '/fill_channels':
            loop.run_until_complete(fill_channels())
        elif cmd == '/autopost':
            logging.info(f"Start Monitoring at {datetime.now().astimezone(pytz.timezone('Europe/Kiev'))}")
            while True:
                loop.run_until_complete(CheckUpdates())
                time.sleep(60 * 3)
        elif cmd == '/clear_channels':
            loop.run_until_complete(ClearChannel())
        elif cmd == '/exit':
            sys.exit()

