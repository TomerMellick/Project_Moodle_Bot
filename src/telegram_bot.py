import datetime
from typing import List

import telegram
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters, \
    CallbackQueryHandler

import internet
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
                           text="must enter username and password before using this command \nuse /update_user")


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
                               text="error: username or password is incorrect use /update_user to update them")
    elif error is Internet.Error.BOT_ERROR:
        await bot.send_message(chat_id=chat_id,
                               text="error: the bot did something stupid, please try again later")
    elif error is Internet.Error.CHANGE_PASSWORD:
        await bot.send_message(chat_id=chat_id,
                               text="error: you need to change the password in the orbit site "
                                    "or by using /change_password command")
    elif error is Internet.Error.OLD_EQUAL_NEW_PASSWORD:
        await bot.send_message(chat_id=chat_id,
                               text="error: Please enter password that was never in use or /cancel to cancel")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Hello and welcome to our bot.\nPlease enter your orbit username")
    return GetUser.GET_USERNAME


async def update_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit username")
    return GetUser.GET_USERNAME


async def change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your new orbit password "
                                                                          "or /cancel to cancel")
    return GetUser.GET_PASSWORD


async def get_new_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    await context.bot.deleteMessage(update.effective_chat.id, update.message.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    new_password = Internet(data.user_name, data.password).change_password(update.message.text)
    if new_password.warnings:
        await handle_warnings(new_password.warnings, context.bot, update.effective_chat.id)
    if new_password.error:
        await handle_error(new_password.error, context.bot, update.effective_chat.id)
        return GetUser.GET_PASSWORD
    database.add_user(update.effective_chat.id, data.user_name, update.message.text)
    await context.bot.send_message(update.effective_chat.id, text="password changed successfully")
    return ConversationHandler.END


async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = update.message.text
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter your orbit password")
    return GetUser.GET_PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = users.pop(update.effective_chat.id)
    password = update.message.text
    database.add_user(update.effective_chat.id, username, password)
    await context.bot.deleteMessage(update.effective_chat.id, update.message.id)
    if Internet(username, password).connect_orbit().result:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Thanks")
        return ConversationHandler.END
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="username or password are incorrect\n"
                                            "Please enter your username again")
        return GetUser.GET_USERNAME


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


async def get_grade_distribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    grades = Internet(data.user_name, data.password).get_grades()
    if grades.warnings:
        await handle_warnings(grades.warnings, context.bot, update.effective_chat.id)
    if grades.error:
        await handle_error(grades.error, context.bot, update.effective_chat.id)
        return
    grades = grades.result

    keyword = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f'{grade.name}', callback_data=f'grade_distribution_{grade.grade_distribution}')]
            for grade in grades if grade.grade_distribution
        ]
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text='select subject', reply_markup=keyword)


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


async def update_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("once a day", callback_data='schedule_1'),
                                      InlineKeyboardButton("once a week", callback_data='schedule_2'),
                                      InlineKeyboardButton("never", callback_data='schedule_0')]])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="on what schedule would you like to get you unfinished events?",
                                   reply_markup=keyboard)


async def get_document_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=f'document_{doc_num.value}')] for doc_num, name in
         documents_heb_name.items()])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="choose  file to download",
                                   reply_markup=keyboard)


async def call_back_get_grade_distribution_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    grade_distribution_id = update.callback_query.data[len('grade_distribution_'):]
    grade_distribution = Internet(data.user_name, data.password).get_grade_distribution(grade_distribution_id)
    if grade_distribution.warnings:
        await handle_warnings(grade_distribution.warnings, context.bot, update.effective_chat.id)
    if grade_distribution.error:
        await handle_error(grade_distribution.error, context.bot, update.effective_chat.id)
        return
    grade_distribution = grade_distribution.result
    text = f'ציונך: {grade_distribution.grade}\n' \
           f'ממוצע: {grade_distribution.average}\n' \
           f'ס.ת: {grade_distribution.standard_deviation}\n' \
           f'דירוג: {grade_distribution.position}\n'
    await context.bot.send_message(update.effective_chat.id, text=text)
    await context.bot.send_photo(update.effective_chat.id, grade_distribution.image)


async def get_notebook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    exams = Internet(data.user_name, data.password).get_all_exams()
    if exams.warnings:
        await handle_warnings(exams.warnings, context.bot, update.effective_chat.id)
    if exams.error:
        await handle_error(exams.error, context.bot, update.effective_chat.id)
        return
    exams = exams.result
    exams = [exam for exam in exams if exam.notebook_url]
    exams.sort(key=lambda a: a.time_start, reverse=True)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f'{exam.name} {exam.number}', callback_data=f'notebook_{exam.notebook_url}')]
         for exam in exams])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="choose notebook to download",
                                   reply_markup=keyboard)


async def get_upcoming_exams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    exams = Internet(data.user_name, data.password).get_all_exams()
    if exams.warnings:
        await handle_warnings(exams.warnings, context.bot, update.effective_chat.id)
    if exams.error:
        await handle_error(exams.error, context.bot, update.effective_chat.id)
        return
    exams = exams.result
    now = datetime.datetime.now()
    exams = [exam for exam in exams if exam.time_start > now]
    exams.sort(key=lambda a: a.time_start)
    text = '\n--------\n\n'.join(f'{exam.name} {exam.number}\n{exam.room}\n{exam.time_start}\n{exam.time_end}'
                                 for exam in exams)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text)


async def call_back_notebook_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    notebook_id = int(update.callback_query.data[len('notebook_'):])
    in_user = Internet(data.user_name, data.password)
    notebook = in_user.get_exam_notebook(notebook_id)
    if notebook.warnings:
        await handle_warnings(notebook.warnings, context.bot, update.effective_chat.id)
    if notebook.error:
        await handle_error(notebook.error, context.bot, update.effective_chat.id)
        return
    notebook = notebook.result
    await context.bot.send_document(update.effective_chat.id, notebook, filename=f'notebook.pdf')


async def call_back_document_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    doc = Document(int(update.callback_query.data[len('document_'):]))
    doc_value = Internet(data[1], data[2]).get_document(doc)
    if doc_value.warnings:
        await handle_warnings(doc_value.warnings, context.bot, update.effective_chat.id)
    if doc_value.error:
        await handle_error(doc_value.error, context.bot, update.effective_chat.id)
        return
    doc_value = doc_value.result
    await context.bot.send_document(update.effective_chat.id, doc_value, filename=documents_file_name[doc])


async def call_back_schedule_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value_int = int(update.callback_query.data[len('schedule_')])
    value_text = ['never', 'once a day', 'once a week'][value_int]
    database.update_schedule(update.effective_chat.id, value_int)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"schedule message to unfinished events set to `{value_text}`")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id, text="operation canceled")
    return ConversationHandler.END


login_info_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), CommandHandler('update_user', update_user)],
    states={
        GetUser.GET_USERNAME: [MessageHandler(filters.TEXT, get_username)],
        GetUser.GET_PASSWORD: [MessageHandler(filters.TEXT | filters.COMMAND, get_password)],
    },
    fallbacks=[],
)
change_password_handler = ConversationHandler(
    entry_points=[CommandHandler("change_password", change_password)],
    states={
        GetUser.GET_PASSWORD: [MessageHandler(filters.TEXT & (~ filters.COMMAND), get_new_password)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


def start_telegram_bot(token: str):
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('get_grades', get_grades))
    application.add_handler(CommandHandler('get_unfinished_events', get_unfinished_events))
    application.add_handler(CommandHandler('get_document', get_document_buttons))
    application.add_handler(CommandHandler('update_schedule', update_schedule))
    application.add_handler(CommandHandler('get_notebook', get_notebook))
    application.add_handler(CommandHandler('get_upcoming_exams', get_upcoming_exams))
    application.add_handler(CommandHandler('get_grade_distribution', get_grade_distribution))

    application.add_handler(login_info_handler)
    application.add_handler(change_password_handler)

    application.add_handler(CallbackQueryHandler(call_back_document_button, pattern=r'^document_'))
    application.add_handler(CallbackQueryHandler(call_back_schedule_button, pattern=r'^schedule_'))
    application.add_handler(CallbackQueryHandler(call_back_notebook_button, pattern=r'^notebook_'))
    application.add_handler(CallbackQueryHandler(call_back_get_grade_distribution_button,
                                                 pattern=r'^grade_distribution_'))

    application.run_polling()


if __name__ == '__main__':
    start_telegram_bot(open('BotToken.txt').readline())
