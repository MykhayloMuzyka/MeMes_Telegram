#! /usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import pickle
import sys
import time
from datetime import datetime, timedelta
import os

import aiogram
import pytz
from telebot import TeleBot
from telethon import errors

from confgis.settings import *
from memes import Api, ImageReader, Post

here = os.path.dirname(os.path.abspath(__file__))


def getAction():
    """
    Возвращает последние действие
    """
    with open(os.path.join(here, "action.txt"), 'r') as f:
        return f.read()


def setAction(action: str):
    """
    Перезаписывает последние действие
    """
    with open(os.path.join(here, "action.txt"), 'w') as f:
        f.write(action)


def getCounters():
    """
    Считывает с файла numbers.pickle словарь
    :return: каунтеры постов для каждого канала
    """
    try:
        with open(os.path.join(here, "numbers.pickle"), 'rb') as f:
            res = pickle.load(f)
    except EOFError:
        res = dict()
        for channel_id, _ in channels:
            if channel_id != '6058bdbcf89e242f997d006d':
                res[channel_id] = 0
        res['featured'] = 0
    return res


def changeCounters(numbers: dict):
    """
    Перезаписывает файл numbers.pickle
    """
    with open(os.path.join(here, "numbers.pickle"), 'wb') as f:
        pickle.dump(numbers, f)


def uniqueByURL(list_of_oblects: list):
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


Api = Api()
channels = Api.get_channels() + [['featured', 'featured']]
id_to_link = dict()
id_to_name = dict()
for ch_id, ch_name in channels:
    id_to_name[ch_id] = ch_name
    for name in channels_info:
        if name in ch_name:
            id_to_link[ch_id] = channels_info[name]['telegram']
            channels_info[name]['api_id'] = ch_id
channels_info['featured']['api_id'] = 'featured'
id_to_name['featured'] = 'featured'
id_to_link['featured'] = favorite_id
links = [i for i in channels_links.values()]
client = None
was_started = False


def getMemesByDate(year: int, month: int, day: int):
    """
    Возвращает все посты за заданный день по всем категориям
    :param year: год
    :param month: месяц
    :param day: день
    :return: словарь (ключ - идентификатор канала, значения - все посты за заданый день по этой категории)
    """
    res = dict()
    all_memes = Api.all_posts()
    for channel_id, _ in channels:
        if channel_id != '6058bdbcf89e242f997d006d':
            res[channel_id] = []
            for post in all_memes[channel_id]:
                if post.publish_at.year == year and post.publish_at.month == month and post.publish_at.day == day:
                    res[channel_id].append(post)
            res[channel_id] = sorted(res[channel_id], key=lambda post: post.smiles)
            res[channel_id] = uniqueByURL(res[channel_id])
        time.sleep(10)
    return res


logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s', filename='logging.log')

logging.warning('Script was Started')
utc = pytz.UTC

was_working = False
bot = TeleBot(TOKEN_ADMIN)

# posts = getMemesByDate(2021, 11, 4)
# for ch_id in posts:
#     print(id_to_name[ch_id])
#     c = 1
#     for post in posts[ch_id]:
#         print(f"{c}) {post.url} {post.publish_at} {post.smiles}")
#         c += 1
# with open(os.path.join(here, "posts.pickle"), 'wb') as f:
#     pickle.dump(posts, f)

try:
    with open(os.path.join(here, "posts.pickle"), 'rb') as f:
        posts_for_pubblishing = pickle.load(f)
except EOFError:
    posts_for_pubblishing = dict()
    for channel_id, _ in channels:
        if channel_id != '6058bdbcf89e242f997d006d':
            posts_for_pubblishing[channel_id] = []
    posts_for_pubblishing['featured'] = []
except FileNotFoundError:
    posts_for_pubblishing = dict()
    for channel_id, _ in channels:
        if channel_id != '6058bdbcf89e242f997d006d':
            posts_for_pubblishing[channel_id] = []
    posts_for_pubblishing['featured'] = []

# for ch_id in posts_for_pubblishing:
#     print(id_to_name[ch_id])
#     c = 1
#     for post in posts_for_pubblishing[ch_id]:
#         print(f"{c}) {post.url} {post.publish_at} {post.smiles}")
#         c += 1


def counts():
    with open(os.path.join(here, "posts.pickle"), 'rb') as f:
        temp_lists = pickle.load(f)
    res = ''
    for ch_id in temp_lists:
        res += f'{id_to_name[ch_id]} {len(temp_lists[ch_id])}\n'
    return res


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


id = key_by_value(id_to_link, '-1001367691516')
del posts_for_pubblishing[id][-5]
del posts_for_pubblishing[id][-6]
del posts_for_pubblishing[id][-7]
with open(os.path.join(here, "posts.pickle"), 'wb') as f:
    pickle.dump(posts_for_pubblishing, f)


def setLastChannelsPublicationTime(ch_link):
    last_times = lastChannelsPublicationTime()
    last_times[ch_link] = datetime.now()
    with open(os.path.join(here, "lastPubsTime.pickle"), 'wb') as f:
        pickle.dump(last_times, f)


def lastChannelsPublicationTime():
    """
    Определяет время последнего поста в каждом канале
    :return: словарь, где ключем являеться ссылка на канал, а значением - время последней публикации в нем
    """
    with open(os.path.join(here, "lastPubsTime.pickle"), 'rb') as f:
        return pickle.load(f)


def getLastPostTime(posts):
    last = posts[0].publish_at
    for post in posts:
        if post.publish_at > last:
            last = post.publish_at
    return last


async def send_post(channel_id: str, chat: int, post: Post):
    """
    :param channel_id: ID канала из апи для текцщего поста
    :param chat: Telegram ID канала телеграмм для постов этой категории
    :param post: экземпляр класса Post() который нужно отправить в телеграм
    :return: True при успешной отправке поста, False в ином случае
    """
    numbers = getCounters()
    post_nums = numbers[channel_id]
    post_filetype = post.url.strip()[-3:]
    if post_nums % 4 == 0:
        caption = "<a href='" + 'https://t.me/idaprikol_memes' + "'>Подборка лучших приколов по категориям: Мемы Видео Девушки Животные Позалипать Жизненно Отношения</a>"
    elif post_nums % 4 == 1:
        caption = "<a href='" + 'https://t.me/memes_smeshnye_video' + "'>Улётные приколы😂</a>"
    elif post_nums % 4 == 2:
        caption = "<a href='" + 'https://t.me/video_films_online' + "'>Фильмы бесплатно , без рекламы</a>"
    else:
        caption = "<a href='" + 'https://t.me/audiobooks_storage' + "'>Аудиокниги бесплатно, без рекламы</a>"

    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            try:
                bot.send_photo(chat, image.crop(), caption=caption, parse_mode='HTML')
                setLastChannelsPublicationTime(str(chat))
            except Exception as e:
                logging.info('Cant send', e)
                return False
        else:
            logging.info('Post Don`t have watermark (no need to crop image) ' + post.url)
            try:
                bot.send_photo(chat, post.url, caption=caption, parse_mode='HTML')
                setLastChannelsPublicationTime(str(chat))
            except Exception as e:
                logging.info('Cant send', e)
                return False

    elif post_filetype == 'mp4':
        try:
            bot.send_video(chat, post.url, caption=caption, parse_mode='HTML')
            setLastChannelsPublicationTime(str(chat))
        except Exception as e:
            logging.info('Cant send video', caption, e)
            return False
    elif post_filetype == 'gif':
        try:
            bot.send_animation(chat, post.url, caption=caption, parse_mode='HTML')
            setLastChannelsPublicationTime(str(chat))
        except Exception as e:
            return False
    numbers[channel_id] += 1
    changeCounters(numbers)
    return True


async def fill_channels():
    """
    Функция заполнения всех имеющихся телеграм каналов тысячей лучших постов в каждом
    """
    print('Gathering all memes...')
    Api.result = dict()
    lastPostTimes = lastChannelsPublicationTime()
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
                if len(best_new_posts[channel_id]) > 300:
                    best_new_posts[channel_id] = best_new_posts[channel_id][len(best_new_posts[channel_id]) - 300:]
            except KeyError as e:
                print(e)
        print('Filling channels...')
        counter = 0
        print('\n')
        for channel_id in best_new_posts:
            best_new_posts[channel_id] = uniqueByURL(best_new_posts[channel_id])
            amount = len(best_new_posts[channel_id])
            for post_num, post in enumerate(best_new_posts[channel_id]):
                p = round((post_num + 1) / amount * 100)
                sys.stdout.write(
                    '\r' + str(counter + 1) + ' of ' + str(len(links)) + ' channels is filling: ' + str(
                        p) + '% ' + '#' * (int(p // 2)) + '_' * (
                        int(50 - p // 2)))
                try:
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except aiogram.exceptions.RetryAfter as err:
                    logging.warning('№' + str(post_num) + ': CATCH FLOOD CONTROL for ' + str(err.timeout) + ' seconds')
                    time.sleep(err.timeout)
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except aiogram.exceptions.BadRequest as err:
                    await send_post(channel_id, int(id_to_link[channel_id]), post)
                except errors.rpcerrorlist.ChatAdminRequiredError:
                    print('\nYou must be admin of the channel to send messages!\n')
                    break
                except Exception as err:
                    print('fill_channels unknown error: ' + str(err))
                time.sleep(3)
            counter += 1
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of the channel to send messages!\n')


async def mail(msg: str):
    """
    Функция розсылки сообщения по всем каналам
    :param msg: сообщение, которое необходимо разослать
    """
    counter = 1
    try:
        print('\n')
        for link in links:
            sys.stdout.write('\rMessage is sended to ' + str(counter) + ' of ' + str(len(links)) + ' channels')
            counter += 1
            bot.send_message(int(link), msg)
    except errors.rpcerrorlist.ChatAdminRequiredError:
        print('\nYou must be admin of the channel to send messages!\n')


async def is_new_posts():
    """
    В 08:00 каждый день пополняет словарь новыми постами. В 9:00, 12:00 и 18:00 заполняет каналы
    """
    while was_working:
        now = datetime.now() + timedelta(hours=2)
        yesterday = now - timedelta(days=1)
        if now.hour == 8 and now.minute == 0:
            today_posts = getMemesByDate(yesterday.year, yesterday.month, yesterday.day)
            with open(os.path.join(here, "posts.pickle"), 'rb') as f:
                posts_for_pubblishing = pickle.load(f)
            for channel_id in posts_for_pubblishing:
                posts_for_pubblishing[channel_id] += today_posts[channel_id]
            with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                pickle.dump(posts_for_pubblishing, f)

        elif now.hour in (9, 12, 18) and now.minute == 0:
            if was_working:
                with open(os.path.join(here, "posts.pickle"), 'rb') as f:
                    posts_for_pubblishing = pickle.load(f)
                for channel_id in posts_for_pubblishing:
                    if posts_for_pubblishing[channel_id]:
                        try:
                            await send_post(channel_id, int(id_to_link[channel_id]), posts_for_pubblishing[channel_id][-1])
                            del posts_for_pubblishing[channel_id][-1]
                            with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                                pickle.dump(posts_for_pubblishing, f)
                        except aiogram.exceptions.RetryAfter as err:
                            logging.warning('Post: CATCH FLOOD CONTROL for ' + str(err.timeout) + ' seconds')
                            time.sleep(err.timeout)
                            await send_post(channel_id, int(id_to_link[channel_id]), posts_for_pubblishing[channel_id][-1])
                            del posts_for_pubblishing[channel_id][-1]
                            with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                                pickle.dump(posts_for_pubblishing, f)
                        except aiogram.exceptions.BadRequest:
                            await send_post(channel_id, int(id_to_link[channel_id]), posts_for_pubblishing[channel_id][channel_id][-1])
                            del posts_for_pubblishing[channel_id][-1]
                            with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                                pickle.dump(posts_for_pubblishing, f)
                time.sleep(60)
            else:
                break
    setAction('menu')


async def sendOnePostToEachChannel():
    with open(os.path.join(here, "posts.pickle"), 'rb') as f:
        posts_for_pubblishing = pickle.load(f)
    for channel_id in posts_for_pubblishing:
        if posts_for_pubblishing[channel_id]:
            try:
                await send_post(channel_id, int(id_to_link[channel_id]), posts_for_pubblishing[channel_id][-1])
                del posts_for_pubblishing[channel_id][-1]
                with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                    pickle.dump(posts_for_pubblishing, f)
            except aiogram.exceptions.RetryAfter as err:
                logging.warning('Post: CATCH FLOOD CONTROL for ' + str(err.timeout) + ' seconds')
                time.sleep(err.timeout)
                await send_post(channel_id, int(id_to_link[channel_id]), posts_for_pubblishing[channel_id][-1])
                del posts_for_pubblishing[channel_id][-1]
                with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                    pickle.dump(posts_for_pubblishing, f)
            except aiogram.exceptions.BadRequest:
                await send_post(channel_id, int(id_to_link[channel_id]),
                                posts_for_pubblishing[channel_id][channel_id][-1])
                del posts_for_pubblishing[channel_id][-1]
                with open(os.path.join(here, "posts.pickle"), 'wb') as f:
                    pickle.dump(posts_for_pubblishing, f)


