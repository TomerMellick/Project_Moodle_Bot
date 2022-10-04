import sqlite3
from collections import namedtuple
from typing import Iterator

DATABASE = 'database.db'
TABLE = 'users'

User = namedtuple('User', 'user_id user_name password schedule_code, year')


def add_user(user_id: int, user_name: str, password: str):
    """
    adds a row to TABLE with the parameters
    if exist user_id, remove that row
    :param user_id:
    :param user_name:
    :param password:
    :return:
    """
    # delete if exist
    delete_user(user_id)

    with sqlite3.connect(DATABASE) as con:
        curses = con.cursor()
        curses.execute(f'INSERT INTO {TABLE} VALUES(?,?,?,0,0)', (user_id, user_name, password))


def delete_user(user_id: int):
    """
    delete a user by its id
    :param user_id:
    :return:
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        handle.execute(f'DELETE FROM {TABLE} WHERE user_id = ?', (user_id,))


def get_user_by_id(user_id: int) -> User:
    """
    gets the row of a user by id
    :param user_id:
    :return: the row as a tuple
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        user_row = handle.execute(f'SELECT * FROM {TABLE} WHERE user_id=?', (user_id,))
        user = user_row.fetchone()
        if not user:
            return user

        return User(*user)


def get_all_users() -> Iterator[User]:
    """
    :return: all the TABLE as sqlite3 object
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        return (User(*user) for user in handle.execute(f'SELECT * FROM {TABLE}'))


def update_schedule(user_id: int, schedule_code: int):
    """
    updates the schedule_code field in a given user
    :param user_id:
    :param schedule_code:
    :return:
    """
    with sqlite3.connect(DATABASE) as con:
        curses = con.cursor()
        curses.execute(f'UPDATE {TABLE} SET schedule_code =? WHERE user_id=? ', (schedule_code, user_id))


def get_users_by_schedule(schedule_code: int) -> Iterator[User]:
    """

    :param schedule_code:
    :return:
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()

        return (User(*user) for user in
                handle.execute(f'SELECT * FROM {TABLE} WHERE schedule_code=?', (schedule_code,)))
