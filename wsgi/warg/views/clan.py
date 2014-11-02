# -*- coding: utf-8 -*-
from warg import api_route
from flask import request
from warg.views import rs
import json
from warg.views.users import loggedUserUid


clan_model = {'name', 'abbreviation', 'clan_id'}


@api_route('/clan', methods=['POST'])
def create_clan():
    uid = loggedUserUid()
    if uid == 0:
        return -2
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    gdata = {}
    fulldata = True
    for k in clan_model:
        if data.get(k, None) is None:
            fulldata = False
            break
        else:
            gdata[k] = data[k]
    if not fulldata:
        return "Few data"
    user_clan_id = rs.get("user:%s:clan" % uid)
    if user_clan_id == str(data["clan_id"]):
        return data["clan_id"]
    if int(user_clan_id or 0) > 0:
        clan_del_user(user_clan_id, uid)
    rs.hmset("clan:%s" % data["clan_id"], {'data': json.dumps(data), 'id': data["clan_id"]})
    clan_add_user(data["clan_id"], uid)
    return data["clan_id"]


def clan_add_user(clan_id, user_id):
    rs.sadd("clan:%s:users" % clan_id, user_id)
    rs.set("user:%s:clan" % user_id, clan_id)
    user_cnt = rs.scard('clan:%s:users' % clan_id)
    rs.zadd("clan_ids", clan_id, user_cnt)
    return user_cnt


def clan_del_user(clan_id, user_id):
    rs.srem("clan:%s:users" % clan_id, user_id)
    rs.delete("user:%s:clan" % user_id)
    user_cnt = rs.scard('clan:%s:users' % clan_id)
    rs.zadd("clan_ids", clan_id, user_cnt)
    return user_cnt


@api_route('/clan/<int:clan_id>/users', methods=['GET'])
def get_clan_users(clan_id):
    if rs.exists("clan:%s" % clan_id) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 20)
    lua = """local r1 = redis.call('sort', 'clan:'..tostring(KEYS[1])..':users', 'DESC', 'LIMIT', KEYS[3], KEYS[4],
    'GET', 'users:*', 'GET', '#', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 4 == 1 then
    r1[i+1] = redis.call('sismember', 'user:' .. tostring(r1[i+1]) .. ':followers', KEYS[2])
    r1[i+2] = redis.call('sismember', 'users:virtual', r1[i+2])
    r1[i+3] = redis.call('sismember', 'users_online', r1[i+3])
  end
end
return r1;"""
    rows = rs.eval(lua, 4, clan_id, loggedUserUid(), offset, count)
    users = []
    for i in range(0, len(rows) - 1):
        print i, rows[i]
        if i % 4 != 0 or rows[i] is None:
            continue
        u = json.loads(rows[i])
        u['is_follow'] = rows[i + 1]
        u['is_online'] = rows[i + 3]
        u['virtual'] = rows[i + 2]
        users.append(u)
    return users


#CLAN BATTLES
@api_route('/clan/<int:clan_id>/battle', methods=['POST'])
def create_clan_battle(clan_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if rs.sismember("clan:%s:users" % clan_id, uid) == 0:
        return -1
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    data["privacy"] = "PRIVATE"
    from warg.views.battle import do_create_battle
    battle_id = do_create_battle(uid, data)
    if int(battle_id) > 0:
        zscore = rs.zscore("battles_ids", battle_id)
        rs.zadd("clan:%s:battles" % clan_id, battle_id, zscore)
    return battle_id


@api_route('/clan/<int:clan_id>/battles', methods=['GET'])
def get_clan_battles(clan_id):
    uid = loggedUserUid()
    if uid == 0:
        return []
    if rs.sismember("clan:%s:users" % clan_id, uid) == 0:
        return []
    from warg.views.battle import get_battles_by_set
    return get_battles_by_set("clan:%s:battles" % clan_id)