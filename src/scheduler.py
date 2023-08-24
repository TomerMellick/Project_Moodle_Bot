import asyncio
import datetime
import schedule
import telegram
import database
import internet
import time
import telegram_bot


async def async_send_messages(token, all_users, time_scope):
    try:
        await asyncio.gather(*[send_scheduled_event(token, user, time_scope) for user in all_users])
    except Exception as e:
        print(e)


def once_a_day(token: str):
    all_users = database.get_users_by_schedule(1)
    time_scope = datetime.datetime.now() + datetime.timedelta(days=1)
    asyncio.run(async_send_messages(token, all_users, time_scope))


def once_a_week(token: str):
    all_users = database.get_users_by_schedule(2)
    time_scope = datetime.datetime.now() + datetime.timedelta(days=7)
    asyncio.run(async_send_messages(token, all_users, time_scope))


async def send_scheduled_event(token: str, user: database.User, time_scope: datetime.datetime):
    """
    send the unfinished events by the given time scope
    :param token:
    :param user:
    :param time_scope:
    :return:
    """
    bot = telegram.Bot(token)
    unfinished_events = internet.Internet.create(user).get_unfinished_events(time_scope)
    if not unfinished_events:
        return
    if unfinished_events.warnings:
        await telegram_bot.handle_warnings(unfinished_events.warnings, bot, user.user_id)
    if unfinished_events.error:
        await telegram_bot.handle_error(unfinished_events.error, bot, user.user_id)
        return
    events = unfinished_events.result
    events_text = "no events"
    if events:
        events_text = '\n---------------------------------------------\n'.join(f'{event.name}\n'
                                                                               f'{event.course_name}\n'
                                                                               f'{event.end_time}\n'
                                                                               f'{event.url}'
                                                                               for event in events)

    await bot.send_message(chat_id=user.user_id, text=events_text)


def schedule_messages(token: str):
    """
    schedule sending the messages and call the scheduled jobs
    :param token:
    :return:
    """
    schedule.every().day.at("06:00").do(once_a_day, token)
    schedule.every().sunday.at("06:00").do(once_a_week, token)

    while True:
        schedule.run_pending()
        time.sleep(1)
