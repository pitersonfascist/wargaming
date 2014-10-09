# -*- coding: utf-8 -*-
from warg.views.battle import get_battle
from warg import sched
from warg.views import rs
from datetime import datetime, timedelta
import calendar
from warg.views.notifications import create_battle_notification


reminders = {}
REMINDER_BTL_START = u"Напоминание: Бой %s состоится через %s"


def startup_initialize():
    battles = rs.zrangebyscore("battles_ids", int(calendar.timegm(datetime.utcnow().timetuple())), '+inf', withscores=True)
    for bid, bdate in battles:
        print bid, datetime.fromtimestamp(bdate)
        delta = timedelta(minutes=1)
        print "delta", delta
        reminders["battle:%s:job" % bid] = sched.add_date_job(send_battle_reminder, datetime.now() + delta, args=[bid, delta])
    #sched.add_date_job(read_news, minute='*/10')
    #sched.unschedule_job(reminders["battle:%s:job" % 1])
    print delta_to_left(timedelta(minutes=110))
    sched.print_jobs()


def send_battle_reminder(battle_id, delta):
    battle = get_battle._original(battle_id)
    accepted = rs.smembers('battle:%s:accepted' % battle_id)
    for member in accepted:
        create_battle_notification(battle['user']["id"], member, REMINDER_BTL_START % (battle['descr'], delta_to_left(delta)))


def delta_to_left(delta):
    days, hours, minutes = delta.days, delta.seconds // 3600, delta.seconds % 3600 / 60
    msg = u"%s мин" % minutes
    if hours > 0:
        msg = u"%s ч %s" % (hours, msg)
    if days > 0:
        msg = u"%s д %s" % (days, msg)
    return msg