import sqlite3

DATABASE = 'database.db'


# def user_login(user_id: str) -> tuple:
#     con = sqlite3.connect(DATABASE)
#     curses = con.cursor()
#     user_row = curses.execute(f'''SELECT * FROM users WHERE user_id={user_id}''')
#     if user_row.fetchone() is None:
#         add_user()
#         user_row = curses.execute(f'''SELECT * FROM users WHERE user_id={user_id}''')
#     return user_row.fetchone()


def add_user(user_id: str, user_name: str, password: str):
    con = sqlite3.connect(DATABASE)
    curses = con.cursor()
    curses.execute(f'''INSERT INTO users VALUES ({user_id}), {user_name}, {password}''')
    con.commit()
    con.close()


def delete_user(user_id: str):
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        handle.execute(f'''DELETE FROM users WHERE user_id = {user_id}''')
        con.commit()


def get_user(user: str) -> tuple:
    with sqlite3.connect(DATABASE) as con:
        handle = con.cursor()
        user_row = handle.execute(f'''SELECT * FROM users WHERE user_id={user} OR user_name={user}''')
        return user_row.fetchone()
