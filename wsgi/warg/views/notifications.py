# -*- coding: utf-8 -*-
from warg.views.battle import get_battle
from warg.views.users import detail as user_datail
from warg.views.chat import send_message_to_user, get_user_unread
from datetime import datetime
import calendar
import pytz
from warg.views import rs
import json


NTFY_BATTLE_INVITE = u"%s пригласил Вас в бой %s %s"
NTFY_BATTLE_FOLLOW = u"%s подал заявку на бой %s %s"
NTFY_BATTLE_UFLLOW = u"%s отозвал заявку на бой %s %s"
NTFY_BATTLE_KICK   = u"%s отменил Ваше участие в бою %s %s"
NTFY_BATTLE_ACCEPT = u"Заявка принята. %s %s"
NTFY_BATTLE_REJECT = u"Заявка не принята. %s %s"
NTFY_INVITE_ACCEPT = u"%s готов к бою %s %s"
NTFY_INVITE_REJECT = u"%s отказался от боя %s %s"
#NTFY_USER_FOLLOW   = u"%s добавил Вас в избранное"


def create_battle_notification(from_user, to_user, battle_id, template):
    battle = get_battle._original(battle_id)
    to_user = battle['user']["id"] if int(to_user) == 0 else to_user
    #timedelta = int(rs.get('user:%s:timedelta' % to_user) or 0)
    #zonedelta = int(rs.get('user:%s:zonedelta' % to_user) or 0)
    battle_date = datetime.fromtimestamp(int(battle["battle_date"]), tz=pytz.utc).strftime('UTC %H:%M %d/%m')
    message = None
    if template == NTFY_BATTLE_INVITE:
        message = NTFY_BATTLE_INVITE % (battle['user']['nickname'], battle_date, battle["descr"])
    if template == NTFY_BATTLE_FOLLOW:
        usr = user_datail._original(from_user)
        to_user = battle['user']["id"]
        message = NTFY_BATTLE_FOLLOW % (usr["nickname"], battle_date, battle["descr"])
    if template == NTFY_BATTLE_UFLLOW:
        usr = user_datail._original(from_user)
        to_user = battle['user']["id"]
        message = NTFY_BATTLE_UFLLOW % (usr["nickname"], battle_date, battle["descr"])
    if template == NTFY_BATTLE_KICK:
        message = NTFY_BATTLE_KICK % (battle['user']['nickname'], battle_date, battle["descr"])
    if template == NTFY_BATTLE_ACCEPT:
        message = NTFY_BATTLE_ACCEPT % (battle_date, battle["descr"])
    if template == NTFY_BATTLE_REJECT:
        message = NTFY_BATTLE_REJECT % (battle_date, battle["descr"])
    if template == NTFY_INVITE_ACCEPT:
        usr = user_datail._original(from_user)
        to_user = battle['user']["id"]
        message = NTFY_INVITE_ACCEPT % (usr["nickname"], battle_date, battle["descr"])
    if template == NTFY_INVITE_REJECT:
        usr = user_datail._original(from_user)
        to_user = battle['user']["id"]
        message = NTFY_INVITE_REJECT % (usr["nickname"], battle_date, battle["descr"])
    if message is None:
        message = template
    if rs.sismember("users:virtual", to_user):
        return
    chid = "chat:message:%s:%s:" % (from_user, to_user)
    mid = rs.incr(chid + "counter")
    chid = chid + str(mid)
    score = calendar.timegm(datetime.utcnow().timetuple())
    chatm = {"id": mid, "text": message, 'is_read': 'false', 'sid': from_user, 'rid': to_user, "type": "battle", "battle_id": battle_id}
    rs.hmset(chid, chatm)
    rs.zadd("chat:user:%s:unread" % to_user, chid, score)
    rs.sadd("chat:user:%s:ntfy" % to_user, chid)
    rs.zadd("battle:%s:unread" % battle_id, chid, score)
    ucount = rs.zcard("chat:user:%s:unread" % to_user)
    unread = get_user_unread(to_user)
    if len(unread) > 0:
        unread_message = json.dumps({"type": "unread", "content": {"count": ucount, "message": unread[0]}})
        send_message_to_user(to_user, unread_message)