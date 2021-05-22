from aiogram import executor, Dispatcher, Bot
from localbase import DataBase, TABLES
from memes import Api, ImageReader
from telethon import functions, errors
from telethon.tl.types import PeerUser, PeerChat, PeerChannel, InputPeerUser, InputPeerChat, InputPeerChannel, InputPeerEmpty
from telethon.tl.types.messages import Messages
from telethon import types
from telethon.sync import TelegramClient
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

id_to_link = dict()
id_to_name = dict()

channels = Api.getChannels()
for ch_id, ch_name in Api.getChannels():
    id_to_name[ch_id] = ch_name
    for name in channels_links:
        if name in ch_name:
            id_to_link[ch_id] = channels_links[name]
            DataBase.WriteChannels(ch_id, ch_name, channels_links[name])
DataBase.WriteChannels('featured', 'featured', favorite_id)


smiles = [1200, 2973, 1802, 3180, 3380, 1350, 0, 0, 0]
count = 0
for i in Api.smiles_filter.keys():
    Api.smiles_filter[i] = smiles[count]
    count += 1


async def send_post(channel_id, chat, post, send_time):
    post_filetype = post.url.strip()[-3:]
    timeout = abs(2.5 - float(time.time() - send_time).__round__(2))
    logging.info(f'\t\tTimeout {timeout}')
    success = True
    if timeout < 2.5:
        time.sleep(timeout)

    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            logging.info(f'\t\tSEND time = {float(time.time() - send_time).__round__(2) * 1000} ms')
            message = await bot.send_photo(chat, image.Crop())
            send_time = time.time()
            logging.info(f'\t\tSENDED time = {float(time.time() - send_time).__round__(2) * 1000} ms')

        else:
            logging.info('\t\t\t\t\t\t\tWITHOUT WATERMARK')
            message = await bot.send_photo(chat, post.url, post.title)

    elif post_filetype in ('mp4',):
        message = await bot.send_video(chat, post.url, caption=post.title)

    elif post_filetype in ('gif',):
        message = await bot.send_animation(chat, post.url, caption=post.title)

    else:
        print(post.type, post.url)
        message = 0000
        success = False
    if success:
        DataBase.AddPost(message.message_id, post, id_to_name[channel_id])


async def fill_channels():
    best_memes = Api.BestPosts()
    length = list()
    for channel_id in best_memes:
        length.append(len(best_memes[channel_id]))
    send_time = time.time()
    for post_num in range(max(length)):
        print('\ncurrent post = ', post_num)
        post_time = time.time()

        for channel_id in best_memes.keys():
            if channel_id in id_to_link.keys() and post_num in range(0, len(best_memes[channel_id])):

                post = best_memes[channel_id][post_num]
                post_filetype = post.url.strip()[-3:]
                try:
                    await send_post(channel_id,id_to_link[channel_id], post, send_time)
                    send_time = time.time()
                    DataBase.Last_1000_id('set', channel_id, post.id)

                except aiogram.exceptions.RetryAfter as err:
                    logging.info(f'\t\t\t\t\t\tCATCH FLOOD CONTROL {err.timeout}')
                    time.sleep(err.timeout)
                    post_num = post_num - 1
                except:
                    PrintException()

                print(f'post time = {float(time.time() - post_time).__round__(2) * 1000} ms\n')

            else:
                continue




async def fill_favorite():
    best_favorites = Api.getFeatures()
    send_time = time.time()

    for post_num in range(len(best_favorites)):
        post = best_favorites[post_num]
        post_filetype = post.url.strip()[-3:]
        try:
            await send_post('featured',favorite_id,post,send_time)
            send_time = time.time()
        except aiogram.exceptions.RetryAfter as err:
            logging.warning(f'\t\t\t\t\t\tCATCH FLOOD CONTROL {err.timeout}')
            time.sleep(err.timeout)
            post_num -= 1

        except:
            PrintException()

async def fill_test():
    best_posts = Api.BestPosts()
    length = list()
    for channel_id in best_posts:
        length.append(len(best_posts[channel_id]))
    send_time = time.time()
    for post_num in range(max(length)):
        post = best_posts['5ed63a9f0c26185b832ccc3c'][post_num]
        try:
            await send_post(test_id, post, send_time)
            DataBase.Last_1000_id('set', '5ed63a9f0c26185b832ccc3c', post.id)
        except aiogram.exceptions.RetryAfter as err:
            logging.info(f'\t\t\t\t\t\tCATCH FLOOD CONTROL {err.timeout}')
            time.sleep(err.timeout)
            post_num -= 1
        except:
            PrintException()
    DataBase.lastUpdate('set', '5ed63a9f0c26185b832ccc3c', best_posts['5ed63a9f0c26185b832ccc3c'][-1].id)

async def CheckUpdates(): # chat replace
    all_channels = DataBase.ReadChannels()
    for chName, chId in all_channels:
        last_post = DataBase.lastUpdate('get', chId)
        new_posts = Api.UpdatePost(chId, last_post)
        send_time = time.time()
        for post_num in range(len(new_posts)):
            post = new_posts[post_num]
            post_filetype = post.url.strip()[-3:]
            try:
                await send_post(test_id, post, send_time)
                send_time = time.time()
            except aiogram.exceptions.RetryAfter as err:
                time.sleep(err.timeout)

            except:
                PrintException()


async def ClearChannel():
    all_chats = list(channels_links.values())
    all_chats.append(favorite_id)
    to_clear = list()

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
                self_user = await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                pw = input('Two step verification is enabled. Please enter your password: ')
                self_user = await client.sign_in(password=pw)

    get_dialogs = functions.messages.GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=30,
        hash=0
    )
    dialogs = await client(get_dialogs)

    # create dictionary of ids to chats
    chats = {}

    for c in dialogs.chats:
        chats[c.id] = c

    for d in dialogs.dialogs:
        peer = d.peer
        if isinstance(peer, PeerChannel):

            id = peer.channel_id
            channel = chats[id]
            access_hash = channel.access_hash
            name = channel.title
            if name in channels_links.keys():
                to_clear.append([id, access_hash])
        else:
            continue

    for chat_id, access_hash in to_clear:
        chat = PeerChannel(int(chat_id))
        start = await client.send_message(chat, 'Abra Candelabra')

        to_delete = list(range(0, start.id+1))
        to_delete.reverse()
        messeges_count = len(to_delete)

        while True:
            try:
                chunk = to_delete[messeges_count - 100:messeges_count]
                if messeges_count < 100:
                    chunk = to_delete[0:messeges_count]

                await client.delete_messages(chat, chunk)
                if to_delete[0] in chunk or messeges_count < 0:
                    break
                messeges_count = messeges_count - 100
            except Exception:
                logging.error(Exception.args)
                break

        await client.delete_messages(types.PeerChannel(chat_id), start.id)
        await client.disconnect()


def repeat(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(DELAY, repeat, coro, loop)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        cmd = input('There is list of comands:\n'
                    '\t- /fill_channels :  to start sending 1000 best posts to every channel\n'
                    '\t- /clear_channels : to delete all messages from every channel\n'
                    '\t- /autopost : start waiting for new updates and post them to their channels\n'
                    '\t\t - /exit: to stop the script\n'
                    'Input your command :').strip().lower()
        if cmd == '/fill_channels':
            loop.run_until_complete(fill_favorite())
            loop.run_until_complete(fill_test())
        elif cmd == '/autopost':
            loop.call_later(DELAY, repeat, CheckUpdates, loop)
        elif cmd == '/clear_channels':
            loop.run_until_complete(ClearChannel())
        elif cmd == '/exit':
            sys.exit()



    print('polling')
    executor.start_polling(dp)

