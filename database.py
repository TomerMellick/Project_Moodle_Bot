import sqlite3

DATABASE = 'database.db'
TABLE = 'users'

# def user_login(user_id: str) -> tuple:
#     con = sqlite3.connect(DATABASE)
#     curses = con.cursor()
#     user_row = curses.execute(f'''SELECT * FROM users WHERE user_id={user_id}''')
#     if user_row.fetchone() is None:
#         add_user()
#         user_row = curses.execute(f'''SELECT * FROM users WHERE user_id={user_id}''')
#     return user_row.fetchone()


def add_user(user_id: str, user_name: str, password: str):
    """
    adds a row to TABLE with the parameters
    :param user_id:
    :param user_name:
    :param password:
    :return:
    """
    con = sqlite3.connect(DATABASE)
    curses = con.cursor()
    curses.execute(f'''INSERT INTO {TABLE} VALUES ({user_id}), {user_name}, {password}''')
    con.commit()
    con.close()


def delete_user(user_id: str):
    """
    delete a user by its id
    :param user_id:
    :return:
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        handle.execute(f'''DELETE FROM {TABLE} WHERE user_id = {user_id}''')
        con.commit()


def get_user(user: str) -> tuple:
    """
    gets the row of a user by id or username
    :param user:
    :return: the row as a tuple
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        user_row = handle.execute(f'''SELECT * FROM {TABLE} WHERE user_id={user} OR user_name={user}''')
        return user_row.fetchone()


def get_all_user():
    """
        :return: all the TABLE as sqlite3 object
    """
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        return handle.execute(f'''SELECT * FROM {TABLE} ''')

