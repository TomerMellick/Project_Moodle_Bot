import datetime
from typing import List
from enum import Enum, auto


import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, \
    filters, CallbackQueryHandler

from internet import Internet, Document, documents_heb_name, documents_file_name
import database

users = {}


def get_user(f):
    async def function(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = database.get_user_by_id(update.effective_chat.id)
        if not user:
            await enter_data(context.bot, update.effective_chat.id)
            return
        return await f(user, update, context, *args, **kwargs)

    return function


def internet_func(internet_function, value_on_error=None, btn_name=None, btn_value_func=None, get_message=False):
    def decorator(function):
        @get_user
        async def actual_function(user: database.User, update: Update, context: ContextTypes.DEFAULT_TYPE):

            if btn_name:
                btn_value = update.callback_query.data[len(btn_name):]
                if btn_value_func:
                    btn_value = btn_value_func(btn_value)
                res = internet_function(Internet(user), btn_value)
            elif get_message:
                res = internet_function(Internet(user), update.message.text)
            else:
                res = internet_function(Internet(user))

            if res.warnings:
                await handle_warnings(res.warnings, context.bot, update.effective_chat.id)
            if res.error:
                await handle_error(res.error, context.bot, update.effective_chat.id)
                return value_on_error
            return await function(user, res.result, update, context)

        return actual_function

    return decorator


class GetUser(Enum):
    GET_USERNAME = auto()
    GET_PASSWORD = auto()


async def enter_data(bot: telegram.Bot, chat_id: int):
    await bot.send_message(chat_id=chat_id,
                           text="must enter username and password before using this command\n"
                                "/update_user")


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


@internet_func(Internet.change_password, value_on_error=GetUser.GET_PASSWORD, get_message=True)
async def get_new_password(user, _, update: Update, context: ContextTypes.DEFAULT_TYPE):
    database.add_user(update.effective_chat.id, user.user_name, update.message.text)
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
    if Internet(database.User(update.effective_chat.id, username, password, 0, 0)).connect_orbit().result:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Thanks")
        return ConversationHandler.END
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="username or password are incorrect\n"
                                            "Please enter your username again")
        return GetUser.GET_USERNAME


async def get_time_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f'סמסטר א', callback_data=f'time_table_1'),
                InlineKeyboardButton(f'סמסטר ב', callback_data=f'time_table_2'),
                InlineKeyboardButton(f'סמסטר קיץ', callback_data=f'time_table_3')
            ]
        ]
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text='select semester', reply_markup=keyword)


@internet_func(Internet.get_time_table, btn_name='time_table_', btn_value_func=int)
async def call_back_time_table_button(_, res, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if res:
        await context.bot.send_document(update.effective_chat.id, res[1], filename=res[0])
    else:
        await context.bot.send_message(update.effective_chat.id, "can't find the time table")


@internet_func(Internet.get_grades)
async def get_grades(_, grades, update: Update, context: ContextTypes.DEFAULT_TYPE):
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


@internet_func(Internet.get_years)
async def set_year(_, years, update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f'default', callback_data=f'set_year_0')]] +
        [
            [InlineKeyboardButton(f'{year}', callback_data=f'set_year_{year}')]
            for year in years
        ]
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text='select year', reply_markup=keyword)


@internet_func(Internet.get_grades)
async def get_grade_distribution(_, grades, update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f'{grade.name}', callback_data=f'grade_distribution_{grade.grade_distribution}')]
            for grade in grades if grade.grade_distribution
        ]
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text='select subject', reply_markup=keyword)


@internet_func(Internet.get_unfinished_events)
async def get_unfinished_events(_, events, update: Update, context: ContextTypes.DEFAULT_TYPE):
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



# async def get_notebook(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     data = database.get_user_by_id(update.effective_chat.id)
#     if not data:
#         await enter_data(context.bot, update.effective_chat.id)
#         return
#     exams = Internet(data.user_name, data.password).get_all_exams()
#     if exams.warnings:
#         await handle_warnings(exams.warnings, context.bot, update.effective_chat.id)
#     if exams.error:
#         await handle_error(exams.error, context.bot, update.effective_chat.id)
#         return
#     exams = exams.result
#     exams = [exam for exam in exams if exam.notebook]

@internet_func(Internet.get_grade_distribution, btn_name='grade_distribution_')
async def call_back_get_grade_distribution_button(_,
                                                  grade_distribution,
                                                  update: Update,
                                                  context: ContextTypes.DEFAULT_TYPE):
    text = f'ציונך: {grade_distribution.grade}\n' \
           f'ממוצע: {grade_distribution.average}\n' \
           f'ס.ת: {grade_distribution.standard_deviation}\n' \
           f'דירוג: {grade_distribution.position}\n'
    await context.bot.send_message(update.effective_chat.id, text=text)
    await context.bot.send_photo(update.effective_chat.id, grade_distribution.image)


@internet_func(Internet.get_all_exams)
async def get_notebook(_, exams, update: Update, context: ContextTypes.DEFAULT_TYPE):
    exams = [exam for exam in exams if exam.notebook_url]
    exams.sort(key=lambda a: a.time_start, reverse=True)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f'{exam.name} {exam.period}', callback_data=f'notebook_{exam.number}')]
         for exam in exams])

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="choose notebook to download",
                                   reply_markup=keyboard)

@internet_func(Internet.get_all_exams)
async def register_period(_, exams, update: Update, context: ContextTypes.DEFAULT_TYPE):
    exams.sort(key=lambda a: a.time_start, reverse=False)
    buttons = []
    for exam in exams:
        if exam.register:
            buttons.append([InlineKeyboardButton(f'רישום {exam.name} {exam.period}',
                                                 callback_data=f'register_period_1_{exam.number}')])
        elif exam.cancel_register:
            buttons.append([InlineKeyboardButton(f'ביטול רישום {exam.name} {exam.period}',
                                                 callback_data=f'register_period_0_{exam.number}')])
    keyboard = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="register or cancel register",
                                   reply_markup=keyboard)



# @internet_func(Internet.register_exam, btn_name='register_period_', btn_value_func=lambda x: Document(int(x)))
# todo: add this decorator (some variables in the function)
async def call_back_register_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = database.get_user_by_id(update.effective_chat.id)
    if not data:
        await enter_data(context.bot, update.effective_chat.id)
        return
    register_data = update.callback_query.data[len('register_period_'):].split('_')
    register_data[0] = register_data[0] == '1'
    res = Internet(data).register_exam(register_data[1], register_data[0])
    if res.error:
        await handle_error(res.error, context.bot, update.effective_chat.id)
        return
    exams = Internet(data).get_all_exams()
    if exams.error:
        await handle_error(exams.error, context.bot, update.effective_chat.id)
        return
    exams = exams.result
    buttons = []
    for exam in exams:
        if exam.register:
            buttons.append([InlineKeyboardButton(f'רישום {exam.name} {exam.period}',
                                                 callback_data=f'register_period_1_{exam.number}')])
        elif exam.cancel_register:
            buttons.append([InlineKeyboardButton(f'ביטול רישום {exam.name} {exam.period}',
                                                 callback_data=f'register_period_0_{exam.number}')])
    keyboard = InlineKeyboardMarkup(buttons)

    await context.bot.edit_message_reply_markup(update.effective_chat.id, update.effective_message.id, reply_markup=keyboard)


@internet_func(Internet.get_all_exams)
async def get_upcoming_exams(_, exams, update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    exams = [exam for exam in exams if exam.time_start > now]
    exams.sort(key=lambda a: a.time_start)
    text = '\n--------\n\n'.join(f'{exam.name} {exam.period}\n{exam.room}\n{exam.time_start}\n{exam.time_end}'
                                 for exam in exams)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text)


@internet_func(Internet.get_classes)
async def register_class(_, classes, update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(my_class, callback_data=f'register_class_{my_class}')] for my_class in classes])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="select class", reply_markup=keyboard)


@internet_func(Internet.register_for_class, btn_name='register_class_')
async def call_back_register_class_button(_, res, update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_message = '\n-------\n'.join(f'{lesson[1]}-{lesson[2]}' for lesson in res[0])
    if register_message:
        register_message = "register to:\n" + register_message
    unregister_message = '\n-------\n'.join(f'{lesson[1]}-{lesson[2]}' for lesson in res[1])
    if unregister_message:
        unregister_message = "\nproblem with:\n" + unregister_message
    message = register_message + unregister_message
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


@internet_func(Internet.get_exam_notebook, btn_name='notebook_', btn_value_func=int)
async def call_back_notebook_button(_, notebook, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_document(update.effective_chat.id, notebook, filename=f'notebook.pdf')


@internet_func(Internet.get_document, btn_name='document_', btn_value_func=lambda x: Document(int(x)))
async def call_back_document_button(_, doc_value, update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = Document(int(update.callback_query.data[len('document_'):]))
    await context.bot.send_document(update.effective_chat.id, doc_value, filename=documents_file_name[doc])


async def call_back_schedule_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value_int = int(update.callback_query.data[len('schedule_'):])
    value_text = ['never', 'once a day', 'once a week'][value_int]
    database.update_schedule(update.effective_chat.id, value_int)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"schedule message to unfinished events set to `{value_text}`")

async def call_back_set_year_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value_int = int(update.callback_query.data[len('set_year_'):])
    database.update_year(update.effective_chat.id, value_int)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"year set to `{value_int if value_int else 'default'}`")


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
    application.add_handler(CommandHandler('register_period', register_period))
    application.add_handler(CommandHandler('get_grade_distribution', get_grade_distribution))
    application.add_handler(CommandHandler('register_class', register_class))
    application.add_handler(CommandHandler('set_year', set_year))
    application.add_handler(CommandHandler('get_time_table', get_time_table))

    application.add_handler(login_info_handler)
    application.add_handler(change_password_handler)

    application.add_handler(CallbackQueryHandler(call_back_document_button, pattern=r'^document_'))
    application.add_handler(CallbackQueryHandler(call_back_schedule_button, pattern=r'^schedule_'))
    application.add_handler(CallbackQueryHandler(call_back_notebook_button, pattern=r'^notebook_'))
    application.add_handler(CallbackQueryHandler(call_back_register_button, pattern=r'^register_period_'))
    application.add_handler(CallbackQueryHandler(call_back_set_year_button, pattern=r'^set_year_'))
    application.add_handler(CallbackQueryHandler(call_back_register_class_button, pattern=r'^register_class_'))
    application.add_handler(CallbackQueryHandler(call_back_time_table_button, pattern=r'^time_table_'))
    application.add_handler(CallbackQueryHandler(call_back_get_grade_distribution_button,
                                                 pattern=r'^grade_distribution_'))

    application.run_polling()


if __name__ == '__main__':
    start_telegram_bot(open('BotToken.txt').readline())
