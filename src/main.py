import telegram_bot
import database
import scheduler


def main():
    bot = telegram_bot.start_telegram_bot()
    scheduler.schedule_messages(bot)


if __name__ == '__main__':
    main()
