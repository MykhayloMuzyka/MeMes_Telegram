import asyncio
import logging
import threading
import time
# from MeMes_Telegram.db.localbase import DataBase, TABLES
from datetime import datetime, timedelta

import aiogram
import pytz
import telebot
from telebot import TeleBot
from telethon import errors
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel, MessageMediaPhoto, MessageMediaDocument

from MeMes_Telegram.confgis.settings import *
from MeMes_Telegram.memes import Api, ImageReader, Post

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s', filename='logging.log')

logging.warning('Script was Started')
utc = pytz.UTC
bot = TeleBot(token=TOKEN)
# dp = Dispatcher(bot)
Api = Api()
# DataBase = DataBase()
# DataBase.create_tables(TABLES)
channels = Api.get_channels()
id_to_link = dict()
id_to_name = dict()
was_working = False

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

links = [i for i in channels_links.values()]
client = None


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


async def lastChannelsPublicationTime() -> dict:
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
                res[str(cid)] = None
                for m in messages:
                    if m.media:
                        # проверяем, присутствует ли в сообщении медиа
                        if isinstance(m.media, MessageMediaPhoto) or isinstance(m.media, MessageMediaDocument):
                            # проверка, являеться ли медиа фото
                            res[str(cid)] = m.date + timedelta(hours=3)
                        break
    return res


def uniqueByURL(list_of_oblects: list) -> list:
    """
    Функция поиска и удаления дубикатов url постов из списка обьектов Post()
    :param list_of_oblects: список обьектов типа Post()
    :return: очищенный от дубликатов список
    """
    if len(list_of_oblects) == 0:
        return []
    res = [list_of_oblects[0]]
    urls = [list_of_oblects[0].url]
    for obj in list_of_oblects:
        if obj.url not in urls:
            res.append(obj)
            urls.append(obj.url)
    return res


async def logIn() -> TelegramClient:
    """
    Функция входа в телеграм аккаунт
    :return: обьект авторизированого клиента
    """
    client = TelegramClient('admin', api_id, api_hash)
    client.flood_sleep_threshold = 0
    is_connected = client.is_connected()
    if not is_connected:
        await client.connect()
    auth = await client.is_user_authorized()
    if not auth:
        user = None
        while user is None:
            await client.send_code_request(phone)
            user = None
            code = input('Enter the code you just received: ')
            try:
                int(code)
            except Exception:
                print('\nCode must be the number!\n')
            try:
                user = await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                pw = input('Two step verification is enabled. Please enter your password: ')
                try:
                    user = await client.sign_in(password=pw)
                except errors.rpcerrorlist.PasswordHashInvalidError:
                    print('Wrong password')
            except errors.rpcerrorlist.PhoneCodeInvalidError:
                print('\nWrong code!\n')
                time.sleep(5)
    return client


async def logOut():
    """
    Функция выхода из Телеграм аккаунта
    """
    await client.log_out()
    if client.is_connected():
        await client.disconnect()


async def send_post(channel_id: str, chat: int, post: Post, send_time=0):
    """
    :param channel_id: ID канала из апи для текцщего поста
    :param chat: Telegram ID канала телеграмм для постов этой категории
    :param post: экземпляр класса Post() который нужно отправить в телеграм
    :param client: авторизованный клиент
    :param send_time: время вызова функции, по умолчанию 0
    :return: True при успешной отправке поста, False в ином случае
    """
    post_filetype = post.url.strip()[-3:]
    if send_time != 0:
        timeout = abs(2 - float(time.time() - send_time).__round__(2))
        if float(time.time() - send_time).__round__(2) < 2:
            time.sleep(timeout)
            logging.info(f'Post: Timeout before sending =  {timeout}')

    if channel_id != 'featured':
        if post.title:
            caption = f"<b>{post.title}</b>\n\n<a href='{main_channnel_inv_link}'>Улётные приколы😂</a>"
        else:
            caption = f"<a href='{main_channnel_inv_link}'>Улётные приколы😂</a>"
    else:
        caption = f"<b>{post.title}</b>"

    # to_send_time = time.time()
    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            try:
                message = bot.send_photo(chat, image.crop(), caption=caption, parse_mode='HTML')
            except Exception as e:
                logging.info('Cant send', e)
                return False
        else:
            logging.info(f'Post Don`t have watermark (no need to crop image) {post.url}')
            try:
                message = bot.send_photo(chat, post.url, caption=caption, parse_mode='HTML')
            except Exception as e:
                logging.info('Cant send', e)
                return False

    elif post_filetype == 'mp4':
        try:
            message = bot.send_video(chat, post.url, caption=caption, parse_mode='HTML')
        except Exception as e:
            logging.info('Cant send video', caption, e)
            return False
    elif post_filetype == 'gif':
        try:
            message = bot.send_animation(chat, post.url, caption=caption, parse_mode='HTML')
        except Exception as e:
            logging.info(f'Cant send animation {post.url}', e)
            return False
    # logging.info(f'№{id} send in {float((send_time - to_send_time) * 1000).__round__(2)} ms')
    # Есди пост был отправлен то добавить информацию о нем в БД
    # DataBase.add_post(message.message_id, post, key_by_value(channels_links, chat))
    # DataBase.last_id('set', channel_id, post.id)
    # DataBase.last_update('set', channel_id,
    #                      datetime.now().astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT))
    return True


async def fill_channels():
    """
    Функция заполнения всех имеющихся телеграм каналов тысячей лучших постов в каждом
    """
    Api.result = dict()
    lastPostTimes = await lastChannelsPublicationTime()
    try:
        all_memes = Api.all_posts()
        all_new_posts = dict()
        best_new_posts = dict()
        for channel_id in all_memes:
            all_new_posts[channel_id] = []
            try:
                if lastPostTimes[id_to_link[channel_id]]:
                    lastPostTime = lastPostTimes[id_to_link[channel_id]]
                    for post_num, post in enumerate(all_memes[channel_id]):
                        if utc.localize(post.publish_at) > lastPostTime:
                            all_new_posts[channel_id].append(post)
                else:
                    for post_num, post in enumerate(all_memes[channel_id]):
                        all_new_posts[channel_id].append(post)
                best_new_posts[channel_id] = sorted(all_new_posts[channel_id], key=lambda post: post.smiles)
                if len(best_new_posts[channel_id]) > 50:
                    best_new_posts[channel_id] = best_new_posts[channel_id][len(best_new_posts[channel_id]) - 50:]
            except KeyError as e:
                print(e)
        for channel_id in best_new_posts:
            print(len(best_new_posts[channel_id]))
            best_new_posts[channel_id] = uniqueByURL(best_new_posts[channel_id])
            print(len(best_new_posts[channel_id]))
            for post_num, post in enumerate(best_new_posts[channel_id]):
                print(post_num, post.url)
                try:
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except aiogram.exceptions.RetryAfter as err:
                    logging.warning(f'№{post_num}: CATCH FLOOD CONTROL for {err.timeout} seconds')
                    time.sleep(err.timeout)
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except aiogram.exceptions.BadRequest as err:
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except errors.rpcerrorlist.ChatAdminRequiredError:
                    print('\nYou must be admin of the channel to send messages!\n')
                    break
                except Exception as err:
                    print(f'fill_channels unknown error : {err}')
                time.sleep(3)
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of the channel to send messages!\n')


async def mail(msg: str):
    """
    Функция розсылки сообщения по всем каналам
    :param msg: сообщение, которое необходимо разослать
    """
    try:
        for link in links:
            bot.send_message(int(link), msg)
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of the channel to send messages!\n')


was_started = False


async def clear_channel():
    """
    Очистка всех имеющихся каналов от всех сообщений
    """
    try:
        dialogs = await client.get_dialogs()
        for d in dialogs:
            peer_id = d.message.peer_id
            if isinstance(peer_id, PeerChannel):
                cid = f"-100{peer_id.channel_id}"
                if cid in links:
                    messages = [0, 0]
                    # await client.send_message(int(cid), 'test')
                    while len(messages) > 1:
                        messages = await client.get_messages(peer_id.channel_id, limit=400)
                        for m in messages:
                            try:
                                bot.delete_message(int(cid), m.id)
                            except telebot.apihelper.ApiException:
                                print(f'Cant delete message {m.id}')
                        time.sleep(1)
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of the channel to clear it!\n')


async def is_new_posts():
    """
    Вытягивает дату последней публикации с приложения по каждой категории и сверяет с датой последней публикации
    телеграм канала. Если публикация новая, то отправляеться в соответствующий канал.
    """
    while was_working:
        now = datetime.now()
        print(f'\n{now.hour}:{now.minute}')
        if not was_working:
            break
        if now.hour in (8, 11, 17) and now.minute == 58:
            Api.new_posts = dict()
            if was_working:
                last_channel_pubs = await lastChannelsPublicationTime()
                last_api_pubs = Api.is_new_memes()
                print(last_api_pubs)
            else:
                break
            if was_working:
                for key in last_channel_pubs:
                    if last_channel_pubs[key]:
                        if last_channel_pubs[key] < utc.localize(
                                last_api_pubs[key_by_value(id_to_link, key)].publish_at) and was_working:
                            print(last_channel_pubs[key],
                                  utc.localize(last_api_pubs[key_by_value(id_to_link, key)].publish_at))
                            await send_post(key_by_value(id_to_link, key), int(key),
                                            last_api_pubs[key_by_value(id_to_link, key)])
                            time.sleep(1)
                    else:
                        await send_post(key_by_value(id_to_link, key), int(key),
                                        last_api_pubs[key_by_value(id_to_link, key)])
                        time.sleep(1)
            else:
                break
        time.sleep(60)


def stopWorking():
    global was_working
    print('/exit to stop the script')
    cmd = ''
    while cmd != '/exit':
        cmd = input()
    print('Stopping...\nThis can take up to a minute')
    was_working = False


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        cmd = input('Вот список комманд:\n'
                    '\t1) /login : Ввойти в аккаунт Телеграм\n'
                    '\t2) /logout : Выйти из аккаунта Телеграм\n'
                    '\t3) /mailing :  Рассылка сообщения по всем чатам\n'
                    '\t4) /fill_channels :  начать заполенеие каналов по 1000 лучших постов\n'
                    '\t5) /clear_channels : очистить все сообщения из всех каналов\n'
                    '\t6) /autopost : начать монитроринг новых постов и их отправку по расписанию\n'
                    'Введите вашу команду: ').strip().lower()
        try:
            if int(cmd.strip()) == 1:
                if not client:
                    client = loop.run_until_complete(logIn())
                else:
                    print('\nYou have already logged in!\n')
            elif int(cmd.strip()) == 2:
                if client:
                    loop.run_until_complete(logOut())
                    client = None
            elif int(cmd.strip()) == 3:
                msg = input('Enter your message: ')
                loop.run_until_complete(mail(msg))
            elif int(cmd.strip()) == 4:
                if client:
                    print('Filling...')
                    loop.run_until_complete(fill_channels())
                else:
                    print('\nYou have to log in firstly!\n')
            elif int(cmd.strip()) == 5:
                if client:

                    conf = input('Do you really want to clear all channels? y/n\n')
                    if conf == 'y':
                        print('Clearing...')
                        loop.run_until_complete(clear_channel())
                else:
                    print('\nYou have to log in firstly!\n')
            elif int(cmd.strip()) == 6:
                if client:
                    was_working = True
                    print('\nStart threading...')
                    t = threading.Thread(target=stopWorking)
                    t.start()
                    loop.run_until_complete(is_new_posts())
                    t.join()
                else:
                    print('\nYou have to log in firstly!\n')
        except ValueError:
            print('\nCommand must be a number!\n')
