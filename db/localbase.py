import time

from settings import channels_links, DT_FORMAT
from aiogram.types import base
from typing import Optional
import sqlite3
import logging
from datetime import datetime

from exception.exception import FlagError

import pytz

TABLES = dict()

TABLES['channels'] = '''
                     CREATE TABLE "channels" (
                        "id"	INTEGER NOT NULL,
                        "name"	varchar(30) NOT NULL,
                        "channel_id" varchar(15) UNIQUE,
                        "channel_telegram" varchar(20) UNIQUE,
                        "last_1000_id"  varchar(20) UNIQUE,
                        "last_update_time" varchar(20),
                        "prelast_update_time" varchar(20),
                        PRIMARY KEY("id" AUTOINCREMENT)
                        
                        );
                     '''
for name in channels_links:
    TABLES[name] = f'''
                        CREATE TABLE "{name}" (
                        "id"	INTEGER NOT NULL,
                        "message_id" varchar(20) UNIQUE,
                        "post_id"	varchar(30) NOT NULL,
                        "post_url" varchar(15) UNIQUE,
                        "post_type" varchar(20),
                        PRIMARY KEY("id" AUTOINCREMENT)
                        );
                    '''

    TABLES['featured'] = f'''
                        CREATE TABLE "featured" (
                        "id"	INTEGER NOT NULL,
                        "message_id" varchar(20) UNIQUE,
                        "post_id"	varchar(30) NOT NULL,
                        "post_url" varchar(15) UNIQUE,
                        "post_type" varchar(20) ,
                        PRIMARY KEY("id" AUTOINCREMENT)
                        );
                    '''


class DataBase:
    def __init__(self):
        try:
            self.name = 'memes'
            self.db = sqlite3.connect('{0}.db'.format(self.name))

        except sqlite3.Error as err:
            logging.error(f'Init Database: {err}')

        except Exception as err:
            logging.critical(f'Init Database: {err}')

    def create_tables(self, tables: dict):
        """
        Метод создания таблиц в БД
        :param tables: Словарь значения котрого SQL запросы по созданию таблиц
        :return: True если таблицы созданы успешно иначе False
        """
        result = True
        for table in tables:
            try:
                self.cursor = self.db.cursor()

                self.cursor.execute(tables[table])

                logging.info(f'Table {table} successfully created')
            except sqlite3.Error as err:
                if 'already exists' in err.args[0]:
                    logging.info(f'Table {table} already exists')
                else:
                    logging.warning(f'createTables {err} on {table} ')
                    result = False
            finally:
                self.cursor.close()

        self.db.commit()

        return result

    def WriteChannels(self, ch_id, ch_name, channel_telegram):
        """
        Запись указанного канала в БД
        :param ch_id: Api ID канала
        :param ch_name: Имя канала
        :param channel_telegram: Telegram ID канала
        :return: True если канал успешно записан успешно иначе False
        """
        cmd = "insert into channels (channel_id, name, channel_telegram) values (?, ?, ?)"
        exc_cmd = f"update channels set channel_id = '{ch_id}', name = '{ch_name}', " \
                  f"channel_telegram = '{channel_telegram}' where channel_telegram = '{channel_telegram}'"
        result = True

        self.cursor = self.db.cursor()
        try:
            self.cursor.execute(cmd, (ch_id, ch_name, channel_telegram,))
            self.db.commit()
        except sqlite3.Error as err:
            if 'UNIQUE constraint failed' in err.args[0]:
                if 'channel_id' in err.args[0]:
                    logging.warning(f'WriteChannels :{ch_name}({ch_id}) already exists')
                elif 'channel_telegram' in err.args[0]:
                    self.cursor.execute(exc_cmd)
                    self.db.commit()
                else:
                    logging.error(f'WriteChannels : {err}')
            else:
                result = False
                logging.error(f'WriteChannels : {err}')

        self.cursor.close()
        return result

    def ReadChannels(self):
        """
        Получить список данных о каналах их БД
        :return: list() в формате ([name_1, channel_id_1],[name_2, channel_id_2], ...) если все в порядке,
            иначе пустой список
        """
        result = list()
        cmd = "select name, channel_id from channels"
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(cmd)
            records = self.cursor.fetchall()
            for row in records:
                result.append([row[0], row[1]])

        except sqlite3.Error as err:
            result = list()
            logging.error(f'ReadChannels: {err}')

        except Exception as err:
            result = list()
            logging.error(f'ReadChannels: {err}')

        finally:
            self.cursor.close()
            return result

    def last_id(self, flag, channel_id: str, last_id: Optional[base.String] = None):
        """
        :param channel_id: Api ID канала
        :param last_id: ID последнего отправленного поста для обновления в БД
        :param flag: set = записать и обновить последний отправленный ID в БД
                   :get = считать последний записанный ID из БД
        :return: set: True если запись прошла успешно иначе  False
                 get: значение последнего ID из БД
        """
        cmd_set = f"update channels set `last_1000_id` = '{last_id}' where `channel_id` = '{channel_id}'"
        cmd_get = f"select `last_1000_id` from channels where `channel_id` = '{channel_id}'"
        if flag == 'set':
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(cmd_set)
                self.db.commit()
                self.cursor.close()
                return True
            except sqlite3.Error as err:
                logging.error(err)
                self.cursor.close()
                return False
        elif flag == 'get':
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(cmd_get)
                record = self.cursor.fetchone()

                self.cursor.close()
                return record[0]
            except sqlite3.Error as err:
                logging.error(f' Last_1000_id: {err}')
                self.cursor.close()
                return 0
        else:
            raise FlagError

    def last_update(self, flag, channel_id: str, last_time: Optional[str] = None):
        """

        :param last_time:
        :param channel_id: ID канала
        :param flag: set =записать и обновить последний отосланный пост в БД
                   :get = считать последний записанный ID из БД
        :return: set: True если запись прошла успешно иначе  False
                 get: значение последнего ID из БД
        """

        cmd_get = f"select `last_update_time` from channels where `channel_id` = '{channel_id}'"
        cmd_set = f"update channels set `last_update_time` = '{last_time}' where `channel_id` = '{channel_id}'"
        cmd_set_2 = f"update `channels` set `prelast_update_time` = (?) where `channel_id` = '{channel_id}'"

        exception_return = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
        exception_return = exception_return.replace(day=exception_return.day + 2).strftime(DT_FORMAT)
        if flag == 'set':
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(cmd_get)
                record = self.cursor.fetchone()[0]
                self.cursor.execute(cmd_set_2, (record,))
                self.db.commit()
                time.sleep(1)
                self.cursor.execute(cmd_set)
                self.db.commit()
                self.cursor.close()
                return True
            except sqlite3.Error as err:
                logging.error(f'lastUpdate set {err}')
                self.cursor.close()
                return False
        elif flag == 'get':
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(cmd_get)
                record = self.cursor.fetchone()
                self.cursor.close()
                result = record[0]
                return result
            except sqlite3.Error as err:
                logging.error(f' lastUpdate get: {err}')
                self.cursor.close()
                return exception_return
            except TypeError as err:
                logging.error(f' lastUpdate get: maybe function get None from Database {err}')
                self.cursor.close()
                return exception_return
        else:
            raise FlagError

    def pre_last_update(self, channel_id):
        """
        :param channel_id: ID канала из АПИ
        :return: время предполседней отправки в виде строки
        """
        cmd = f"select prelast_update_time from `channels` where channel_id = '{channel_id}'"
        exception_return = datetime.now().astimezone(pytz.timezone('Europe/Kiev'))
        exception_return = exception_return.replace(day=exception_return.day + 2).strftime(DT_FORMAT)
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(cmd)
            record = self.cursor.fetchone()
            self.cursor.close()
            result = record[0]
            return result

        except sqlite3.Error as err:
            logging.error(f' prelastUpdate: {err}')
            return exception_return

        except TypeError as err:
            logging.error(f'prelast Update: maybe function get None from Database {err}')
            return exception_return

    def add_post(self, message_id, post, channel_name: str):
        """
        :param message_id: ID собщения которое содердит в себе пост
        :param post: экемпляр класса Post() котороый нужно отправить
        :param channel_name: имя канала в БД
        :return: True если запись прошла успешно иначе False
        """

        cmd = f'insert into `{channel_name}` (message_id, post_id, post_url, post_type) values (?, ?, ?, ?)'
        try:
            self.cursor = self.db.cursor()
            params = (message_id, post.id, post.url, post.type)
            self.cursor.execute(cmd, params)
            self.db.commit()
            self.cursor.close()
            return True
        except sqlite3.Error as err:
            self.cursor.close()
            logging.error(err)

        except Exception as err:
            logging.error(f' AddPost: {err}')
            return False

    def DuplicatePost(self, channel_name, post_id):
        """
        Проверка поста на наличие его дубликатов в базе данных
        :param channel_name: имя канала в БД
        :param post_id: ID поста который требуется проверить
        :return: True если у поста есть дубликат, False если нет
        """
        cmd = f"select * from `{channel_name}` where post_id = '{post_id}'"
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(cmd)
            record = self.cursor.fetchone()
            self.cursor.close()
            if record is not None:
                return True
            return False
        except sqlite3.Error as err:
            self.cursor.close()
            logging.error(f'DuplicatePost: {err}')
