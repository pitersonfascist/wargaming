# -*- coding: utf-8 -*-
from warg.views.battle import get_battle
from warg.views.users import detail as user_datail
from warg.views.chat import send_message_to_user, get_unread
from datetime import datetime
import calendar
from warg.views import rs
import json


NTFY_BATTLE_INVITE = u"%s пригласил Вас в бой %s %s"
NTFY_BATTLE_FOLLOW = u"%s подал заявку на бой %s %s"
NTFY_BATTLE_UFLLOW = u"%s отозвал заявку на бой %s %s"
NTFY_BATTLE_KICK   = u"%s отменил Ваше участие в бою %s %s"
NTFY_BATTLE_ACCEPT = u"Заявка принята. %s %s"
NTFY_BATTLE_REJECT = u"Заявка не принята. %s %s"
#NTFY_USER_FOLLOW   = u"%s добавил Вас в избранное"


def create_battle_notification(from_user, to_user, battle_id, template):
    battle = get_battle._original(battle_id)
    battle_date = datetime.fromtimestamp(int(battle["battle_date"])).strftime('%H:%M %d/%m')
    message = ""
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
    if rs.sismember("users:virtual", to_user):
        return
    chid = "chat:message:%s:%s:" % (from_user, to_user)
    mid = rs.incr(chid + "counter")
    chid = chid + str(mid)
    score = calendar.timegm(datetime.utcnow().timetuple())
    chatm = {"id": mid, "text": message, 'is_read': False, 'sid': from_user, 'rid': to_user, "type": "battle", "battle_id": battle_id}
    rs.hmset(chid, chatm)
    rs.zadd("chat:user:%s:unread" % to_user, chid, score)
    rs.zadd("battle:%s:unread" % battle_id, chid, score)
    unread = get_unread._original()
    if len(unread) > 0:
        unread_message = json.dumps({"type": "unread", "content": {"count": len(unread), "message": unread[0]}})
        send_message_to_user(to_user, unread_message)