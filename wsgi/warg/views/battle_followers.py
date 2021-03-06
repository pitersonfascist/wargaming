# -*- coding: utf-8 -*-
from warg import api_route
from flask import request
from warg.views import rs
import json
from warg.views.users import loggedUserUid
from warg.views.notifications import *
"""
return:
-1  battle_id unavailible
-2  not logined
1 ok
"""


@api_route('/battle/<int:battle_id>/follow', methods=['POST', 'PUT'])
def battleFollowUser(battle_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if rs.sismember('battle:%s:invited' % battle_id, uid):
        create_battle_notification(uid, 0, battle_id, NTFY_INVITE_ACCEPT)
        rs.srem('battle:%s:invited' % battle_id, uid)
        rs.zadd('battle:%s:users' % battle_id, uid, 1)
        rs.sadd('battle:%s:accepted' % battle_id, uid)
        rs.zadd('user:%s:battles' % uid, battle_id, rs.zscore("battles_ids", battle_id))
        return 1
    else:
        create_battle_notification(uid, 0, battle_id, NTFY_BATTLE_FOLLOW)
        return followBattleByUser(battle_id, uid)


@api_route('/battle/<int:battle_id>/follow/<int:user_id>', methods=['POST', 'PUT'])
def battleAddUser(battle_id, user_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    if rs.hget("battle:%s" % battle_id, "uid") != str(loggedUserUid()):
        return -2
    rs.sadd('battle:%s:invited' % battle_id, user_id)
    create_battle_notification(loggedUserUid(), user_id, battle_id, NTFY_BATTLE_INVITE)
    return followBattleByUser(battle_id, user_id)


@api_route('/battle/<int:battle_id>/register/<int:account_id>', methods=['POST', 'PUT'])
def battleAddExternalUser(battle_id, account_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    if rs.hget("battle:%s" % battle_id, "uid") != str(loggedUserUid()):
        return -2
    access_token = request.args.get("access_token", None)
    if access_token is None:
        return json.dumps("No access token")
    wotuid = 'wot_user:%s' % account_id
    if rs.exists(wotuid) != 1:
        from warg.views.users import insert_wot_user, account_info
        data = account_info(access_token, account_id)
        if data['status'] == 'ok':
            uid = insert_wot_user(data['data'][str(account_id)], 1)
        else:
            return json.dumps("Error: " + data['error']['message'])
    else:
        uid = rs.hget(wotuid, 'uid')
    create_battle_notification(loggedUserUid(), int(uid), battle_id, NTFY_BATTLE_INVITE)
    rs.sadd('battle:%s:invited' % battle_id, uid)
    return followBattleByUser(battle_id, uid)


@api_route('/battle/<int:battle_id>/accept/<int:user_id>', methods=['POST', 'PUT'])
def battleAcceptUser(battle_id, user_id, admin=False):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if rs.hget("battle:%s" % battle_id, "uid") != str(uid) and not admin:
        return -2
    rs.zadd('battle:%s:users' % battle_id, user_id, 1)
    rs.sadd('battle:%s:accepted' % battle_id, user_id)
    rs.zadd('user:%s:battles' % user_id, battle_id, rs.zscore("battles_ids", battle_id))
    if uid != user_id:
        create_battle_notification(loggedUserUid(), user_id, battle_id, NTFY_BATTLE_ACCEPT)
    return rs.scard('battle:%s:accepted' % battle_id)


def followBattleByUser(battle_id, by_user_id):
    rs.zadd('battle:%s:users' % battle_id, by_user_id, 0)
    rs.zadd('user:%s:battles' % by_user_id, battle_id, rs.zscore("battles_ids", battle_id))
    return rs.zcard('battle:%s:users' % battle_id)


@api_route('/battle/<int:battle_id>/unfollow', methods=['POST'])
def unfollowBattle(battle_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if rs.hget("battle:%s" % battle_id, "uid") == str(uid):
        return -3
    if rs.sismember('battle:%s:invited' % battle_id, uid):
        create_battle_notification(uid, 0, battle_id, NTFY_INVITE_REJECT)
    else:
        create_battle_notification(uid, 0, battle_id, NTFY_BATTLE_UFLLOW)
    return unFollowBattleByUser(battle_id, uid)


@api_route('/battle/<int:battle_id>/unfollow/<int:user_id>', methods=['POST', 'PUT'])
def battleDelUser(battle_id, user_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if rs.hget("battle:%s" % battle_id, "uid") != str(uid):
        return -2
    create_battle_notification(uid, user_id, battle_id, NTFY_BATTLE_KICK)
    return unFollowBattleByUser(battle_id, user_id)


@api_route('/battle/<int:battle_id>/reject/<int:user_id>', methods=['POST', 'PUT'])
def battleRejectUser(battle_id, user_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if rs.hget("battle:%s" % battle_id, "uid") != str(uid):
        return -2
    if uid == user_id:
        return -3
    rs.zadd('battle:%s:users' % battle_id, user_id, 0)
    rs.srem('battle:%s:accepted' % battle_id, user_id)
    create_battle_notification(uid, user_id, battle_id, NTFY_BATTLE_REJECT)
    return rs.scard('battle:%s:accepted' % battle_id)


def unFollowBattleByUser(battle_id, by_user_id):
    rs.zrem('battle:%s:users' % battle_id, by_user_id)
    rs.zrem('user:%s:battles' % by_user_id, battle_id)
    rs.srem('battle:%s:accepted' % battle_id, by_user_id)
    rs.srem('battle:%s:invited' % battle_id, by_user_id)
    return rs.zcard('battle:%s:users' % battle_id)


@api_route('/battle/<int:battle_id>/followers', methods=['GET'], jsondump=True)
def getBattleFollowers(battle_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 20)
    #rows = rs.sort('battle:' + str(battle_id) + ':users', start=offset, num=count, desc=True, get='users:*')
    lua = """local r1 = redis.call('sort', 'battle:'..tostring(KEYS[1])..':users', 'BY', 'score','DESC', 'LIMIT', KEYS[3], KEYS[4],
    'GET', 'users:*', 'GET', '#', 'GET', '#', 'GET', '#', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 6 == 1 then
    r1[i+1] = redis.call('sismember', 'user:' .. tostring(r1[i+1]) .. ':followers', KEYS[2])
    r1[i+2] = redis.call('sismember', 'battle:' .. tostring(KEYS[1]) .. ':accepted', r1[i+3])
    r1[i+3] = redis.call('sismember', 'users:virtual', r1[i+3])
    r1[i+4] = redis.call('sismember', 'users_online', r1[i+4])
    r1[i+5] = redis.call('sismember', 'battle:' .. tostring(KEYS[1]) .. ':invited', r1[i+5])
  end
end
return r1;"""
    rows = rs.eval(lua, 4, battle_id, loggedUserUid(), offset, count)
    users = []
    for i in range(0, len(rows) - 1):
        if i % 6 != 0 or rows[i] is None:
            continue
        u = json.loads(rows[i])
        u['is_follow'] = rows[i + 1]
        u['is_accepted'] = rows[i + 2]
        u['is_online'] = rows[i + 4]
        u['virtual'] = rows[i + 3]
        u['is_invited'] = rows[i + 5]
        users.append(u)
    return users


@api_route('/battle/<int:battle_id>/unread')
def get_battle_unread(battle_id):
    if rs.exists("battle:" + str(battle_id)) != 1:
        return -1
    uid = loggedUserUid()
    if rs.hget("battle:%s" % battle_id, "uid") != str(uid):
        return -2
    if rs.exists("battle:%s:unread" % battle_id) != 1:
        return []
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 10))
    rows = []
    lua = """local r1 = redis.call('ZREVRANGE', KEYS[1], KEYS[2], KEYS[3]);
for i = 1, table.getn(r1) do
  local chid = r1[i]
  r1[i] = {}
  r1[i][1] = redis.call('hget', chid, 'id')
  r1[i][2] = redis.call('hget', chid, 'text')
  r1[i][3] = redis.call('zscore', KEYS[1], chid)
  local uid = redis.call('hget', chid, 'rid')
  r1[i][4] = redis.call('get', 'users:' .. tostring(uid))
  r1[i][5] = redis.call('sismember', 'users_online', uid)
end
return r1;"""
    ids = rs.eval(lua, 3, "battle:%s:unread" % battle_id, offset, offset + count - 1)
    for cmid in ids:
        cmnt = {'id': int(cmid[0]), 'text': cmid[1], 'create_date': int(cmid[2])}
        cmnt['user'] = json.loads(cmid[3])
        cmnt['user']['is_online'] = cmid[4]
        rows.append(cmnt)
    return rows