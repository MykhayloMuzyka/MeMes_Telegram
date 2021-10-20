import logging
import threading
import time
import urllib.request
import cv2
import numpy as np
import requests
from PIL import Image
from datetime import datetime
from typing import Union
import pytz
from confgis.settings import *
import os

links = [i for i in channels_links.values()]
utc = pytz.UTC
here = os.path.dirname(os.path.abspath(__file__))


class Post:
    def __init__(self, item, channel):
        """
        :param item: значение из списка items  в словаре из json файла присланного API
        :param channel: iD канала которое указано в API
        """
        self.id = item['id']
        self.type = item['type']  # тип поста (картинка, видео, или анимация)
        self.title: str = item['title']  # названия значения из списка items
        self.url: str = item['url']
        self.link = item['link']  # ссылка на item
        self.channel = channel
        self.publish_at = datetime.fromtimestamp(item['publish_at'])  # время появления поста в API
        self.smiles = item['num']['smiles']  # Количество "лайков" набранного поста на исходном сайте
        self.sm_per_hour = None  # вычисляемый параметр "лайков в час" для выбора потенциально лучшего поста

    def life_time(self):
        """
        Метод для определения втого времени как долго пост существует в АПИ на момент вызова метода
        :return: целое число минут жизни поста
        """
        dt_now_tz = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
        dt_now = dt_now_tz.replace(tzinfo=None)
        return int((dt_now - self.publish_at).total_seconds().__round__(0) / 3600)


class ImageReader:
    def __init__(self, post: Post):
        """
        :param post: экземарял класса Post() который нужно обработать
        """
        img = urllib.request.urlopen(post.url).read()
        out = open(os.path.join(here, "img/img.jpg"), "wb")
        out.write(img)
        out.close()
        self.path = os.path.join(here, "img/img.jpg")
        self.pic = Image.open(self.path)

    def watermark(self):
        """
        Проверка поста на наличие вотермарки в нижней части изображения
        :return: True если вотермарка была найдена иначе  False
        """
        start_time = time.time()
        img_main = Image.open(self.path)
        img_template = Image.open(os.path.join(here, "img/temp.jpg"))  # шаблон вотермарки статически хранящийся в проекте
        t_width, t_height = img_template.size
        width, height = img_main.size
        box = (width - t_width - 50, height - t_height - 50, width, height)
        img_main = img_main.crop(box)
        img_gray = cv2.cvtColor(np.float32(img_main), cv2.COLOR_BGR2GRAY)
        img_template = cv2.cvtColor(np.float32(img_template), cv2.COLOR_BGR2GRAY)
        w, h = img_template.shape[::-1]
        res = cv2.matchTemplate(img_gray, img_template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.8)
        points = zip(*loc[::-1])
        counter = 0
        for pt in points:
            counter += 1
            cv2.rectangle(np.float32(img_main), pt, (pt[0] + w, pt[1] + h), (255, 0, 0), 4)  # при первом совпадении выход из поиска
            break
        if counter == 1:  # если было совпадение поврат True
            logging.info(f'\t\tWATERMARK time = {float(time.time() - start_time).__round__(2) * 1000} ms')

            return True
        return False

    def crop(self):
        """
        Обрезка нижней части изображения для избаления от вотермарки
        :return: обрезанный вариант изображения в виде открытого файла
        """
        start_time = time.time()
        width, height = self.pic.size
        box = (0, 0, width, height - 20)
        crop_img = self.pic.crop(box)
        crop_img.save(os.path.join(here, "img/cropped.jpg"), quality=90)
        logging.info(f'\t\tCROP time = {float(time.time() - start_time).__round__(2) * 1000} ms')

        return open(os.path.join(here, "img/cropped.jpg"), 'rb')


def isDictFull(res: dict, num: int)\
        :
    """
    Проверяет, заполнен ли словарь до конца
    :param res: проверяеммый словарь
    :param num: ожидаеммый размер словаря
    :return: True если заполнен, False в ином случае
    """
    if len(res) < num:
        return False
    for key in res:
        if not res[key]:
            return False
    return True


class Api:
    result = dict()
    new_posts = dict()

    def __init__(self):
        self.headers = {
            'Accept': 'application/json,image/jpeg,image/webp,video/mp4',
            'iFunny-Project-Id': 'Russia',
            'Accept-Language': 'ru-RU',
            'Messaging-Project': 'idaprikol.ru:idaprikol-60aec',
            'ApplicationState': '1',
            'Authorization': "Basic MDIzNTYxMzY2NDYxMzY2MzMzMkQ2NDMyMzU2MzJEMzQ2MzY0NjQyRDM4Mzg2MzM1MkQzMDMyMzQzNjYy"
                             "MzkzOTMxNjEzNjY2MzZfUHpuNEQxMnNvSzo5Nzg0ZjE2MzZlYzdhYjE4YmI5YzczNmNhZjg0MzY1Mzc3M2M5Y2Mz",
            'Host': 'api.ifunny.mobi',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'iDaPrikol/6.15.4(1119163) Android/6.0 (Xiaomi; Redmi Note 4; Xiaomi)',
        }
        self.channels_url = 'https://api.ifunny.mobi/v4/channels'

        self.lower_limit = None

    def get_channels(self):
        """
        :return: Список категорий в АПИ в виде ([id_1, name_1], [id_2, name_2], ...) или False в случае неудачи
        """
        result = list()
        channels = requests.get(self.channels_url, headers=self.headers)
        if channels.status_code == 200:
            for item in channels.json()['data']['channels']['items']:
                result.append([item['id'], item['name']])
            return result
        return False

    def threading_all_posts(self, posts: list, channel_info: str):
        """Берет посты посты по которым нужно пройтись и собрать информацию, channel_info текущего канала"""
        all_posts = []
        for i in posts:
            content = i['data']['content']
            next_page = content['paging']['cursors']['next']
            requests_time = 0
            while content['paging']['hasNext'] is not False:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1000&next={next_page}"
                if channel_info[0] == 'featured':
                    url = f"https://api.ifunny.mobi/v4/feeds/featured?limit=1000&next={next_page}"
                start_request = time.time()
                posts = requests.get(url, headers=self.headers).json()
                requests_time += time.time() - start_request
                content = posts['data']['content']
                items = content['items']
                try:
                    next_page = content['paging']['cursors']['next']
                except KeyError:
                    print(channel_info, content['paging']['cursors'])
                filtered = list(Post(item, channel_info[0]) for item in items)
                all_posts += filtered
            self.result[channel_info[0]] = all_posts

    def all_posts(self):
        """
        Проход по всем существующим постам в АПИ по всем имеющимся катерогиям
        для сббора всех постов
        :return: dict() : dict[channel_id] = list(Post(), Post(), ...)
            словарь хранящий списки всех постов по ключу ID канала
        """
        channels = self.get_channels()[::-1]
        channels += [['featured', 'featured']]
        for channel_num, channel_info in enumerate(channels):
            skip = True
            posts = []
            for name in channels_links:
                if name in channel_info[1]:
                    skip = False  # если отсутвует информация от текущем канале пропустить его сканирование
                    break
            if not skip:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1"
                if channel_info[0] == 'featured':
                    url = f"https://api.ifunny.mobi/v4/feeds/featured?limit=1"
                # Первый запрос в апи для получения ID слудующей страницы
                posts.append(requests.get(url, headers=self.headers).json())
                x = threading.Thread(target=self.threading_all_posts, args=(posts, channel_info))
                x.start()
                time.sleep(5)
        while not isDictFull(self.result, len(channels_links)):
            time.sleep(1)
        return self.result

    def threading_new_posts(self, posts: list, channel_id: str):
        """Берет посты по которым нужно пройтись и найти последний для канала с идентификатором channel_id"""
        last_date, last_post = None, None
        for i in posts:
            content = i['data']['content']
            next_page = content['paging']['cursors']['next']
            while content['paging']['hasNext'] is not False:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_id}/items?limit=1000&next={next_page}"
                if channel_id == 'featured':
                    url = f"https://api.ifunny.mobi/v4/feeds/featured?limit=1000&next={next_page}"
                posts = requests.get(url, headers=self.headers).json()
                content = posts['data']['content']
                items = content['items']
                next_page = content['paging']['cursors']['next']
                for item in items:
                    p = Post(item, channel_id)
                    if last_date:
                        if last_date < p.publish_at:
                            last_date = p.publish_at
                            last_post = p
                    else:
                        last_date = p.publish_at
                        last_post = p
            self.new_posts[channel_id] = last_post

    def is_new_memes(self):
        """
                Проход по всем существующим постам в АПИ по всем имеющимся катерогиям
                для сббора всех постов
                :return: dict() : dict[channel_id] = list(Post(), Post(), ...)
                    словарь хранящий списки всех постов по ключу ID канала
                """
        channels = self.get_channels()[::-1]
        channels += [['featured', 'featured']]
        for channel_num, channel_info in enumerate(channels):
            skip = True
            posts = []
            for name in channels_links:
                if name in channel_info[1]:
                    skip = False  # если отсутвует информация от текущем канале пропустить его сканирование
                    break
            if not skip:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1"
                if channel_info[0] == 'featured':
                    url = f"https://api.ifunny.mobi/v4/feeds/featured?limit=1"
                # Первый запрос в апи для получения ID слудующей страницы
                posts.append(requests.get(url, headers=self.headers).json())
                x = threading.Thread(target=self.threading_new_posts, args=(posts, channel_info[0]))
                x.start()
                time.sleep(5)
        while not isDictFull(self.new_posts, len(channels_links)):
            time.sleep(1)
        return self.new_posts
