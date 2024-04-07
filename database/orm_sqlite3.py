import asyncio
import sqlite3
from abc import abstractmethod, ABCMeta
from collections import namedtuple
from sqlite3 import Connection, Cursor
from typing import Any


class QueryException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.msgfmt = message


class BaseTable(object, metaclass=ABCMeta):
    __slots__ = ("__table_name__", "connection", "cursor", "model_obj")

    def __init__(self, *, table_name: str = '', connection: Connection = None, cursor: Cursor = None):
        self.__table_name__ = table_name
        self.connection = connection
        self.cursor = cursor
        fields_arr = []
        defaults_arr = []
        is_rename = False
        for field in self.__slots__:
            if field.startswith('_'):
                is_rename = True
            fields_arr.append(field)
            defaults_arr.append('')
        self.model_obj = namedtuple(table_name, fields_arr, rename=is_rename, defaults=defaults_arr)


    @abstractmethod
    async def create_table(self):
        ...

    async def add(self, data):
        query_str, values_arr = self.build_insert_query(data)
        try:
            with self.connection:
                self.cursor.execute(query_str, values_arr)
        except sqlite3.Error as er:
            raise er

    async def update(self, data, where):
        query_str, values_arr = self.build_update_query(data, where=where)
        try:
            with self.connection:
                self.cursor.execute(query_str, values_arr)
                self.connection.commit()
        except sqlite3.Error:
            raise

    async def delete(self, **kwargs):
        """
        Delete record(s) from table
        :param kwargs: may contain one or more parameters. In case of 2 or more parameters you must specify logical
        operation between these parameters 'AND' or 'OR', such as: operand='AND'
        :return: None
        """
        where_str = " WHERE "
        where_args = []

        operand = kwargs.get("operand")
        if operand:
            if len(kwargs) < 3:
                raise KeyError(f"operation AND requires more then 1 arguments!")

        for key in kwargs:
            if key == 'operand':
                continue
            where_str += f"{key}=(?)"
            where_args.append(kwargs[key])
            if len(kwargs) > 1:
                where_str += f" {operand} "

        where_str = where_str.removesuffix(f" {operand} ")
        where_str += ";"

        with self.connection:
            self.cursor.execute(f"DELETE FROM {self.__table_name__} {where_str}", where_args)
            self.connection.commit()

    async def count(self, **where) -> int:
        """
        Count record(s) in table
        :param where: may contain one or more parameters. In case of 2 or more parameters you must specify logical
        operation between these parameters 'AND' or 'OR', such as: operand='AND'
        :return: count of records
        """
        where_str = ""
        where_args = []

        operand = where.get("operand")
        if operand:
            if len(where) < 3:
                raise KeyError(f"operation AND requires more then 1 arguments!")

        if len(where):
            where_str = " WHERE "
            for key in where:
                if key == 'operand':
                    continue
                where_str += f"{key}=(?)"
                where_args.append(where[key])
                if len(where) > 1:
                    where_str += f" {operand} "

            where_str = where_str.removesuffix(f" {operand} ")
        where_str += ";"

        with self.connection:
            count = self.cursor.execute(f"SELECT COUNT(*) FROM {self.__table_name__}{where_str}", where_args).fetchall()
            self.connection.commit()

        if len(count):
            count = count[0][0]
        return count

    def build_order_by_str(self, order_by: str or list[str] or None = None) -> str:
        order_by_str = ''
        if order_by:
            order_by = list([order_by]) if isinstance(order_by, str) else order_by
            order_by_str += " ORDER BY "
            for order in order_by:
                # don't order by unknown columns name
                if order not in self.__slots__:
                    continue
                order_by_str += order
                if len(order_by) > 1:
                    order_by_str += ", "
            order_by_str = order_by_str.removesuffix(', ')
            order_by_str += ";"
        return order_by_str

    def _build_order_by_str(self, order_by: str or list[str] or None = None) -> str:
        order_by_str = ''
        if order_by:
            order_by = list([order_by]) if isinstance(order_by, str) else order_by
            order_by_str += " ORDER BY "
            for order in order_by:
                # don't order by unknown columns name
                if order not in self.__slots__:
                    continue
                order_by_str += order
                if len(order_by) > 1:
                    order_by_str += ", "
            order_by_str = order_by_str.removesuffix(', ')
        return order_by_str

    def _build_where_str(self, where: dict[str, Any] or None = None) -> tuple[str, list]:
        values = []
        where_str = ""
        if where:
            where_str = " WHERE "
            for key in where:
                # add to query only known parameters
                if key in self.__slots__:
                    where_str += f"{key}=(?)"
                    values.append(where.get(key))
                if len(where) > 1:
                    where_str += " AND "
            where_str = where_str.removesuffix(f" AND ")
        return where_str, values

    def build_insert_query(self, data) -> tuple[str, list]:
        columns = ""
        values = ""
        values_arr = []
        for index, column_name in enumerate(self.__slots__):
            attr = self.__getattribute__(column_name)
            if type(attr) == int or type(attr) == float:
                attr = str(attr).lower()
            if attr == 'autoincrement':
                continue
            columns += f"{column_name}, "
            values += f"?, "
            values_arr.append(data.get(column_name) or self.__getattribute__(column_name))
        columns = columns.rstrip(' ').removesuffix(',')
        values = values.rstrip(' ').removesuffix(',')
        query_str = f"INSERT INTO {self.__table_name__} ({columns}) VALUES ({values})"

        return query_str, values_arr

    def build_select_query(self,
                           where: dict[str, Any] or None = None,
                           order_by: str or list[str] or None = None) -> tuple[str, list]:
        select_str = f"SELECT * FROM {self.__table_name__}"
        order_by_str = self._build_order_by_str(order_by)
        where_str, values = self._build_where_str(where)

        select_str += f"{where_str}{order_by_str};"
        return select_str, values

    def build_update_query(self, data, where: dict[str, Any] = None) -> tuple[str, list]:
        #  f"UPDATE users SET role=(?), company=(?), company_number=(?) WHERE userid=(?)"
        columns = ""
        values_arr = []
        for column_name in data:
            # add to query only known parameters!
            if column_name in self.__slots__:
                columns += f"{column_name}=(?), "
                values_arr.append(data.get(column_name))
        columns = columns.rstrip(' ').removesuffix(',')
        query_str = f"UPDATE {self.__table_name__} SET {columns}"
        where_str = ""
        if where:
            where_str = " WHERE "
            for key in where:
                where_str += f"{key}=(?)"
                values_arr.append(where.get(key))
                if len(where) > 1:
                    where_str += " AND "
        query_str += where_str
        return query_str, values_arr

    def convert_to_data(self, raw_data) -> dict[str, Any]:
        data: dict = {}
        for index, column_name in enumerate(self.__slots__):
            if column_name.startswith('_'):
                continue
            data[column_name] = raw_data[index]

        return data

    def convert_to_model_obj(self, raw_data) -> Any:
        values_arr = []
        for index, col_name in enumerate(self.__slots__):
            if col_name.startswith('_'):
                continue
            values_arr.append(raw_data[index])

        return self.model_obj._make(values_arr)


class ImageTable(BaseTable):
    __slots__ = ("file_id", "path")

    def __init__(self, connection: Connection, cursor: Cursor):
        super().__init__(table_name="image", connection=connection, cursor=cursor)
        self.file_id: str = ''
        self.path: str = ''

    async def create_table(self):
        create_table_query = f"CREATE TABLE IF NOT EXISTS {self.__table_name__}(" \
                             f"{self.__slots__[0]} TEXT," \
                             f"{self.__slots__[1]} TEXT)"
        try:
            with self.connection:
                self.cursor.execute(create_table_query)
                self.connection.commit()
        except sqlite3.Error as er:
            print("Failed to create table: 'image'", er)

    async def add_image(self, data: dict[str, str]):
        try:
            await self.add(data)
        except sqlite3.Error as er:
            print("add_image error:", er)

    async def get_image(self, path: str) -> Any:
        image = None
        try:
            with self.connection:
                row = self.cursor.execute(f"SELECT * FROM {self.__table_name__} WHERE path=(?);", [path]).fetchone()
                if row:
                    image = self.convert_to_model_obj(row)
        except sqlite3.Error as er:
            print("get_image error:", er)
        return image


class RulesTable(BaseTable):
    __slots__ = ("recip_name", "recip_id", "donor_name", "donor_id", "sender_fname", "sender_lname", "sender_uname",
                 "sender_id", "filter", "black_list", "and_list", "or_list", "format", "title", "status", "user_id")

    def __init__(self, connection: Connection, cursor: Cursor):
        super().__init__(table_name="rules", connection=connection, cursor=cursor)
        self.recip_name: str = ''
        self.recip_id: int = 0
        self.donor_name: str = ''
        self.donor_id: int = 0
        self.sender_fname: str = ''
        self.sender_lname: str = ''
        self.sender_uname: str = ''
        self.sender_id: int = 0
        self.filter: str = ''       # must contain the * character to disable filtering and accept all messages.
                                    # Can also contain single words in combination with '*', '!', ' & ',' | '
        self.black_list: str = ''   # '|' separated list of forbidden words in the message.text, may be empty
        self.and_list: str = ''     # '+' separated list of words that must be in the message.text, may be empty
        self.or_list: str = ''      # '|' separated list of words, at least one of which must be found in the text,
                                    # may be empty
        self.format: str = ''
        self.title: str = ''
        self.status: str = ""       # set to 'active' to activate the rule!
        self.user_id: int = 0

    async def create_table(self):
        create_table_query = f"CREATE TABLE IF NOT EXISTS {self.__table_name__}(" \
                             f"{self.__slots__[0]} TEXT," \
                             f"{self.__slots__[1]} INT," \
                             f"{self.__slots__[2]} TEXT," \
                             f"{self.__slots__[3]} INT," \
                             f"{self.__slots__[4]} TEXT," \
                             f"{self.__slots__[5]} TEXT," \
                             f"{self.__slots__[6]} TEXT," \
                             f"{self.__slots__[7]} INT," \
                             f"{self.__slots__[8]} TEXT," \
                             f"{self.__slots__[9]} TEXT," \
                             f"{self.__slots__[10]} TEXT," \
                             f"{self.__slots__[11]} TEXT," \
                             f"{self.__slots__[12]} TEXT," \
                             f"{self.__slots__[13]} TEXT," \
                             f"{self.__slots__[14]} TEXT," \
                             f"{self.__slots__[15]} INT)"
        try:
            with self.connection:
                self.cursor.execute(create_table_query)
                self.connection.commit()
        except sqlite3.Error as er:
            print(f"Failed to create table: '{self.__table_name__}'", er)

    async def add_rule(self, data: dict[str, Any]):
        try:
            await self.add(data)
        except sqlite3.Error as er:
            print("add_rule error:", er)

    async def get_rules(self, where: dict[str, Any] or None = None,
                        order_by: str or list[str] or None = None) -> list[Any]:
        rules = []
        query_str, values = self.build_select_query(where=where, order_by=order_by)
        try:
            with self.connection:
                rows = self.cursor.execute(query_str, values).fetchall()
                for row in rows:
                    obj = self.convert_to_model_obj(row)
                    rules.append(obj)
        except sqlite3.Error as er:
            print("get_users error:", er)
        return rules

    async def delete_all_rules(self):
        with self.connection:
            self.cursor.execute(f"DELETE FROM {self.__table_name__};")
            self.connection.commit()


class Database:
    def __init__(self, *, db_file: str = ''):
        self.connection = sqlite3.connect(db_file if len(db_file) else ":memory:")
        self.cursor = self.connection.cursor()

        self.image_table: ImageTable = ImageTable(connection=self.connection, cursor=self.cursor)
        self.rules_table: RulesTable = RulesTable(connection=self.connection, cursor=self.cursor)

    async def disconnect(self):
        self.cursor.close()
        self.connection.close()

    def get_image_table(self) -> ImageTable:
        return self.image_table

    def get_rules_table(self) -> RulesTable:
        return self.rules_table

    async def create_tables(self):
        await self.image_table.create_table()
        await self.rules_table.create_table()


async def start():
    db = Database(db_file="test_db.db")
    await db.create_tables()


if __name__ == '__main__':
    asyncio.run(start())

