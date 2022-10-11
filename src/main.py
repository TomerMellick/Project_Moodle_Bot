import telegram_bot
import multiprocessing
import scheduler


def main():
    token = open('BotToken.txt').readline().strip()
    scheduler_task = multiprocessing.Process(target=scheduler.schedule_messages, args=(token,))
    scheduler_task.start()
    telegram_bot.start_telegram_bot(token)
    scheduler_task.close()


if __name__ == '__main__':
    main()
