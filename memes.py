import json
from datetime import datetime
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


class Post:
    def __init__(self, item, channel):
        self.id = item['id']
        self.type = item['type']
        self.title: str = item['title']
        self.url: str = item['url']
        self.channel = channel
        self.publish_at = datetime.fromtimestamp(item['publish_at'])
        self.link = item['link']
        # self.watermark = item[]


class ImageReader:
    def __init__(self, post):
        img = urllib.request.urlopen(post.url).read()
        out = open("img/img.jpg", "wb")
        out.write(img)
        out.close()
        self.path = 'img/img.jpg'
        self.pic = Image.open(self.path)

    def watermark(self):
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

    def getChannels(self):
        result = list()

        channels = requests.get(self.channels_url, headers=self.headers)
        if channels.status_code == 200:
            for item in channels.json()['data']['channels']['items']:
                result.append([item['id'], item['name']])
            return result
        return False

    def getPosts(self, channel_id: str, limit: int = 1):
        channel_posts_url = self.channels_url + f"/{channel_id}/items?limit={limit}"
        posts = requests.get(channel_posts_url, headers=self.headers)
        if posts.status_code == 200:
            return 1
        return list()

    def getFeatures(self):
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
        begin_time = time.time()
        channels = self.getChannels()
        best_memes = dict()
        for channel_num, channel_info in enumerate(channels):
            start_time = time.time()
            filtered = list()

            if channel_num not in self.guessed and channel_num == 7:
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
                best_memes[channel_info[0]] = filtered[:1000]  # dict[channel] = list of top 1000 posts (Post objects)
                logging.info(f'Category {channel_info[1]} filtered in {float(time.time() - start_time).__round__(2)} s')
        logging.info(f'BestPosts filtered in {float(time.time() - begin_time).__round__(2)} seconds')
        return best_memes

    def UpdatePost(self, channel, last_id):

        all_updates = list()
        searching: bool = False
        check_upd_url = f"https://api.ifunny.mobi/v4/channels/{channel}/items?limit=1"
        if channel == 'featured':
            check_upd_url = f'https://api.ifunny.mobi/v4/feeds/featured?limit=1'
        last_posts = requests.get(check_upd_url, headers=self.headers)
        if last_posts.status_code == 200:
            content = last_posts.json()['data']['content']
            next_page = content['paging']['cursors']['next']
            items = content['items']

            if items[0]['id'] == last_id:
                print('no need to update')
                return
            else:
                all_updates.append(Post(items[0], channel))
                while searching is False:
                    r_link = f"https://api.ifunny.mobi/v4/channels/{channel}/items?limit=100&next={next_page}"
                    if channel == 'featured':
                        r_link = f'https://api.ifunny.mobi/v4/feeds/featured?limit=100&next={next_page}'
                    last_posts = requests.get(r_link, headers=self.headers).json()
                    content = last_posts['data']['content']
                    items = content['items']
                    next_page = content['paging']['cursors']['next']
                    for item in items:
                        if item['id'] != last_id:
                            all_updates.append(Post(item, channel))
                        else:
                            searching = True
                            all_updates.reverse()
                            return all_updates

    def test_time_header(self):
        headers = self.headers
        headers['If-Modified-Since'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')  # EXAMPLE FORMAT, 08 Dec 2020 19:54:20 GMT
        print(headers['If-Modified-Since'])
        url = f'https://api.ifunny.mobi/v4/channels/5ed63a9f0c26185b832ccc3c/items'
        my_request = requests.get(url, headers=headers)
        if my_request.status_code == 200:
            posts = my_request.json()
            items = posts['data']['content']['items']
            for item in items:
                publ = datetime.fromtimestamp(item['publish_at'])
                print(publ > datetime.now())
            return
        print(my_request.status_code)
