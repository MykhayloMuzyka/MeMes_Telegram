from aiogram import executor, Dispatcher, Bot
from localbase import DataBase, TABLES
from memes import Api, ImageReader
from settings import *
import logging
import aiogram
import asyncio
import time

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DataBase = DataBase()
Api = Api()

DataBase.createTables(TABLES)

links_dict = dict()
channels = Api.getChannels()
for ch_id, ch_name in Api.getChannels():
    for name in channels_links:
        if name in ch_name:
            links_dict[ch_id] = channels_links[name]
            DataBase.WriteChannels(ch_id, ch_name, channels_links[name])
DataBase.WriteChannels('featured', 'featured', favorite_id)


smiles = [1200, 2973, 1802, 3180, 3380, 1350, 0, 0, 0]
count = 0
for i in Api.smiles_filter.keys():
    Api.smiles_filter[i] = smiles[count]
    count += 1




async def fill_channels():
    best_memes = Api.BestPosts()
    length = list()
    for channel_id in best_memes:
        length.append(len(best_memes[channel_id]))

    for post_num in range(max(length)):
        print('\ncurrent post = ', post_num)
        post_time = time.time()
        for channel_id in best_memes.keys():
            start_time = time.time()
            if channel_id in links_dict.keys() and post_num in range(0, len(best_memes[channel_id])):
                post = best_memes[channel_id][post_num]
                post_filetype = post.url.strip()[-3:]
                try:
                    if post_filetype in ('jpg', 'png'):
                        image = ImageReader(post)
                        if image.watermark():
                            timeout = abs(2.5-float(time.time() - start_time).__round__(2))
                            logging.warning('\t\ttimeout', timeout)
                            if timeout < 2.5:
                                time.sleep(timeout)
                            logging.info(f'\t\tSEND time = {float(time.time() - start_time).__round__(2) * 1000} ms')
                            await bot.send_photo(links_dict[channel_id], image.Crop())
                            logging.info(f'\t\tSENDED time = {float(time.time() - start_time).__round__(2) * 1000} ms')

                        else:
                            logging.info('\t\t\t\t\t\t\tWITHOUT WATERMARK')
                            await bot.send_photo(links_dict[channel_id], post.url, post.title)

                    elif post_filetype in ('mp4',):
                        await bot.send_video(links_dict[channel_id], post.url, caption=post.title)
                    elif post_filetype in ('gif',):
                        await bot.send_animation(links_dict[channel_id], post.url, caption=post.title)
                    else:
                        print(post.type, post.url)
                    DataBase.Last_1000_id('set', channel_id, post.id)
                except aiogram.exceptions.RetryAfter as err:
                    logging.info('\t\t\t\t\t\tCATCH FLOOD CONTROL', err.args, err.timeout)
                    time.sleep(err.timeout)
                    post_num = post_num - 1
                except:
                    PrintException()

                print(f'post time = {float(time.time() - post_time).__round__(2) * 1000} ms\n')

            else:
                continue


async def fill_favorite():
    best_favorites = Api.getFeatures()
    start_time = time.time()
    for post_num in range(len(best_favorites)):
        post = best_favorites[post_num]
        post_filetype = post.url.strip()[-3:]
        try:
            if post_filetype in ('jpg', 'png'):
                image = ImageReader(post)
                if image.watermark():
                    timeout = 2.5
                    print('\t\ttimeout', timeout)
                    time.sleep(timeout)
                    print(f'\t\tSEND time = {float(time.time() - start_time).__round__(2) * 1000} ms')
                    await bot.send_photo(favorite_id, image.Crop())
                    print(f'\t\tSENDED time = {float(time.time() - start_time).__round__(2) * 1000} ms')

                else:
                    print('\t\t\t\t\t\t\tWITHOUT WATERMARK', post.url)
                    await bot.send_photo(favorite_id, post.url, post.title)

            elif post_filetype in ('mp4',):
                await bot.send_video(favorite_id, post.url, caption=post.title)

            elif post_filetype in ('gif',):
                await bot.send_animation(favorite_id, post.url, caption=post.title)

            else:
                print(post.type, post.url)
        except aiogram.exceptions.RetryAfter as err:
            print('\t\t\t\t\t\tCATCHED', err.args)
            time.sleep(err.timeout)
            post_num -= 1

        except:
            PrintException()

async def CheckUpdates():
    all_channels = DataBase.ReadChannels()
    for ch_name, ch_id in all_channels:
        last_post = DataBase.lastUpdate('get', ch_id)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    print('thats all')
    # loop.run_until_complete(fill_favorite())
    # loop.run_until_complete(fill_channels())
    #executor.start_polling(dp)
