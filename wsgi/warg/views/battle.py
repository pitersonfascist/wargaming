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
    battleAcceptUser(bid, uid, True)
    #from warg.views.full_text import storeBattleInIndex
    #storeBattleInIndex(bdata, None)
    rs.sadd("whoosh:battles:added", bid)
    return bid


def process_battle_db(bid, uid, bdata, tanks):
    rs.hmset("battle:%s" % bid, {'data': json.dumps(bdata), 'id': bid, 'uid': uid, 'battle_date': bdata['battle_date'], 'type': bdata['type'], 'privacy': bdata['privacy']})
    rs.zadd("battles:%s" % bdata['type'], bid, bdata['battle_date'])
    rs.zadd("user_battles:" + str(uid), bid, bdata['battle_date'])
    rs.zadd("battles_ids", bid, bdata['battle_date'])
    rs.zadd("privacy:%s" % bdata['privacy'], bid, bdata['battle_date'])
    if tanks is not None:
        for tank_id in tanks:
            rs.sadd("tank:%s:battles" % tank_id, bid)
            rs.sadd("battle:%s:tanks" % bid, tank_id)


@api_route('/battle/<int:battle_id>/update', methods=['POST'])
def update_battle(battle_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if str(uid) != rs.hget("battle:%s" % battle_id, 'uid'):
        return -1
    try:
        data = json.loads(request.stream.read())
    except:
        return -3

    battle = json.loads(rs.hget("battle:%s" % battle_id, 'data'))
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
        rs.zrem("battles:%s" % battle_old['type'], battle_id)
    if battle_old['privacy'] != data['privacy']:
        rs.zrem("privacy:%s" % battle_old['privacy'], battle_id)

    tanks = rs.smembers("battle:%s:tanks" % battle_id)
    for tank_id in tanks:
        rs.srem("tank:%s:battles" % tank_id, battle_id)
    rs.delete("battle:%s:tanks" % battle_id)

    process_battle_db(battle_id, uid, battle, data.get("tanks", None))
    users = rs.zrange('battle:%s:users' % battle_id, 0, -1)
    for user_id in users:
        rs.zadd('user:%s:battles' % user_id, battle_id, battle['battle_date'])
    #from uhelp.views.full_text import storeLookInIndex
    #storeLookInIndex(look, None, True)
    rs.sadd("whoosh:battles:updated", battle_id)
    return battle_id


@api_route('/battle/<int:battle_id>/delete', methods=['POST'])
def delete_battle(battle_id, admin=0):
    if rs.exists("battle:%s" % battle_id) == 1 and (admin == 1 or str(loggedUserUid()) == rs.hget("battle:%s" % battle_id, 'uid')):
        uid = rs.hget("battle:%s" % battle_id, 'uid')
        rs.zrem("user_battles:" + uid, battle_id)
        rs.zrem("battles_ids", battle_id)
        battle = json.loads(rs.hget("battle:%s" % battle_id, 'data'))
        rs.zrem("battles:%s" % battle['type'], battle_id)
        rs.zrem("privacy:%s" % battle['privacy'], battle_id)
        tanks = rs.smembers("battle:%s:tanks" % battle_id)
        for tank_id in tanks:
            rs.srem("tank:%s:battles" % tank_id, battle_id)
        users = rs.zrange('battle:%s:users' % battle_id, 0, -1)
        from warg.views.battle_followers import unFollowBattleByUser
        from warg.views.notifications import create_battle_notification, NTFY_BATTLE_KICK
        for user_id in users:
            unFollowBattleByUser(battle_id, int(user_id))
            if user_id != uid:
                create_battle_notification(uid, user_id, battle_id, NTFY_BATTLE_KICK)
        rs.delete("battle:%s:tanks" % battle_id)
        rs.delete("battle:%s" % battle_id)
        rs.sadd("whoosh:battles:deleted", battle_id)
        return 1
    return 0


@requires_auth
@api_route('/system/battle/<int:battle_id>/delete', methods=['POST'])
def admin_delete_battle(battle_id):
    return delete_battle._original(battle_id, 1)


@api_route('/battle/<int:battle_id>', methods=['GET'])
def get_battle(battle_id):
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple()))).hexdigest() + "battle_" + str(battle_id)
    zscore = rs.zscore("battles_ids", battle_id)
    if zscore is not None:
        rs.zadd(tmp, battle_id, 10 * zscore)
        res = get_battles_by_set(tmp)
        rs.delete(tmp)
        return {} if len(res) == 0 else res[0]
    else:
        return {}


@api_route('/user/<int:user_id>/battles', methods=['GET'])
def get_user_battles(user_id):
    return get_battles_by_set("user_battles:%s" % user_id)


@api_route('/battles/all', methods=['GET'])
def get_privacy_all_battles():
    return get_battles_by_set("privacy:ALL")


@api_route('/user/allowed/battles', methods=['GET'])
def get_allowed_battles():
    uid = loggedUserUid()
    if uid == 0:
        return []
    lua = """local r1 = redis.call('sort', 'user:'..tostring(KEYS[2])..':followers', 'GET', 'user:*->battles');
for i = 1, table.getn(r1) do
  redis.call('zadd', KEYS[1], redis.call('hget', 'battle:'..tostring(r1[i]), 'battle_date'), r1[i]);
end
redis.call('zinterstore', KEYS[1], 2, KEYS[1], 'privacy:PRIVATE', 'AGGREGATE', 'MIN');
redis.call('zunionstore', KEYS[1], 4, KEYS[1], 'user:'..tostring(KEYS[2])..':battles','privacy:ALL', 'user_battles:'..tostring(KEYS[2]), 'AGGREGATE', 'MIN');
return 1;"""
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple()))).hexdigest() + "allowed_battle_" + str(uid)
    #rs.sort('user:%s:followers' % uid, get=["user:*->battles"], store=tmp)
    #rs.zinterstore(tmp, tmp, "privacy:PRIVATE", aggregate="MIN")
    #rs.zinterstore(tmp, tmp, 'user:%s:battles' % uid, "privacy:ALL", "user_battles:%s" % uid, aggregate="MIN")
    rs.eval(lua, 2, tmp, uid)
    res = get_battles_by_set(tmp)
    rs.delete(tmp)
    return res


@api_route('/user/followed/battles', methods=['GET'])
def get_followed_battles():
    uid = loggedUserUid()
    if uid == 0:
        return []
    return get_battles_by_set("user:%s:battles" % uid)


@api_route('/battle/<int:battle_id>/tanks', methods=['GET'], jsondump=False)
def get_battle_tanks(battle_id):
    tanks = rs.sort("battle:%s:tanks" % battle_id, get='tank:*')
    return "[" + ",".join(tanks) + "]"


def get_battles_arr_by_set(key, by2=None, offset=0, count=20):
    #start_time = time.time()
    uid = loggedUserUid()
    battles = []
    lua = """local r1 = redis.call('ZRANGEBYSCORE', KEYS[1], KEYS[2], '+inf', 'LIMIT', KEYS[4], KEYS[5]);
for i = 1, table.getn(r1) do
  local bid = r1[i];
  r1[i] = {}
  r1[i][1] = redis.call('HGET', 'battle:'..bid, 'data');
  local uid = redis.call('HGET', 'battle:'..bid, 'uid');
  r1[i][2] = redis.call('get', 'users:' .. uid);
  r1[i][3] = redis.call('sismember', 'users_online', uid);
--    r1[i+3] = redis.call('smembers', 'battle:' .. tostring(r1[i+3]) .. ':tanks')
  r1[i][4] = redis.call('sismember', 'battle:' .. bid .. ':accepted', tostring(KEYS[3]))
  r1[i][5] = redis.call('zrank', 'battle:' .. bid .. ':users', KEYS[3])
  r1[i][6] = redis.call('scard', 'battle:' .. bid .. ':accepted')
  r1[i][7] = redis.call('zcard', 'battle:' .. bid .. ':users')
end
return r1;"""
    #
    # str(by2) if by2 is not None else
    rows = rs.eval(lua, 5, key, int(calendar.timegm(datetime.utcnow().timetuple())), uid, offset, count)
    for b in rows:
        l = json.loads(b[0])
        l['user'] = json.loads(b[1])
        l['user']['is_online'] = b[2]
        l['tanks'] = []  # rows[i + 3]
        l['is_accepted'] = b[3]
        l['is_follow'] = 1 if b[4] >= 0 else 0
        l['accepted'] = b[5]
        l['followers'] = b[6]
        battles.append(l)

    #print time.time() - start_time, "seconds"
    return battles


def get_battles_by_set(key, by2=None):
    offset = request.args.get("offset", 0)
    count = min(int(request.args.get("count", 10)), 20)
    return get_battles_arr_by_set(key, by2, offset, count)
