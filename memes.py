import json
from datetime import datetime, timedelta
from settings import *
from PIL import Image
import urllib.request
import numpy as np
import pytesseract

from localbase import DataBase
import requests
import logging
import time
import cv2

import logging

logging.basicConfig(level=logging.INFO)


class Post:
    def __init__(self, item, channel):
        """
        :param item: dict() from json from API request in Request['data']['content']['items']
        :param channel: ID from API for the category this post is from
        """

        self.id = item['id']
        self.type = item['type']
        self.title: str = item['title']
        self.url: str = item['url']
        self.channel = channel
        self.publish_at = datetime.fromtimestamp(item['publish_at'])
        self.link = item['link']
        self.smiles = item['num']['smiles']


class ImageReader:
    def __init__(self, post: Post):
        """
        :param post: Post() that you need to check
        """
        img = urllib.request.urlopen(post.url).read()
        out = open("img/img.jpg", "wb")
        out.write(img)
        out.close()
        self.path = 'img/img.jpg'
        self.pic = Image.open(self.path)

    def watermark(self):
        """
        Сhecks the image for a site watermark
        :return: True is success else False
        """

        start_time = time.time()
        img_main = Image.open(self.path)
        img_template = Image.open('img/temp.jpg')
        t_width, t_height = img_template.size
        width, height = img_main.size
        box = (width - t_width - 50, height - t_height - 50, width, height)
        img_main.crop(box).save('img/corner.jpg')
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
            cv2.rectangle(img_main, pt, (pt[0] + w, pt[1] + h), (255, 0, 0), 4)
            break
        if counter == 1:
            logging.info(f'\t\tWATERMARK time = {float(time.time() - start_time).__round__(2) * 1000} ms')

            return True
        return False

    def Crop(self):
        """
        Crop 20 pixels from image bottom to delete watermark
        :return: Cropped image
        """
        start_time = time.time()
        width, height = self.pic.size
        box = (0, 0, width, height - 20)
        crop_img = self.pic.crop(box)
        crop_img.save('img/cropped.jpg', quality=90)
        logging.info(f'\t\tCROP time = {float(time.time() - start_time).__round__(2) * 1000} ms')
        return open('img/cropped.jpg', 'rb')


class Api:
    def __init__(self):
        self.headers = {
            'Accept': 'application/json,image/jpeg,image/webp,video/mp4',
            'iFunny-Project-Id': 'Russia',
            'Accept-Language': 'ru-RU',
            'Messaging-Project': 'idaprikol.ru:idaprikol-60aec',
            'ApplicationState': '1',
            'Authorization': 'Basic MDIzNTYxMzY2NDYxMzY2MzMzMkQ2NDMyMzU2MzJEMzQ2MzY0NjQyRDM4Mzg2MzM1MkQzMDMyMzQzNjYyMzkzOTMxNjEzNjY2MzZfUHpuNEQxMnNvSzo5Nzg0ZjE2MzZlYzdhYjE4YmI5YzczNmNhZjg0MzY1Mzc3M2M5Y2Mz',
            'Host': 'api.ifunny.mobi',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'iDaPrikol/6.15.4(1119163) Android/6.0 (Xiaomi; Redmi Note 4; Xiaomi)',
        }
        self.channels_url = 'https://api.ifunny.mobi/v4/channels'

        self.lower_limit = None

    def getChannels(self):
        """
        :return: List of API categories ([id_1, name_1], [id_2, name_2], ...) or boolean False if error
        """
        result = list()

        channels = requests.get(self.channels_url, headers=self.headers)
        if channels.status_code == 200:
            for item in channels.json()['data']['channels']['items']:
                result.append([item['id'], item['name']])
            return result
        return False

    def getPosts(self, channel_id: str, limit: int = 1):
        """

        :param channel_id: ID from API for this category of posts
        :param limit: amount of posts you need to get (int)
        :return: dict() from request json, or empty dict() if error
        """
        channel_posts_url = self.channels_url + f"/{channel_id}/items?limit={limit}"
        posts = requests.get(channel_posts_url, headers=self.headers)
        if posts.status_code == 200:
            items = posts.json()['data']['content']['items']
            all_posts = (Post(item, channel_id) for item in items)
            return all_posts
        return False

    def BestPosts(self):
        """
        Filter every channel in API to get Top 1000 best posts by smiles
        :return: dict() : dict[channel_id] = list(Post(), Post(), ...)
        """
        begin_time = time.time()
        channels = self.getChannels()
        channels.append(['featured', 'featured'])
        result = dict()
        for channel_num, channel_info in enumerate(channels):

            skip = True
            start_time = time.time()
            all_posts = list()

            for name in channels_links:
                if name in channel_info[1]:
                    skip = False
                    break

            if not skip and channel_num == 6:
                url = f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1"
                if channel_info[1] == 'featured':
                    url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=1'

                posts = requests.get(url, headers=self.headers).json()
                content = posts['data']['content']

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

                best_posts = sorted(all_posts, key=lambda post: post.smiles, reverse=True)
                best_posts = best_posts[:1000]
                from_old_to_new = sorted(best_posts, key=lambda post: post.publish_at, reverse=True)
                result[channel_info[0]] = from_old_to_new

                logging.info(f'Category {channel_info[1]} filtered in {float(time.time() - start_time).__round__(2)} s')
                logging.info(f'Category {channel_info[1]}  requests time = {float(requests_time).__round__(2)} s, '
                             f'code time = {(float(time.time() - start_time) - float(requests_time)).__round__(2)}')

        logging.info(f'BestPosts filtered in {float(time.time() - begin_time).__round__(2)} seconds')
        return result

    def UpdatePost(self, channel_id, channel_name, lower_limit, tries):
        """
        Сhecks current channel for new posts since the last one written to the database.
        :param tries: set this parameter to Zero, its for recursion searaching of result
        :param channel_name: channel name from DB that you want to update
        :param upper_limit: latest moment for  post publish date (real time usually)
        :param lower_limit: earliest moment for  post publish date (previous message sending usually)
        :param channel_id: ID from API for the category this post is from or 'featured'

        :return: if channel needs update return list() of Post() with best post from last period, else return empty list()
        """
        logging.info(f'{channel_name}: Searching for new post since {lower_limit}')

        right_period = list()
        best_post = None
        print(f'\t\t\tTRIES = {tries}')
        if tries > 20:
            return None
        check_upd_url = f"https://api.ifunny.mobi/v4/channels/{channel_id}/items?limit=500"
        if channel_id == 'featured':
            check_upd_url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=500'
        all_posts = requests.get(check_upd_url, headers=self.headers)

        if all_posts.status_code == 200:
            content = all_posts.json()['data']['content']
            items = content['items']
            #  sort posts from new to older
            posts = list(Post(item, channel_id) for item in items)
            posts = sorted(posts, key=lambda p: p.publish_at, reverse=True)
            oldest_post = len(posts) - 1
            # check posts ony by one to match right time period
            for post in posts:
                if post.publish_at < lower_limit:
                    oldest_post = posts.index(post)
                    break

            right_period = posts[0:oldest_post]
            # if no posts in this period
            if len(right_period) == 0:

                pre_lower_limit = DataBase.preLastUpdate(DataBase(), channel_id)
                pre_lower_limit = datetime.strptime(pre_lower_limit, DT_FORMAT)  # get previous update time
                if tries == 0:
                    self.lower_limit = pre_lower_limit
                if 1 <= tries < 10:  # if previous period have no posts too
                    self.lower_limit = self.lower_limit - timedelta(hours=5)  # iterating beck with 5 hours step
                    pre_lower_limit = self.lower_limit  # until we get post in this time period

                elif tries >= 10:  # if previous period have no posts too
                    self.lower_limit = self.lower_limit - timedelta(days=1)  # iterating beck with 1 day step
                    pre_lower_limit = self.lower_limit  # until we get post in this time period that wasn't sended

                result = self.UpdatePost(channel_id, channel_name, pre_lower_limit, tries + 1)
                return result
            else:  # if we have post in period and can take it
                top_smiles = sorted(right_period, key=lambda post: post.smiles, reverse=True)  # sorting by smiles
                position = 0
                for post in top_smiles:
                    d = DataBase.DuplicatePost(DataBase(), channel_name, post.id)
                    print(post.publish_at, post.url, d)
                if DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                    while DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                        position += 1
                        if position >= len(top_smiles):
                            logging.warning(f'UpdatePost: get not enough posts that wasn`t sended before in this period')
                            self.lower_limit = self.lower_limit - timedelta(hours=5)  # iterating back with 5 hours step
                            pre_lower_limit = self.lower_limit  # until we get post in this time period
                            result = self.UpdatePost(channel_id, channel_name, pre_lower_limit, tries + 1)

                            logging.info(f'Finished searching for updates in category: {channel_id}')
                            return result
                        try:
                            best_post = top_smiles[position]
                        except:
                            best_post = None

                    logging.info(f'Finished searching for updates in category: {channel_id}')

                    return best_post  # get one of the most smiled post

                return top_smiles[position]

