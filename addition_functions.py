from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel
from MeMes_Telegram.confgis.settings import *
from typing import Union
import pytz
from datetime import datetime
from telethon import errors


async def isNew(post) -> bool:
    """
    Определяет дату последней публикации по id канала
    return: дата последней публикации канала если канал найден, False в ином случае
    """
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
                user = client.sign_in(password=pw)
    # собираем все диалоги пользователя
    dialogs = await client.get_dialogs()
    for d in dialogs:
        peer_id = d.message.peer_id
        if isinstance(peer_id, PeerChannel):
            # проверка, являеться ли диалог каналом
            cid = int(f"{-100}{peer_id.channel_id}")
            channel_id = post.channel
            if cid == channel_id:
                # проверка, совпадает ли id даного канала с параметром функции
                return d.message.date.astimezone(pytz.timezone('Europe/Kiev')).strftime(DT_FORMAT)
    return False
