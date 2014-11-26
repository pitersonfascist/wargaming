# -*- coding: utf-8 -*-
from warg import api_route, requires_auth
from flask import request
from warg.views import rs
import json
from datetime import datetime
import calendar
import hashlib
from time import mktime
from warg.views.users import loggedUserUid


group_model = {'name', 'descr'}


@api_route('/group', methods=['POST'])
def create_group():
    uid = loggedUserUid()
    if uid == 0:
        return -2
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    gdata = {}
    fulldata = True
    for k in group_model:
        if data.get(k, None) is None:
            fulldata = False
            break
        else:
            gdata[k] = data[k]
    if not fulldata:
        return "Few data"
    gid = rs.incr('group_counter')
    gdata['id'] = gid
    gdata['create_date'] = int(calendar.timegm(datetime.utcnow().timetuple()))
    rs.hmset("group:%s" % gid, {'data': json.dumps(gdata), 'id': gid, 'uid': uid})
    group_add_user(gid, uid)
    rs.sadd("whoosh:groups:added", gid)
    return gid


@api_route('/group/<int:group_id>/update', methods=['POST'])
def update_group(group_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if str(uid) != rs.hget("group:%s" % group_id, 'uid'):
        return -1
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    group = json.loads(rs.hget("group:%s" % group_id, 'data'))
    for k in group_model:
        group[k] = data[k]
    rs.hset("group:%s" % group_id, "data", json.dumps(group))
    rs.sadd("whoosh:groups:updated", group_id)
    return group_id


@api_route('/group/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id, admin=0):
    if rs.exists("group:%s" % group_id) == 1 and (admin == 1 or str(loggedUserUid()) == rs.hget("group:%s" % group_id, 'uid')):
        users = rs.smembers("group:%s:users" % group_id)
        for user_id in users:
            rs.srem("user:%s:groups" % user_id, group_id)
        rs.delete("group:%s:users" % group_id)
        rs.delete("group:%s" % group_id)
        return 1
    else:
        return 0


@requires_auth
@api_route('/system/group/<int:group_id>/delete', methods=['POST'])
def admin_delete_group(group_id):
    return delete_group._original(group_id, 1)


def get_groups_arr_by_set(key, offset=0, count=20):
    uid = loggedUserUid()
    groups = []
    lua = """local r1 = redis.call('ZREVRANGEBYSCORE', KEYS[1], '+inf', '-inf', 'LIMIT', KEYS[3], KEYS[4]);
for i = 1, table.getn(r1) do
  local gid = r1[i];
  r1[i] = {}
  r1[i][1] = redis.call('HGET', 'group:'..gid, 'data');
  local uid = redis.call('HGET', 'group:'..gid, 'uid');
  r1[i][2] = redis.call('get', 'users:' .. uid);
  r1[i][3] = redis.call('sismember', 'users_online', uid);
  r1[i][4] = redis.call('sismember', 'group:' .. gid .. ':users', KEYS[2])
  r1[i][5] = redis.call('scard', 'group:' .. gid .. ':users')
end
return r1;"""
    rows = rs.eval(lua, 4, key, uid, offset, count)
    for b in rows:
        l = json.loads(b[0])
        l['user'] = json.loads(b[1])
        l['user']['is_online'] = b[2]
        l['is_follow'] = b[3]
        l['followers'] = b[4]
        groups.append(l)
    return groups


def get_groups_by_set(key):
    offset = request.args.get("offset", 0)
    count = min(int(request.args.get("count", 10)), 20)
    return get_groups_arr_by_set(key, offset, count)


@api_route('/group/<int:group_id>', methods=['GET'])
def get_group(group_id):
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple()))).hexdigest() + "group_" + str(group_id)
    zscore = rs.zscore("group_ids", group_id)
    if zscore is not None:
        rs.zadd(tmp, group_id, zscore)
        res = get_groups_arr_by_set(tmp, 0, 1)
        rs.delete(tmp)
        return {} if len(res) == 0 else res[0]
    else:
        rs.delete(tmp)
        return {}


@api_route('/user/<int:user_id>/groups', methods=['GET'])
def get_user_groups(user_id):
    return get_groups_by_set("user:%s:groups" % user_id)


@api_route('/groups/all', methods=['GET'])
def get_all_groups():
    return get_groups_by_set("group_ids")


#  GROUP FOLLOWERS
@api_route('/group/<int:group_id>/follow', methods=['POST'])
def group_follow(group_id):
    if rs.exists("group:%s" % group_id) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2
    return group_add_user(group_id, uid)


def group_add_user(group_id, user_id):
    rs.sadd("group:%s:users" % group_id, user_id)
    rs.zadd("user:%s:groups" % user_id, group_id, rs.zcard("user:%s:groups" % user_id) + 1)
    user_cnt = rs.scard('group:%s:users' % group_id)
    rs.zadd("group_ids", group_id, user_cnt)
    return user_cnt


def group_del_user(group_id, user_id):
    rs.srem("group:%s:users" % group_id, user_id)
    rs.zrem("user:%s:groups" % user_id, group_id)
    user_cnt = rs.scard('group:%s:users' % group_id)
    rs.zadd("group_ids", group_id, user_cnt)
    return user_cnt


@api_route('/group/<int:group_id>/unfollow', methods=['POST'])
def group_unfollow(group_id):
    if rs.exists("group:%s" % group_id) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2
    #user can't leave own group
    if rs.hget("group:%s" % group_id, "uid") == str(uid):
        return -3
    return group_del_user(group_id, uid)


@api_route('/group/<int:group_id>/users', methods=['GET'])
def get_group_users(group_id):
    if rs.exists("group:%s" % group_id) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 20)
    lua = """local r1 = redis.call('sort', 'group:'..tostring(KEYS[1])..':users', 'DESC', 'LIMIT', KEYS[3], KEYS[4],
    'GET', 'users:*', 'GET', '#', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 4 == 1 then
    r1[i+1] = redis.call('sismember', 'user:' .. tostring(r1[i+1]) .. ':followers', KEYS[2])
    r1[i+2] = redis.call('sismember', 'users:virtual', r1[i+2])
    r1[i+3] = redis.call('sismember', 'users_online', r1[i+3])
  end
end
return r1;"""
    rows = rs.eval(lua, 4, group_id, loggedUserUid(), offset, count)
    users = []
    for i in range(0, len(rows) - 1):
        if i % 4 != 0 or rows[i] is None:
            continue
        u = json.loads(rows[i])
        u['is_follow'] = rows[i + 1]
        u['is_online'] = rows[i + 3]
        u['virtual'] = rows[i + 2]
        users.append(u)
    return users


#GROUP BATTLES
@api_route('/group/<int:group_id>/battle', methods=['POST'])
def create_group_battle(group_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if rs.sismember("group:%s:users" % group_id, uid) == 0:
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
        rs.zadd("group:%s:battles" % group_id, battle_id, zscore)
    return battle_id


@api_route('/group/<int:group_id>/battles', methods=['GET'])
def get_group_battles(group_id):
    uid = loggedUserUid()
    if uid == 0:
        return []
    if rs.sismember("group:%s:users" % group_id, uid) == 0:
        return []
    from warg.views.battle import get_battles_by_set
    return get_battles_by_set("group:%s:battles" % group_id)