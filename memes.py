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


class PostList(list):
    def index(self, value, **kwargs):
        for i, obj in enumerate(self):
            if obj.id == value:
                return i


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
        self.guessed = []
        channels = DataBase.ReadChannels(DataBase())
        self.smiles_filter = dict()
        self.feature_smiles = 200
        for channel in channels:
            self.smiles_filter[channel[1]] = 700
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

    def getFeatures(self):
        """
        Get Top 1000 posts from Features
        :return: list of Post()
        """
        best_featured = list()
        features_url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=1'
        features = requests.get(features_url, headers=self.headers)
        posts = features.json()
        if features.status_code == 200:
            content = posts['data']['content']
            items = content['items']
            next_page = content['paging']['cursors']['next']
            count = len(items)
            for item in items:
                if item['num']['smiles'] >= self.feature_smiles:
                    best_featured.append(Post(item, 'featured'))
            while content['paging']['hasNext'] is not False:
                posts = requests.get(
                    f"https://api.ifunny.mobi/v4/feeds/featured?limit=500&next={next_page}",
                    headers=self.headers).json()
                content = posts['data']['content']
                items = content['items']
                next_page = content['paging']['cursors']['next']
                for item in items:
                    if item['num']['smiles'] >= self.feature_smiles or len(items) < 900:
                        best_featured.append(Post(item, 'featured'))
                count += len(items)
            print('featured', '=', "Всего:", count, 'Отфильтрованные: ', len(best_featured),
                  f'При {self.feature_smiles} лайков.')
            if count >= 1000:
                if 1000 > len(best_featured) or len(best_featured) > 1100:
                    k = int(count / (len(best_featured) * 0.05 + 1))
                    if len(best_featured) > 1100:
                        self.feature_smiles += k
                    elif len(best_featured) < 1000:
                        self.feature_smiles -= k
                    self.getFeatures()
            best_featured.reverse()
            return best_featured[:1000]
        return list()

    def BestPosts(self):
        """
        Filter every channel in API to get Top 1000 best posts by smiles
        :return: list of Post()
        """
        begin_time = time.time()
        channels = self.getChannels()
        best_memes = dict()

        for channel_num, channel_info in enumerate(channels):
            skip = True
            print(channel_num)
            start_time = time.time()
            filtered = list()
            for name in channels_links:
                if name in channel_info[1]:
                    skip = False
                    break

            if channel_num not in self.guessed and not skip and channel_num == 5:
                posts = requests.get(f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1",
                                     headers=self.headers).json()
                content = posts['data']['content']

                next_page = content['paging']['cursors']['next']
                items = content['items']

                count = len(items)
                for item in items:
                    if item['num']['smiles'] >= self.smiles_filter[channel_info[0]]:
                        filtered.append(Post(item, channel_info[0]))
                while content['paging']['hasNext'] is not False:
                    posts = requests.get(
                        f"https://api.ifunny.mobi/v4/channels/{channel_info[0]}/items?limit=1000&next={next_page}",
                        headers=self.headers).json()
                    content = posts['data']['content']
                    items = content['items']
                    next_page = content['paging']['cursors']['next']
                    for item in items:
                        if item['num']['smiles'] >= self.smiles_filter[channel_info[0]] or len(items) < 900:
                            filtered.append(Post(item, channel_info[0]))
                    count += len(items)
                print(channel_info[0], '= ', "Всего:", count, 'Отфильтрованные: ', len(filtered),
                      f'При {self.smiles_filter[channel_info[0]]} лайков.')
                if count > 1000:
                    if 1000 > len(filtered) or len(filtered) > 1100:
                        k = int(count / (len(filtered) * 0.05 + 1))
                        if len(filtered) > 1100:
                            self.smiles_filter[channel_info[0]] += k
                        elif len(filtered) < 1000:
                            self.smiles_filter[channel_info[0]] -= k
                        self.BestPosts()
                    else:
                        self.guessed.append(channel_num)
                else:
                    self.guessed.append(channel_num)
                filtered.reverse()
                filtered = sorted(filtered, key=lambda meme: meme.publish_at)
                best_memes[channel_info[0]] = filtered[:1000]  # dict[channel] = list of top 1000 posts (Post objects)
                logging.info(f'Category {channel_info[1]} filtered in {float(time.time() - start_time).__round__(2)} s')
        logging.info(f'BestPosts filtered in {float(time.time() - begin_time).__round__(2)} seconds')
        return best_memes

    def UpdatePost(self, channel_id, channel_name, lower_limit, upper_limit, tries):
        """
        Сhecks current channel for new posts since the last one written to the database.
        :param upper_limit:
        :param lower_limit:
        :param last_check_time: Value in Datetime type, that shows the last moment when channel was updated
        :param channel_id: ID from API for the category this post is from or 'featured'
        :return: if channel needs update return list() of Post(), else return empty list()
        """
        right_period = list()
        best_post = None
        check_upd_url = f"https://api.ifunny.mobi/v4/channels/{channel_id}/items?limit=1000"
        if channel_id == 'featured':
            check_upd_url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=1000'
        all_posts = requests.get(check_upd_url, headers=self.headers)
        print(channel_name)
        print(f'upper_limit = {upper_limit}\n'
              f'lower_limit = {lower_limit}')

        if all_posts.status_code == 200:
            content = all_posts.json()['data']['content']
            items = content['items']
            #  sort posts from new to older
            posts = list(Post(item, channel_id) for item in items)
            posts = sorted(posts, key=lambda p: p.publish_at, reverse=True)

            # check posts ony by one to match right time period
            for post in posts:
                if post.publish_at < lower_limit:
                    break

                # if lower_limit < post.publish_at < upper_limit:
                right_period.append(post)
                print(f' >> {post.publish_at}, {post.id}')

            # if no posts in this period
            if len(right_period) == 0:

                pre_lower_limit = DataBase.preLastUpdate(DataBase(), channel_id)
                pre_lower_limit = datetime.strptime(pre_lower_limit, DT_FORMAT)  # get previous update time

                if tries >= 2:  # if previous period have no posts too
                    self.lower_limit = self.lower_limit - timedelta(hours=5)  # iterating beck with 5 hours step
                    pre_lower_limit = self.lower_limit                        # until we get post in this time period

                result = self.UpdatePost(channel_id, channel_name, pre_lower_limit, upper_limit, tries + 1)
                return result
            else:  # if we have post in period and can take it
                top_smiles = sorted(right_period, key=lambda post: post.smiles, reverse=True)  # sorting by smiles
                print(f'\t\tSMILES SORT {len(top_smiles)}')
                for post in top_smiles:
                    print(f' s> {post.publish_at}, {post.id}, {post.smiles}')
                DataBase.lastUpdate(DataBase(), 'set', channel_id, upper_limit)
                logging.info(f'Finished searching for updates in category: {channel_id}')
                position = 0
                if DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                    while DataBase.DuplicatePost(DataBase(), channel_name, top_smiles[position].id) is True:
                        position += 1
                        print(f'position = {position}')
                        if position >= len(top_smiles):
                            self.lower_limit = self.lower_limit - timedelta(hours=5)  # iterating beck with 5 hours step
                            pre_lower_limit = self.lower_limit  # until we get post in this time period
                            result = self.UpdatePost(channel_id, channel_name, pre_lower_limit, upper_limit, tries + 1)
                            return result
                        try:
                            best_post = top_smiles[position]
                            DataBase.lastUpdate(DataBase(), 'set', channel_id, upper_limit)
                        except:
                            best_post = None

                    return best_post  # get one of the most smiled post

                DataBase.lastUpdate(DataBase(), 'set', channel_id, upper_limit)
                return top_smiles[position]





    def test_max_quality(self):
        headers = self.headers
        url = f'https://api.ifunny.mobi/v4/channels/5ed63a7d16ba9c5ce307d080/items?limit=30'
        my_request = requests.get(url, headers=headers)
        if my_request.status_code == 200:
            posts = my_request.json()
            items = posts['data']['content']['items']
            for item in items:
                #print(json.dumps(item, indent=4))
                img = urllib.request.urlopen(item['url']).read()
                out = open(f"img_test/original_url.jpg", "wb")
                out.write(img)
                out.close()
                get_qual = Image.open(f"img_test/original_url.jpg")
                print("Отсылаемое изображение: ", get_qual.size)
                o_x, o_y = get_qual.size
                get_qual.close()
                for url in item['thumb']:
                    try:
                        img = urllib.request.urlopen(item['thumb'][url]).read()
                        out = open(f"img_test/{url}.jpg", "wb")
                        out.write(img)
                        out.close()
                        get_qual = Image.open(f"img_test/{url}.jpg")
                        x, y = get_qual.size
                        if o_x < x or o_y < y:
                            print(f'Качество лучше {x}, {y}', item['thumb'][url] )

                        get_qual.close()
                    except:
                        pass


#
# api = Api()
# lower_limit = DataBase.lastUpdate(DataBase(), 'get', '5ee0ccdb73131700157c6ba2')
# lower_limit = datetime.strptime(lower_limit, DT_FORMAT)
# upper_limit = datetime.now().strftime(DT_FORMAT)
# upper_limit = datetime.strptime(upper_limit, DT_FORMAT)
# prelower_limit = DataBase.preLastUpdate(DataBase(),'5ee0ccdb73131700157c6ba2')
# api.lower_limit = datetime.strptime(prelower_limit, DT_FORMAT)
# print(api.lower_limit)
# a = api.UpdatePost('5ee0ccdb73131700157c6ba2', 'мемы', lower_limit, upper_limit, 0)
# print(a.smiles, a.publish_at, a.link)