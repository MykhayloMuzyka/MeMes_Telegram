from datetime import datetime

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

#logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s', filename='logging.log')  #

logging.basicConfig(level=logging.WARNING)
logging.warning('Script was Started')
Api = Api()
DataBase = DataBase()

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DataBase.createTables(TABLES)
channels = Api.getChannels()

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


async def send_post(channel_id, chat, post, send_time):
    """
    :param channel_id: ID from API for this category of posts
    :param chat: Telegram chat ID for this category of posts
    :param post: One Post() that you need to send to telegram channel
    :param send_time: time before sending to make Log
    :return: if success True else False
    """

    message = 0000
    success = True
    post_filetype = post.url.strip()[-3:]
    timeout = abs(2 - float(time.time() - send_time).__round__(2))

    # when trying to send a message faster than 2 seconds after the previous one, make a timeout
    if float(time.time() - send_time).__round__(2) < 2:
        time.sleep(timeout)
        logging.info(f'#{post.id}: Timeout before sending =  {timeout}')

    # check content type to choose Telegram method
    to_send_time = time.time()

    if post_filetype in ('jpg', 'png'):
        image = ImageReader(post)
        if image.watermark():
            message = await bot.send_photo(chat, image.Crop())

        else:
            logging.info(f'№{post.id} Don`t have watermark (no need to crop image) {post.url}')
            message = await bot.send_photo(chat, post.url, post.title)

    elif post_filetype in ('mp4',):
        message = await bot.send_video(chat, post.url, caption=post.title)

    elif post_filetype in ('gif',):
        message = await bot.send_animation(chat, post.url, caption=post.title)
    else:
        logging.warning(f'Unknown Post.type ({post.type}) at {post.url}')
        success = False

    # check how much time to choose method and send post
    send_time = time.time()
    logging.info(f'№{post.id} send in {float((send_time - to_send_time) * 1000).__round__(2)} ms')

    if success:  # if message was send with right method - add post in Database and update id and date
        DataBase.AddPost(message.message_id, post, key_by_value(channels_links, chat))
        DataBase.Last_id('set', channel_id, post.id)
        DataBase.lastUpdate('set', channel_id, datetime.now().strftime(DT_FORMAT))
        return True
    return False


async def fill_channels():
    best_memes = Api.BestPosts()

    for channel_id in best_memes:
        last_post_id = DataBase.Last_id('get', channel_id)

        # Search last post in Telegram channel and strip list from this post to the end to avoid repetition
        for post_num, post in enumerate(best_memes[channel_id]):
            if post.id == last_post_id:
                best_memes[channel_id] = best_memes[channel_id][post_num + 1:]
                break
        # Start filling channel by channel
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
        last_time = datetime.now().strftime(DT_FORMAT)
        DataBase.lastUpdate('set', channel_id, last_time)


was_started = False


async def CheckUpdates():
    global was_started
    timer = datetime.now().replace(hour=0, minute=3, second=0)
    at_start_update = datetime.strptime(datetime.now().strftime(DT_FORMAT), DT_FORMAT)

    morning = datetime.strptime(datetime.now().replace(hour=9, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)
    day = datetime.strptime(datetime.now().replace(hour=12, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)
    evening = datetime.strptime(datetime.now().replace(hour=18, minute=0, second=0).strftime(DT_FORMAT), DT_FORMAT)
    now_time = datetime.now()
    schedule = [at_start_update, morning, day, evening]
    for posting_time in schedule:
        print(posting_time)
        diff = (now_time - posting_time).__abs__().total_seconds()
        dif_hours = int(diff // 3600)
        dif_minutes = int((diff % 3600) // 60)
        dif_seconds = int(diff % 60)

        difference = datetime.now().replace(hour=dif_hours, minute=dif_minutes, second=dif_seconds)
        logging.info(f'Difference between {posting_time} and {now_time} = {difference}| {difference <= timer:}')
        if difference <= timer:

            if posting_time == at_start_update:
                if was_started is False:
                    was_started = True
                else:
                    break
            all_channels = DataBase.ReadChannels()
            for chName, chId in all_channels:

                lower_limit = DataBase.lastUpdate('get', chId)
                lower_limit = datetime.strptime(lower_limit, DT_FORMAT)

                logging.info(f'Search post since {lower_limit} for channel: {chName}')

                channel_table = key_by_value(channels_info, {'telegram': id_to_link[chId], 'api_id': chId})
                new_post = (Api.UpdatePost(chId, channel_table, lower_limit, 0),)
                if len(new_post) > 0 and new_post[0] is not None:

                    logging.info(f'Found a new post:  {new_post[0].id}, {new_post[0].publish_at}  {new_post[0].url}')
                    send_time = time.time()
                    for post_num in range(len(new_post)):
                        post = new_post[post_num]
                        try:
                            print(f"\n{chName}: {post.link} | {post.sm_per_hour} | {post.smiles} / {post.publish_at}\n")
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

                    new_time = datetime.now().strftime(DT_FORMAT)
                    DataBase.lastUpdate('set', chId, new_time)
                else:
                    logging.error(f'No content to send at {datetime.now()} {new_post}')


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
    dialogs = await client(get_dialogs)
    # create dictionary of ids to chats
    chats = {}

    for c in dialogs.chats:
        chats[c.id] = c

    for d in dialogs.dialogs:
        peer = d.peer
        if isinstance(peer, PeerChannel):

            peer_id = peer.channel_id
            channel = chats[peer_id]
            access_hash = channel.access_hash
            dialog_name = channel.title
            if dialog_name in channels_links.keys():
                to_clear.append([peer_id, access_hash])
        else:
            continue

    for chat_id, access_hash in to_clear:
        chat = PeerChannel(int(chat_id))
        start = await client.send_message(chat, 'Abra Candelabra')

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


def repeat(coro, arg_loop):
    logging.info(f'Check updating schedule at {datetime.now()}')
    asyncio.ensure_future(coro(), loop=arg_loop)
    arg_loop.call_later(DELAY, repeat, coro, arg_loop)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    while True:
        cmd = input('There is list of commands:\n'
                    '\t- /fill_channels :  to start sending 1000 best posts to every channel\n'
                    '\t- /clear_channels : to delete all messages from every channel\n'
                    '\t- /autopost : start waiting for new updates and post them to their channels\n'
                    '\t\t - /exit: to stop the script\n'
                    'Input your command :').strip().lower()
        if cmd == '/fill_channels':
            loop.run_until_complete(fill_channels())
        elif cmd == '/autopost':
            logging.info(f'Start Monitoring at {datetime.now()}')
            # loop.call_later(DELAY, repeat, CheckUpdates, loop)
            while True:
                print('GO SEARCH')
                loop.run_until_complete(CheckUpdates())
                time.sleep(150)
            # executor.start_polling(dp)
        elif cmd == '/clear_channels':
            loop.run_until_complete(ClearChannel())
        elif cmd == '/exit':
            sys.exit()

