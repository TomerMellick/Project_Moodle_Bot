from enum import Enum, auto

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters

from internet import Internet
from src import database

users = {}


class GET_USER(Enum):
    GET_USERNAME = auto()
    GET_PASSWORD = auto()


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
    grades = Internet(data[1], data[2]).get_grades()
    grades_text = '\n'.join(f'{grade.name} - {grade.units} - {grade.grade}' for grade in grades if grade.grade != '')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=grades_text)


login_info_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), CommandHandler('update_user', update_user)],
    states={
        GET_USER.GET_USERNAME: [MessageHandler(filters.TEXT, get_username)],
        GET_USER.GET_PASSWORD: [MessageHandler(filters.TEXT | filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", lambda a, b: 0)],
)

if __name__ == '__main__':
    application = ApplicationBuilder().token(open('BotToken.txt').readline()).build()
    application.add_handler(login_info_handler)
    application.add_handler(CommandHandler('get_grades',get_grades))
    application.run_polling()
