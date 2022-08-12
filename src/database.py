import sqlite3

DATABASE = 'database.db'
TABLE = 'users'


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
        curses.execute(f'INSERT INTO {TABLE} VALUES(?,?,?)', (user_id, user_name, password))


def delete_user(user_id: int):
    """
    delete a user by its id
    :param user_id:
    :return:
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        handle.execute(f'DELETE FROM {TABLE} WHERE user_id = ?', (user_id,))


def get_user_by_id(user_id: int) -> tuple:
    """
    gets the row of a user by id
    :param user_id:
    :return: the row as a tuple
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        user_row = handle.execute(f'SELECT * FROM {TABLE} WHERE user_id=?', (user_id,))
        return user_row.fetchone()


def get_all_user():
    """
    :return: all the TABLE as sqlite3 object
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        return handle.execute(f'SELECT * FROM {TABLE}')
