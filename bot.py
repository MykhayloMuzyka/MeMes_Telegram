import telebot
import functions
import asyncio
import threading
from confgis.settings import *
from requests.exceptions import ReadTimeout
from datetime import datetime, timedelta
import time

bot = telebot.TeleBot(TOKEN_MANAGE)
loop = asyncio.get_event_loop()
commands_list = 'Вот список комманд:\n' \
                '/mailing :  Рассылка сообщения по всем чатам\n' \
                '/fill_channels :  начать заполнение каналов по 300 лучших постов\n' \
                '/autopost : начать монитроринг новых постов и их отправку по расписанию\n' \
                '/send_post : отправляет по одному новому посту в каждый возможный канал'


@bot.message_handler(commands=['start', 'help'])
def help(msg):
    if not functions.was_working:
        bot.send_message(msg.from_user.id, commands_list)
    else:
        bot.send_message(msg.from_user.id, commands_list + '\n/stop - остановить автопост')


@bot.message_handler(commands=['mailing'])
def mail(msg):
    if not functions.was_working:
        bot.send_message(msg.from_user.id, 'Введите сообщение')
        bot.register_next_step_handler(msg, sendMessage)
    else:
        bot.send_message(msg.from_user.id, 'Сначала выключите автопост (/stop)')


def sendMessage(msg):
    text = msg.text
    loop.run_until_complete(functions.mail(text))
    bot.send_message(msg.from_user.id, commands_list)


@bot.message_handler(commands=['send_post'])
def sendpost(msg):
    if not functions.was_working:
        loop.run_until_complete(functions.sendOnePostToEachChannel())
        bot.send_message(msg.from_user.id, commands_list)
    else:
        bot.send_message(msg.from_user.id, 'Сначала выключите автопост (/stop)')


@bot.message_handler(commands=['fill_channels'])
def fill(msg):
    if not functions.was_working:
        functions.setAction('filling')
        loop.run_until_complete(functions.fill_channels())
        bot.send_message(msg.from_user.id, commands_list)
        functions.setAction('menu')
    else:
        bot.send_message(msg.from_user.id, 'Сначала выключите автопост (/stop)')


@bot.message_handler(commands=['autopost'])
def autopost(msg):
    if not functions.was_working:
        functions.setAction('autopost')
        functions.was_working = True
        bot.send_message(msg.from_user.id, 'Start threading...\n/stop - stop the threading')
        t = threading.Thread(target=loop.run_until_complete(functions.is_new_posts()))
        t.start()
        t.join()
        # bot.send_message(msg.from_user.id, commands_list)
        functions.setAction('menu')
    else:
        bot.send_message(msg.from_user.id, 'Автопост уже включен\n/stop - остановить')


@bot.message_handler(commands=['stop'])
def working(msg):
    if functions.was_working:
        functions.was_working = False
        bot.send_message(msg.from_user.id, commands_list)


@bot.message_handler(commands=['counts'])
def counts(msg):
    bot.send_message(msg.from_user.id, functions.counts())


def poll():
    try:
        print(f'{datetime.now() + timedelta(hours=2)}) Bot polling...')
        bot.polling(none_stop=True)
    except ReadTimeout:
        print('ReadTimeout caught! Sleeping for 30 secs...')
        time.sleep(30)


if __name__ == '__main__':
    action = functions.getAction()
    if action == 'filling':
        loop.run_until_complete(functions.fill_channels())
        functions.setAction('menu')
    elif action == 'autopost':
        functions.was_working = True
        t = threading.Thread(target=poll)
        t.start()
        loop.run_until_complete(functions.is_new_posts())
        t.join()
    while True:
        try:
            poll()
        except RuntimeWarning:
            continue
