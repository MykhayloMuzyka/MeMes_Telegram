import sqlite3
from settings import PrintException

TABLES = dict()

TABLES['channels'] = '''
                     CREATE TABLE "channels" (
                        "id"	INTEGER NOT NULL,
                        "name"	varchar(30) NOT NULL,
                        "channel_id"	varchar(15) NOT NULL UNIQUE,
                        PRIMARY KEY("id" AUTOINCREMENT)
                        );
                     '''

TABLES['telegram_channel'] = '''
                     CREATE TABLE "telegram_channel" (
                        "id"	INTEGER NOT NULL,
                        "name"	varchar(30) NOT NULL,
                        "link"	varchar(50) NOT NULL UNIQUE,
                        PRIMARY KEY("id" AUTOINCREMENT)
                        );
                     '''

class DataBase():
    def __init__(self):
        try:
            self.name = 'memes'
            self.db = sqlite3.connect('{0}.db'.format(self.name))
            self.cursor = self.db.cursor()

        except sqlite3.Error as err:
            print(err)

        except Exception:
            PrintException()

    def createTables(self, tables: dict):
        self.cursor = self.db.cursor()
        result = True
        for table in tables:
            try:
                self.cursor.execute(tables[table])
                print('Create table ok')
            except sqlite3.Error as err:
                print('Create table ERR', err)
                result = False
            finally:
                self.cursor.close()
        self.db.commit()

        return result

    def WriteChannels(self, channel_list):
        cmd = "insert into channels (channel_id, name) values (?, ?)"
        result = True

        self.cursor = self.db.cursor()
        for ch_id, ch_name in channel_list:
            try:
                self.cursor.execute(cmd, (ch_id, ch_name,))
                self.db.commit()

            except sqlite3.Error as err:
                if 'UNIQUE constraint failed' and 'channel_id' in err.args[0]:
                    pass
                    #  print(f'This channels already exists : {ch_name, ch_id}')
                else:
                    result = False
                    print(err)

            except Exception:
                result = False
                PrintException()

        self.cursor.close()
        return result

    def ReadChannels(self):
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
            print(err)

        except Exception:
            result = list()

            PrintException()

        finally:
            self.cursor.close()
            return result