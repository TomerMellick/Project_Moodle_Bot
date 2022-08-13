from typing import List

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from datetime import datetime
from internet import Internet
from enum import Enum, auto
from telegram import Update
from src import database

users = {}


class GET_USER(Enum):
    GET_USERNAME = auto()
    GET_PASSWORD = auto()


async def enter_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="must enter username and password before using this command")

async def handle_warnings(warning: List[Internet.Warning], update: Update, context: ContextTypes.DEFAULT_TYPE):
    if Internet.Warning.CHANGE_PASSWORD in warning:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="warning: please change your username and password at the orbit website")


async def handle_error(error: Internet.Error, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if error is Internet.Error.ORBIT_DOWN:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="error: orbit website is down")
    elif error is Internet.Error.MOODLE_DOWN:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="error: moodle website is down")
    elif error is Internet.Error.WRONG_PASSWORD:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="error: username or password is incorrect")
    elif error is Internet.Error.BOT_ERROR:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="error: the bot did something stupid, please try again later")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Hello and welcome to our bot.\nPlease enter your orbit username")
    return GET_USER.GET_USERNAME


async def update_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit username")
    return GET_USER.GET_USERNAME


async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = update.message.text
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit password")
    return GET_USER.GET_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    database.add_user(update.effective_chat.id, users[update.effective_chat.id], update.message.text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Thanks")
    return ConversationHandler.END


async def get_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(update, context)
        return
    grades = Internet(data[1], data[2]).get_grades()
    if grades.warnings:
        await handle_warnings(grades.warnings, update, context)
    if grades.error:
        await handle_error(grades.error, update, context)
        return
    grades = grades.result
    grades_text = '\n'.join(f'{grade.name} - {grade.units} - {grade.grade}' for grade in grades if grade.grade != '')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=grades_text)


async def get_unfinished_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(update, context)
        return
    events = Internet(data[1], data[2]).get_unfinished_events()
    if events.warnings:
        await handle_warnings(events.warnings, update, context)
    if events.error:
        await handle_error(events.error, update, context)
        return
    events = events.result
    grades_text = '\n----------\n'.join(f'{event.name}\n'
                                        f'{event.course_name}\n'
                                        f'{datetime.fromtimestamp(event.end_time)}\n'
                                        f'{event.url}'
                                        for event in events)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=grades_text)


login_info_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), CommandHandler('update_user', update_user)],
    states={
        GET_USER.GET_USERNAME: [MessageHandler(filters.TEXT, get_username)],
        GET_USER.GET_PASSWORD: [MessageHandler(filters.TEXT | filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", lambda a, b: 0)],
)


def start_telegram_bot():
    application = ApplicationBuilder().token(open('BotToken.txt').readline()).build()
    application.add_handler(login_info_handler)
    application.add_handler(CommandHandler('get_grades', get_grades))
    application.add_handler(CommandHandler('get_unfinished_events', get_unfinished_events))
    application.run_polling()
    return application.bot


if __name__ == '__main__':
    start_telegram_bot()
