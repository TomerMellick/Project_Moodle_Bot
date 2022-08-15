from typing import List

import telegram
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters, \
    CallbackQueryHandler
from internet import Internet, Document, documents_heb_name, documents_file_name
from enum import Enum, auto
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from src import database

users = {}


class GetUser(Enum):
    GET_USERNAME = auto()
    GET_PASSWORD = auto()


async def enter_data(bot: telegram.Bot, chat_id: int):
    await bot.send_message(chat_id=chat_id,
                           text="must enter username and password before using this command")


async def handle_warnings(warning: List[Internet.Warning], bot: telegram.Bot, chat_id: int):
    if Internet.Warning.CHANGE_PASSWORD in warning:
        await bot.send_message(chat_id=chat_id,
                               text="warning: please change your username and password at the orbit website")


async def handle_error(error: Internet.Error, bot: telegram.Bot, chat_id: int):
    if error is Internet.Error.ORBIT_DOWN:
        await bot.send_message(chat_id=chat_id,
                               text="error: orbit website is down")
    elif error is Internet.Error.MOODLE_DOWN:
        await bot.send_message(chat_id=chat_id,
                               text="error: moodle website is down")
    elif error is Internet.Error.WRONG_PASSWORD:
        await bot.send_message(chat_id=chat_id,
                               text="error: username or password is incorrect")
    elif error is Internet.Error.BOT_ERROR:
        await bot.send_message(chat_id=chat_id,
                               text="error: the bot did something stupid, please try again later")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Hello and welcome to our bot.\nPlease enter your orbit username")
    return GetUser.GET_USERNAME


async def update_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit username")
    return GetUser.GET_USERNAME


async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = update.message.text
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit password")
    return GetUser.GET_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    database.add_user(update.effective_chat.id, users.pop(update.effective_chat.id), update.message.text)
    await context.bot.deleteMessage(update.effective_chat.id, update.message.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Thanks")
    return ConversationHandler.END


async def get_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    grades = Internet(data[1], data[2]).get_grades()
    if grades.warnings:
        await handle_warnings(grades.warnings, context.bot, update.effective_chat.id)
    if grades.error:
        await handle_error(grades.error, context.bot, update.effective_chat.id)
        return
    grades = grades.result

    sum_grades = 0
    num_of_units = 0
    for grade in grades:
        if grade.grade.isdigit():
            sum_grades += int(grade.grade) * grade.units
            num_of_units += grade.units
    avg = None
    if num_of_units > 0:
        avg = round(sum_grades / num_of_units, 2)

    grades_text = '\n'.join(f'{grade.name} - {grade.units} - {grade.grade}' for grade in grades if grade.grade != '')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=grades_text + f'\n\n ממוצע: {avg}')


async def get_unfinished_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    events = Internet(data[1], data[2]).get_unfinished_events()
    if events.warnings:
        await handle_warnings(events.warnings, context.bot, update.effective_chat.id)
    if events.error:
        await handle_error(events.error, context.bot, update.effective_chat.id)
        return
    events = events.result
    events_text = '\n---------------------------------------------\n'.join(f'{event.name}\n'
                                                                           f'{event.course_name}\n'
                                                                           f'{event.end_time}\n'
                                                                           f'{event.url}'
                                                                           for event in events)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=events_text)


login_info_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), CommandHandler('update_user', update_user)],
    states={
        GetUser.GET_USERNAME: [MessageHandler(filters.TEXT, get_username)],
        GetUser.GET_PASSWORD: [MessageHandler(filters.TEXT | filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", lambda a, b: 0)],
)


async def update_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("once a day", callback_data='1'),
                                      InlineKeyboardButton("once a week", callback_data='2'),
                                      InlineKeyboardButton("never", callback_data='0')]])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="on what schedule would you like to get you unfinished events?",
                                   reply_markup=keyboard)
    return 1


async def get_document_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=f'document_{doc_num.value}')] for doc_num, name in
         documents_heb_name.items()])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="choose  file to download",
                                   reply_markup=keyboard)


async def call_back_document_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(update, context)
        return
    doc = Document(int(update.callback_query.data[len('document_'):]))
    doc_value = Internet(data[1], data[2]).get_document(doc)
    if doc_value.warnings:
        await handle_warnings(doc_value.warnings, update, context)
    if doc_value.error:
        await handle_error(doc_value.error, update, context)
        return
    doc_value = doc_value.result
    await context.bot.send_document(update.effective_chat.id, doc_value, filename=documents_file_name[doc])


async def call_back_schedule_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    database.update_schedule(update.effective_chat.id, int(update.callback_query.data))
    return ConversationHandler.END


schedule_conversation = ConversationHandler(entry_points=[CommandHandler("update_schedule", update_schedule)], states={
    1: [CallbackQueryHandler(call_back_schedule_button)]
}, fallbacks=[])


def start_telegram_bot():
    application = ApplicationBuilder().token(open('BotToken.txt').readline()).build()
    application.add_handler(login_info_handler)
    application.add_handler(CommandHandler('get_grades', get_grades))
    application.add_handler(CommandHandler('get_unfinished_events', get_unfinished_events))
    application.add_handler(schedule_conversation)
    application.add_handler(CommandHandler('get_document', get_document_buttons))
    application.add_handler(CallbackQueryHandler(call_back_document_button, pattern=r'^document_'))

    application.run_polling()
    return application.bot


if __name__ == '__main__':
    start_telegram_bot()
