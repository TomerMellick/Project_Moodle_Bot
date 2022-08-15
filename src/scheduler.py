import datetime
import schedule
import telegram
import database
import internet
import time
import telegram_bot


async def once_a_day(bot: telegram.Bot):
    all_users = database.get_users_by_schedule(1)
    time_scope = datetime.datetime.now() + datetime.timedelta(days=1)
    for user in all_users:
        await send_scheduled_event(bot, user, time_scope)


async def once_a_week(bot: telegram.Bot):
    all_users = database.get_users_by_schedule(2)
    time = datetime.datetime.now() + datetime.timedelta(days=7)
    for user in all_users:
        await send_scheduled_event(bot, user, time)


async def send_scheduled_event(bot: telegram.Bot, user: database.User, time_scope: datetime.datetime):
    """
    send the unfinished events by the given time scope
    :param bot:
    :param user:
    :param time_scope:
    :return:
    """
    unfinished_events = internet.Internet(user.user_name, user.password).get_unfinished_events(time_scope)
    if not unfinished_events:
        await telegram_bot.enter_data(bot, user.user_id)
        return
    unfinished_events = internet.Internet(user.user_name, user.password).get_unfinished_events(time_scope)
    if unfinished_events.warnings:
        await telegram_bot.handle_warnings(unfinished_events.warnings, bot, user.user_id)
    if unfinished_events.error:
        await telegram_bot.handle_error(unfinished_events.error, bot, user.user_id)
        return
    events = events.result
    events_text = '\n---------------------------------------------\n'.join(f'{event.name}\n'
                                                                           f'{event.course_name}\n'
                                                                           f'{event.end_time}\n'
                                                                           f'{event.url}'
                                                                           for event in unfinished_events)

    await bot.send_message(chat_id=user.user_id, text=events_text)


async def schedule_messages(bot: telegram.Bot):
    """
    schedule sending the messages and call the scheduled jobs
    :param bot:
    :return:
    """
    schedule.every().day.at("06:00").do(once_a_day, bot)
    schedule.every().sunday.at("06:00").do(once_a_week, bot)

    while True:
        schedule.run_pending()
        time.sleep(1)
