from warg import api_route
from flask import request
from warg.views import rs
from warg.views.users import loggedUserUid
import json
import hashlib
from datetime import datetime
from time import mktime

"""
return:
-1  user_id unavailible
-2  not logined
1 ok
"""


@api_route('/user/<int:user_id>/follow', methods=['POST', 'PUT'])
def followUser(user_id):
    if rs.exists("users:" + str(user_id)) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2
    return followUserByUser(user_id, str(uid))


@api_route('/register/<int:account_id>/follow', methods=['POST', 'PUT'])
def followExternalUser(account_id):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    access_token = request.args.get("access_token", None)
    if access_token is None:
        return json.dumps("No access token")
    wotuid = 'wot_user:%d' % account_id
    if rs.exists(wotuid) != 1:
        from warg.views.users import insert_wot_user, account_info
        data = account_info(access_token, account_id)
        if data['status'] == 'ok':
            user_id = insert_wot_user(data['data'][str(account_id)], 1)
        else:
            return json.dumps("Error: " + data['error']['message'])
    else:
        user_id = rs.hget(wotuid, 'uid')
    return followUserByUser(user_id, str(uid))


def followUserByUser(user_id, by_user_id):
    rs.sadd('user:%s:following' % by_user_id, user_id)
    rs.sadd('user:%d:followers' % user_id, by_user_id)
    rs.sunionstore('user:%s:follownig_looks' % by_user_id, 'user:%s:follownig_looks' % by_user_id, 'user_looks:' + str(user_id))

    return rs.scard('user:%d:followers' % user_id)


#('/user/<int:user_id>/follow', methods=['DELETE'])
@api_route('/user/<int:user_id>/unfollow', methods=['POST'])
def unfollowUser(user_id):
    if rs.exists("users:" + str(user_id)) != 1:
        return -1
    uid = loggedUserUid()
    if uid == 0:
        return -2

    rs.srem('user:%s:following' % uid, user_id)
    rs.srem('user:%d:followers' % user_id, uid)
    rs.sdiffstore('user:%s:follownig_looks' % uid, 'user:%s:follownig_looks' % uid, 'user_looks:' + str(user_id))

    return rs.scard('user:%d:followers' % user_id)


@api_route('/user/<int:user_id>/following', methods=['GET'], jsondump=True)
def getUserFollowing(user_id):
    if rs.exists("users:" + str(user_id)) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 20)
    rows = rs.sort('user:' + str(user_id) + ':following', start=offset, num=count, desc=True, get='users:*')
    lua = """local r1 = redis.call('sort', 'user:'..tostring(KEYS[1])..':following', 'LIMIT', KEYS[3], KEYS[4],
    'GET', 'users:*', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 3 == 1 then
    r1[i+1] = redis.call('sismember', 'user:' .. tostring(r1[i+1]) .. ':followers', KEYS[2])
    r1[i+2] = redis.call('sismember', 'users:virtual', r1[i+2])
  end
end
return r1;"""
    rows = rs.eval(lua, 4, user_id, loggedUserUid(), offset, count)
    users = []
    for i in range(0, len(rows) - 1):
        if i % 3 != 0 or rows[i] is None:
            continue
        u = json.loads(rows[i])
        u['is_follow'] = rows[i + 1]
        u['virtual'] = rows[i + 2]
        users.append(u)
    return users
    #return '[' + ','.join(rows) + ']'


@api_route('/user/<int:user_id>/followers', methods=['GET'], jsondump=True)
def getUserFollowers(user_id):
    if rs.exists("users:" + str(user_id)) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 20)
    rows = rs.sort('user:' + str(user_id) + ':followers', start=offset, num=count, desc=True, get='users:*')
    #u['is_follow'] = int(rs.sismember('user:' + str(user_id) + ':followers', loggedUserUid()))
    lua = """local r1 = redis.call('sort', 'user:'..tostring(KEYS[1])..':followers', 'LIMIT', KEYS[3], KEYS[4],
    'GET', 'users:*', 'GET', '#', 'GET', '#');
for i = 1, table.getn(r1) do
  if i % 3 == 1 then
    r1[i+1] = redis.call('sismember', 'user:' .. tostring(r1[i+1]) .. ':followers', KEYS[2])
    r1[i+2] = redis.call('sismember', 'users:virtual', r1[i+2])
  end
end
return r1;"""
    rows = rs.eval(lua, 4, user_id, loggedUserUid(), offset, count)
    users = []
    for i in range(0, len(rows) - 1):
        if i % 3 != 0 or rows[i] is None:
            continue
        u = json.loads(rows[i])
        u['is_follow'] = rows[i + 1]
        u['virtual'] = rows[i + 2]
        users.append(u)
    return users
    #return '[' + ','.join(rows) + ']'


@api_route('/user/follow/diff', methods=['POST'], jsondump=False)
def followDiff():
    uid = loggedUserUid()
    if uid == 0:
        return '-2'
    app_friends = request.stream.read()
    try:
        app_friends = json.loads(app_friends)
    except:
        return '-3'
    lua = """local app_friends = loadstring('return ' .. KEYS[1])()
for i = 1, table.getn(app_friends) do
    redis.call('sadd', KEYS[2], redis.call('hget', 'wot_user:' .. tostring(app_friends[i]), 'uid'))
end
redis.call('sunionstore', KEYS[2], KEYS[2], 'user:' .. tostring(KEYS[3]) .. ':following')
redis.call('sdiffstore', KEYS[2], KEYS[2], 'user:' .. tostring(KEYS[3]) .. ':following')
local r = redis.call('sort', KEYS[2], 'get', 'users:*')
redis.call('del', KEYS[2])
return r"""
    """
    """
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple())) + str(uid)).hexdigest() + "following_tmp"
    diff = rs.eval(lua, 3, '{' + ','.join(str(x) for x in app_friends) + '}', tmp, uid)
    return '[' + ','.join(diff) + ']'