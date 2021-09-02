import logging
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Union
from MeMes_Telegram.db.localbase import DataBase
import cv2
import numpy as np
import pytz
import requests
from PIL import Image
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel

from MeMes_Telegram.confgis.settings import *


def channel_name(full_name):
    name_list = full_name.split(' ')
    if name_list[0][0] == '#':
        return name_list[0][1:]
    else:
        return name_list[0]


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
        # with open("img/img.jpg", "wb") as out:
        #     out.write(img)
        out = open("img/img.jpg", "wb")
        out.write(img)
        out.close()
        self.path = 'img/img.jpg'
        self.pic = Image.open(self.path)

    def watermark(self):
        """
        Проверка поста на наличие вотермарки в нижней части изображения
        :return: True если вотермарка была найдена иначе  False
        """
        start_time = time.time()
        img_main = Image.open(self.path)
        img_template = Image.open('img/temp.jpg')  # шаблон вотермарки статически хранящийся в проекте
        t_width, t_height = img_template.size
        width, height = img_main.size
        box = (width - t_width - 50, height - t_height - 50, width, height)
        img_main.crop(box).save('img/corner.jpg')  # обрезка исходного изображения для увеличения скорости поиска
        img_main = cv2.imread('img/corner.jpg')
        img_gray = cv2.cvtColor(img_main, cv2.COLOR_BGR2GRAY)

        img_template = cv2.imread('img/temp.jpg')
        img_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)
        w, h = img_template.shape[::-1]
        res = cv2.matchTemplate(img_gray, img_template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.8)
        points = zip(*loc[::-1])
        counter = 0
        for pt in points:
            counter += 1
            cv2.rectangle(img_main, pt, (pt[0] + w, pt[1] + h), (255, 0, 0), 4)  # при первом совпадении выход из поиска
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
        crop_img.save('img/cropped.jpg', quality=90)
        logging.info(f'\t\tCROP time = {float(time.time() - start_time).__round__(2) * 1000} ms')
        return open('img/cropped.jpg', 'rb')


class Api:
    result = dict()

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

    def get_channels(self) -> Union[list, bool]:
        """
        :return: Список категорий в АПИ в виде ([id_1, name_1], [id_2, name_2], ...) или False в случае неудачи
        """
        result = list()

        channels = requests.get(self.channels_url, headers=self.headers)
        # print(1)
        # print(channels.json())
        if channels.status_code == 200:
            for item in channels.json()['data']['channels']['items']:
                result.append([item['id'], item['name']])
            return result
        return False

    def threading_best_posts(self, posts: list, channel_info: str):
        """Берет посты посты по которым нужно пройтись и собрать информацию, channel_info текущего канала"""
        all_posts = []
        for i in posts:
            content = i['data']['content']
            next_page = content['paging']['cursors']['next']
            items = content['items']
            all_posts.append(Post(items[0], channel_info[0]))

            requests_time = 0
            while content['paging']['hasNext'] is not False:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1000&next={next_page}"
                if channel_info[1] == 'featured':
                    url = f"https://api.ifunny.mobi/v4/feeds/featured?limit=1000&next={next_page}"

                start_request = time.time()
                posts = requests.get(url, headers=self.headers).json()
                requests_time += time.time() - start_request

                content = posts['data']['content']
                items = content['items']
                next_page = content['paging']['cursors']['next']

                filtered = list(Post(item, channel_info[0]) for item in items)
                all_posts += filtered

            # all_filtered_posts = []
            # for post in all_posts:
            #     if lastChannelPublicationTime(channels_info[channel_name(channel_info[1])]['telegram']) < post.publish_at:
            #         all_filtered_posts.append(post)
            # Сортировка постов по лайкам от больших к меньшему
            if len(all_posts) >= 300:
                best_posts = sorted(all_posts, key=lambda post: post.smiles)[:300]
            else:
                best_posts = sorted(all_posts, key=lambda post: post.smiles)[:len(all_posts)]

            # Сортировка отставшейся тысячи по дате публикации от старых к новым
            from_old_to_new = sorted(best_posts, key=lambda post: post.publish_at)
            self.result[channel_info[0]] = from_old_to_new

    def best_posts(self) -> dict:
        """
        Проход по всем существующим постам в АПИ по всем имеющимся катерогиям
        для отбора 1000 лучших по лайкам постов в каждом канале
        :return: dict() : dict[channel_id] = list(Post(), Post(), ...)
            словарь хранящий списки лучшей 1000 по ключу ID канала
        """
        channels = self.get_channels()
        channels.append(['featured', 'featured'])
        for channel_num, channel_info in enumerate(channels):

            skip = True
            posts = []

            for name in channels_links:
                if name in channel_info[1]:
                    skip = False  # если отсутвует информация от текущем канале пропустить его сканирование
                    # print(skip)
                    break

            if not skip:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1"
                if channel_info[1] == 'featured':
                    url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=1'

                # Первый запрос в апи для получения ID слудующей страницы
                posts.append(requests.get(url, headers=self.headers).json())
                x = threading.Thread(target=self.threading_best_posts, args=(posts, channel_info))
                x.start()

        time.sleep(50)
        return self.result

    def update_post(self, channel_id, channel_name, lower_limit, tries):
        """
        Определение наличия новых постов заданном канала с момента последней отправки
        :param tries: установить этот параметр в ноль при вызове метода,
            он для отработки рекурсии
        :param channel_name: Имя канала из БД который нужно обновить
        :param lower_limit: ранняя граница времени от которой производить поиск нового поста
            (обычно это время последней отправки в канал)
        :param channel_id: ID категории из АПИ для этого поста или 'featured'

        :return: Лучший найдненный пост если таковой имеется иначе возврат None
        """
        logging.info(f'{channel_name}: Searching for new post since {lower_limit}')
        dt_now = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
        dt_now = dt_now.replace(tzinfo=None)
        best_post = None

        # Если метод произвел поиск больше 20 раз безрезультатно то нужно прекратить поиск по этому каналу
        if tries > 20:
            return None
        check_upd_url = f"https://api.ifunny.mobi/v4/channels/{channel_id}/items?limit=500"
        if channel_id == 'featured':
            check_upd_url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=500'
        all_posts = requests.get(check_upd_url, headers=self.headers)

        if all_posts.status_code == 200:
            content = all_posts.json()['data']['content']
            items = content['items']

            #  Сортировка постов от новых к старым до дате публикации
            posts = list(Post(item, channel_id) for item in items)
            posts = sorted(posts, key=lambda p: p.publish_at, reverse=True)
            oldest_post = len(posts) - 1

            # Находим индекс старейшего поста входщим в указанный период времени
            for post in posts:
                if post.publish_at < lower_limit:
                    oldest_post = posts.index(post)
                    break

            #  Отсавляем на проверку только входящие в рамки времени посты
            right_period = posts[0:oldest_post]

            if len(right_period) == 0:  # Если в заданный период времени найдено 0 постов

                # Переопределяем нижнюю границу поиска до предпоследней отправки в канал
                pre_lower_limit = DataBase.pre_last_update(DataBase(), channel_id)
                try:
                    pre_lower_limit = datetime.strptime(pre_lower_limit, DT_FORMAT)  # get previous update time
                except Exception as e:
                    logging.info('An error was detected in the search lower bound', e)
                    pre_lower_limit = datetime.strptime(dt_now.replace(hour=9, minute=0, second=0).strftime(DT_FORMAT),
                                                        DT_FORMAT)

                if tries == 0:
                    self.lower_limit = pre_lower_limit
                # если на промежутке с предпоследней отпрвки также нет результатов постепенное понижение границы
                if 1 <= tries < 10:
                    self.lower_limit = self.lower_limit - timedelta(hours=5)  # откат границы на 5 часов
                    pre_lower_limit = self.lower_limit

                # Если за 10 попыток не был обнаружен подходящий пост, проевярем их наличие за послдние 10 дней
                # относительно последней заданной попытками метода границы
                elif tries >= 10:
                    self.lower_limit = self.lower_limit - timedelta(days=1)  # iterating beck with 1 day step
                    pre_lower_limit = self.lower_limit  # until we get post in this time period that wasn't send

                result = self.update_post(channel_id, channel_name, pre_lower_limit, tries + 1)
                return result
            else:  # Если в нужном временном промежутке есть посты

                # Вычисление параметра скорости набора лайков
                for meme in right_period:
                    try:
                        meme.sm_per_hour = meme.smiles / meme.life_time()
                    except ZeroDivisionError:
                        meme.sm_per_hour = meme.smiles / 0.01

                # Сортировка от луших к худшим
                top_smiles = sorted(right_period, key=lambda s_post: s_post.sm_per_hour, reverse=True)

                position = 0

                # Если пост является повторяющимся с иным из уже отрпавленных то продолжаем выбор по top_smiles
                if DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                    while DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                        position += 1
                        if position >= len(top_smiles):
                            logging.warning(f"update_post:get not enough posts that "
                                            f"wasn't send before in this period")
                            self.lower_limit = self.lower_limit - timedelta(hours=5)
                            pre_lower_limit = self.lower_limit  #
                            result = self.update_post(channel_id, channel_name, pre_lower_limit, tries + 1)

                            logging.info(f'Finished searching for updates in category: {channel_id}')
                            return result
                        try:
                            best_post = top_smiles[position]
                        except Exception as e:
                            logging.info('The error was detected in an attempt to update the post.', e)
                            best_post = None

                    logging.info(f'Finished searching for updates in category: {channel_id}')

                    return best_post  # get one of the most smiled post

                # Если проверка на дубликат прошла успешно вернуть найденный пост
                return top_smiles[position]
