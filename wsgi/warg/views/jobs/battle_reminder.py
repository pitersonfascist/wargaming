# -*- coding: utf-8 -*-
#from warg.views.battle import get_battle
from warg import sched
from warg.views import rs
from datetime import datetime, timedelta
import calendar
import json
from warg.views.notifications import create_battle_notification


reminders = {}
REMINDER_BTL_START = u"Напоминание: Бой %s состоится через %s"


def startup_initialize():
    battles = rs.zrangebyscore("battles_ids", int(calendar.timegm(datetime.utcnow().timetuple())), '+inf', withscores=True)
    for bid, bdate in battles:
        init_battle_reminders(bid, bdate)
    #sched.add_date_job(read_news, minute='*/10')
    #sched.unschedule_job(reminders["battle:%s:job" % 1])
    #print delta_to_left(timedelta(minutes=110))
    #sched.print_jobs()


def remove_battle_reminders(battle_id):
    remitems = rs.smembers("battle:%s:reminders" % battle_id)
    for remmin in remitems:
        key = "battle:%s:job:%s" % (battle_id, remmin)
        job = reminders.get(key)
        if job is not None:
            sched.unschedule_job(job)
            reminders[key] = None


def init_battle_reminders(battle_id, bdate):
    remitems = rs.smembers("battle:%s:reminders" % battle_id)
    for remmin in remitems:
        #remmin = int(remmin)
        delta = timedelta(minutes=int(remmin))
        date = datetime.fromtimestamp(bdate) - delta
        if int(calendar.timegm(datetime.now().timetuple())) <= int(calendar.timegm(date.timetuple())):
            print "battle", battle_id, "remind", remmin, datetime.fromtimestamp(bdate), date
            reminders["battle:%s:job:%s" % (battle_id, remmin)] = sched.add_date_job(send_battle_reminder, date, args=[battle_id, delta])


def send_battle_reminder(battle_id, delta):
    battle = json.loads(rs.hget("battle:%s" % battle_id, 'data'))
    user_id = rs.hget("battle:%s" % battle_id, 'uid')
    accepted = rs.smembers('battle:%s:accepted' % battle_id)
    for member in accepted:
        create_battle_notification(user_id, member, battle_id, REMINDER_BTL_START % (battle['descr'], delta_to_left(delta)))
    key = "battle:%s:job:%s" % (battle_id, delta)
    reminders[key] = None


def delta_to_left(delta):
    days, hours, minutes = delta.days, delta.seconds // 3600, delta.seconds % 3600 / 60
    msg = u"%s мин" % minutes
    if hours > 0:
        msg = u"%s ч %s" % (hours, msg)
    if days > 0:
        msg = u"%s д %s" % (days, msg)
    return msg