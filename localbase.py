from settings import PrintException
from settings import channels_links, DT_FORMAT
from aiogram.types import base
from typing import Optional
import sqlite3
import logging
from datetime import datetime, timedelta
TABLES = dict()

TABLES['channels'] = '''
                     CREATE TABLE "channels" (
                        "id"	INTEGER NOT NULL,
                        "name"	varchar(30) NOT NULL,
                        "channel_id" varchar(15) UNIQUE,
                        "channel_telegram" varchar(20) UNIQUE,
                        "last_1000_id"  varchar(20) UNIQUE,
                        "last_update_time" varchar(20),
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


class MyError(Exception):
    pass


class DataBase:
    def __init__(self):
        try:
            self.name = 'memes'
            self.db = sqlite3.connect('{0}.db'.format(self.name))

        except sqlite3.Error as err:
            print(err)

        except Exception:
            PrintException()

    def createTables(self, tables: dict):
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
        Get Categories from Database
        :return: list() in format ([name_1, channel_id_1],[name_2, channel_id_2], ...) if success, else empty list()
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

        except Exception:
            result = list()
            PrintException()

        finally:
            self.cursor.close()
            return result

    def Last_id(self, flag, channel_id: str, last_id: Optional[base.String] = None):
        """

        :param channel_id:
        :param last_id:
        :param flag: set = write and update last sended post ID
                   :get = read end use last ID that wrote in DB
        :return: set: True or False
                 get: last ID from DB
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
            raise MyError("Wrong flag value, use 'get or 'set")

    def lastUpdate(self, flag, channel_id: str, last_time: Optional[str] = None):
        """

        :param last_time:
        :param channel_id: choose channel to working with
        :param flag: set = write and update last sended post ID
                   :get = read end use last ID that wrote in DB
        :return: set: True or False
                 get: last ID from DB
        :return:
        """

        cmd_get = f"select `last_update_time` from channels where `channel_id` = '{channel_id}'"
        cmd_set = f"update channels set `last_update_time` = '{last_time}' where `channel_id` = '{channel_id}'"
        cmd_set_2 = f"update channels set `prelast_update_time` = " \
                    f"(select `last_update_time` from channels where `channel_id` = '{channel_id}') " \
                    f"where `channel_id` = '{channel_id}'"
        exception_return = datetime.now()
        exception_return = exception_return.replace(day=exception_return.day + 2).strftime(DT_FORMAT)
        if flag == 'set':
            try:
                self.cursor = self.db.cursor()
                self.cursor.execute(cmd_set_2)
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
            raise MyError("Wrong flag value, use 'get or 'set")

    def preLastUpdate(self, channel_id):
        cmd = f"select prelast_update_time from `channels` where channel_id = '{channel_id}'"
        exception_return = datetime.now()
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
            logging.error(f' lpreastUpdate: maybe function get None from Database {err}')
            return exception_return

    def AddPost(self, message_id, post, channel_name: str):

        cmd = f'insert into `{channel_name}` (message_id, post_id, post_url, post_type) values (?, ?, ?, ?)'
        exc_cmd = f'update {channel_name} set message_id = {message_id},  where post_id = {post.id}'
        try:
            self.cursor = self.db.cursor()
            params = (message_id, post.id, post.url, post.type)
            self.cursor.execute(cmd, params)
            self.db.commit()
            self.cursor.close()
            return True
        except sqlite3.Error as err:
            if 'UNIQUE constraint failed' in err.args[0]:
                logging.warning(f'Duplicate row in AddPost: {err.args}')
                self.cursor.execute(exc_cmd)
                self.db.commit()
                self.cursor.close()
                return True
            else:
                self.cursor.close()
                logging.error(err)
                raise sqlite3.Error
        except Exception as err:
            logging.error(f' AddPost: {err}')
            return False

    def DuplicatePost(self, channel_name, post_id):
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
            return False
    def test(self, channel_name):

        cmd = f'SELECT * FROM `{channel_name}` WHERE id=(SELECT max(id) FROM `{channel_name}`);'
        answer = dict()
        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(cmd)
            record = self.cursor.fetchone()
            self.cursor.close()
            answer['num'] = record[0]
            answer['message_id'] = record[1]
            answer['post_id'] = record[2]
            answer['url'] = record[3]
            answer['type'] = record[4]
            return answer

        except sqlite3.Error as err:
            logging.error(f'test: {err}')
            self.cursor.close()


print(DataBase.DuplicatePost(DataBase(), 'мемы', 'dadadadwq'))