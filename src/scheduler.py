import datetime

import schedule
import telegram
import database
import internet


async def once_a_day(bot: telegram.Bot):
    all_users = database.get_users_by_schedule(1)
    time = datetime.datetime.now() + datetime.timedelta(days=1)
    for user in all_users:
        send_scheduled_event(bot, user, time)


async def once_a_week(bot: telegram.Bot):
    all_users = database.get_users_by_schedule(2)
    time = datetime.datetime.now() + datetime.timedelta(days=7)
    for user in all_users:
        await send_scheduled_event(bot, user, time)


async def send_scheduled_event(bot: telegram.Bot, user: database.User, time: datetime.datetime):
    unfinished_events = internet.Internet(user.user_name, user.password).get_unfinished_events(time)
    events_text = '\n---------------------------------------------\n'.join(f'{event.name}\n'
                                                                           f'{event.course_name}\n'
                                                                           f'{datetime.fromtimestamp(event.end_time)}\n'
                                                                           f'{event.url}'
                                                                           for event in unfinished_events)

    await bot.send_message(chat_id=user.user_id, text=events_text)
