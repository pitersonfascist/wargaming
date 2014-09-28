# -*- coding: utf-8 -*-
from warg import api_route, requires_auth
from flask import request
from warg.views import rs
import json
from warg.views.users import loggedUserUid
import hashlib
from datetime import datetime
import calendar
from time import mktime

battle_types = ["platoon", "team", "absolute", "champion", "middle", "junior", "training", "strongholds", "clan_wars"]

battle_model = {'type', 'descr', 'battle_date', 'privacy'}

privacy = ["PRIVATE", "FOLLOWING", "ALL"]


@api_route('/battle', methods=['POST'])
def create_battle():
    uid = loggedUserUid()
    if uid == 0:
        return -2
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    bdata = {}
    fulldata = True
    for k in battle_model:
        if data.get(k, None) is None:
            fulldata = False
            break
        else:
            bdata[k] = data[k]
    if not fulldata:
        return "Few data"
    if data['type'] not in battle_types:
        return "Wrong battle type"
    bid = rs.incr('battle_counter')
    bdata['id'] = bid
    bdata['create_date'] = int(calendar.timegm(datetime.utcnow().timetuple()))
    process_battle_db(bid, uid, bdata, data.get("tanks", None))
    from warg.views.battle_followers import battleAcceptUser
    battleAcceptUser(bid, uid)
    #from warg.views.full_text import storeBattleInIndex
    #storeBattleInIndex(bdata, None)
    rs.sadd("whoosh:battles:added", bid)
    return bid


def process_battle_db(bid, uid, bdata, tanks):
    rs.hmset("battle:%d" % bid, {'data': json.dumps(bdata), 'id': bid, 'uid': uid, 'battle_date': bdata['battle_date'], 'type': bdata['type'], 'privacy': bdata['privacy']})
    rs.sadd("battles:%s" % bdata['type'], bid)
    rs.sadd("user_battles:" + str(uid), bid)
    rs.sadd("battles_ids", bid)
    rs.sadd("privacy:%s" % bdata['privacy'], bid)
    if tanks is not None:
        for tank_id in tanks:
            rs.sadd("tank:%d:battles" % tank_id, bid)
            rs.sadd("battle:%d:tanks" % bid, tank_id)


@api_route('/battle/<int:battle_id>/update', methods=['POST'])
def update_battle(battle_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if uid != rs.hget("battle:%d" % battle_id, 'uid'):
        return -1
    try:
        data = json.loads(request.stream.read())
    except:
        return -3

    battle = json.loads(rs.hget("battle:%d" % battle_id, 'data'))
    battle_old = battle.copy()

    fulldata = True
    for k in battle_model:
        if data.get(k, None) is None:
            fulldata = False
            break
        else:
            battle[k] = data[k]
    if not fulldata:
        return "Few data"
    if data['type'] not in battle_types:
        return "Wrong battle type"

    if battle_old['type'] != data['type']:
        rs.srem("battles:%s" % battle_old['type'], battle_id)
    if battle_old['privacy'] != data['privacy']:
        rs.srem("privacy:%s" % battle_old['privacy'], battle_id)

    tanks = rs.smembers("battle:%d:tanks" % battle_id)
    for tank_id in tanks:
        rs.srem("tank:%s:battles" % tank_id, battle_id)
    rs.delete("battle:%d:tanks" % battle_id)

    process_battle_db(battle_id, uid, battle, data.get("tanks", None))
    #from uhelp.views.full_text import storeLookInIndex
    #storeLookInIndex(look, None, True)
    rs.sadd("whoosh:battles:updated", battle_id)
    return battle_id


@api_route('/battle/<int:battle_id>/delete', methods=['POST'])
def delete_battle(battle_id, admin=0):
    if rs.exists("battle:%d" % battle_id) == 1 and (admin == 1 or str(loggedUserUid()) == rs.hget("battle:%d" % battle_id, 'uid')):
        uid = rs.hget("battle:%d" % battle_id, 'uid')
        rs.srem("user_battles:" + uid, battle_id)
        rs.sadd("battles_ids", battle_id)
        battle = json.loads(rs.hget("battle:%d" % battle_id, 'data'))
        rs.srem("battles:%s" % battle['type'], battle_id)
        rs.srem("privacy:%s" % battle['privacy'], battle_id)
        tanks = rs.smembers("battle:%d:tanks" % battle_id)
        for tank_id in tanks:
            rs.srem("tank:%s:battles" % tank_id, battle_id)
        rs.delete("battle:%d:tanks" % battle_id)
        rs.delete("battle:%d" % battle_id)
        rs.sadd("whoosh:battles:deleted", battle_id)
        return 1
    return 0


@requires_auth
@api_route('/system/battle/<int:battle_id>/delete', methods=['POST'])
def admin_delete_look(battle_id):
    return delete_battle._original(battle_id, 1)


@api_route('/battle/<int:battle_id>', methods=['GET'])
def get_battle(battle_id):
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple()))).hexdigest() + "battle_" + str(battle_id)
    rs.sadd(tmp, battle_id)
    res = get_battles_by_set(tmp)
    rs.delete(tmp)
    return {} if len(res) == 0 else res[0]


@api_route('/user/<int:user_id>/battles', methods=['GET'])
def get_user_battles(user_id):
    return get_battles_by_set("user_battles:%d" % user_id)


@api_route('/battles/all', methods=['GET'])
def get_privacy_all_battles():
    return get_battles_by_set("privacy:all")


@api_route('/user/allowed/battles', methods=['GET'])
def get_allowed_battles():
    uid = loggedUserUid()
    if uid == 0:
        return []
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple()))).hexdigest() + "allowed_battle_" + str(uid)
    rs.sort('user:%d:followers' % uid, get=["user:*->battles"], store=tmp)
    rs.sinterstore(tmp, tmp, "privacy:private")
    rs.sunionstore(tmp, tmp, 'user:%d:battles' % uid, "privacy:all", "user_battles:%d" % uid)
    res = get_battles_by_set(tmp)
    rs.delete(tmp)
    return res


@api_route('/user/followed/battles', methods=['GET'])
def get_followed_battles():
    uid = loggedUserUid()
    if uid == 0:
        return []
    return get_battles_by_set("user:%d:battles" % uid)


@api_route('/battle/<int:battle_id>/tanks', methods=['GET'], jsondump=False)
def get_battle_tanks(battle_id):
    tanks = rs.sort("battle:%d:tanks" % battle_id, get='tank:*')
    return "[" + ",".join(tanks) + "]"


def get_battles_arr_by_set(key, by2=None, offset=0, count=20):
    #start_time = time.time()
    uid = loggedUserUid()
    battles = []
    lua = """local r1 = redis.call('sort', KEYS[1], 'BY', KEYS[2], 'DESC', 'LIMIT', KEYS[4], KEYS[5],
    'GET', 'battle:*->data',
    'GET', 'battle:*->uid', 'GET', '#', 'GET', '#', 'GET', '#', 'GET', '#', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 8 == 1 then
    r1[i+2] = redis.call('get', 'users:' .. tostring(r1[i+1]))
    r1[i+1] = redis.call('sismember', 'users_online', tostring(r1[i+1]))
--    r1[i+3] = redis.call('smembers', 'battle:' .. tostring(r1[i+3]) .. ':tanks')
    r1[i+4] = redis.call('sismember', 'battle:' .. tostring(r1[i+4]) .. ':accepted', tostring(KEYS[3]))
    r1[i+5] = redis.call('zrank', 'battle:' .. tostring(r1[i+5]) .. ':users', KEYS[3])
    r1[i+6] = redis.call('scard', 'battle:' .. tostring(r1[i+6]) .. ':accepted')
    r1[i+7] = redis.call('zcard', 'battle:' .. tostring(r1[i+7]) .. ':users')
  end
end
return r1;"""
    #
    # str(by2) if by2 is not None else
    rows = rs.eval(lua, 5, key, "battle:*->battle_date", uid, offset, count)
    for i in range(0, len(rows) - 1):
        if i % 8 != 0 or rows[i] is None:
            continue
        l = json.loads(rows[i])
        l['user'] = json.loads(rows[i + 2])
        l['user']['is_online'] = rows[i + 1]
        l['tanks'] = []  # rows[i + 3]
        l['is_accepted'] = rows[i + 4]
        l['is_follow'] = 1 if rows[i + 5] else 0
        l['accepted'] = rows[i + 6]
        l['followers'] = rows[i + 7]
        battles.append(l)

    #print time.time() - start_time, "seconds"
    return battles


def get_battles_by_set(key, by2=None):
    offset = request.args.get("offset", 0)
    count = min(int(request.args.get("count", 10)), 20)
    return get_battles_arr_by_set(key, by2, offset, count)
