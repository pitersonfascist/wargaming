# -*- coding: utf-8 -*-
from warg import api_route, app
from flask import request, render_template
from warg.views import rs
from warg.views.users import loggedUserUid
import json
from datetime import datetime
import calendar
import traceback

participants = {}


@app.route('/chat/index')
def chat_index():
    return render_template('chat.html')


@api_route('/chat/websocket/policy', jsondump=False)
def websocket_policyfile():
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        f1 = open(app.config['STATIC_FOLDER'] + "crossdomain.xml")
        policyfile = f1.read()
        f1.close()
        ws.send(policyfile)
        ws.close()
    return "OK"


@api_route('/chat/websocket')
def websocket_api():
    uid = loggedUserUid()
    if uid == 0:
        return "Not authorized"
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        print "New user ", uid, "joined"
        if participants.get(str(uid)) is None:
            participants[str(uid)] = set()
        participants[str(uid)].add(ws)
        participants[str(uid)].add(ws)
        rs.sadd("users_online", uid)
        notify_online_status(uid, True)
        unread = get_unread._original()
        if len(unread) > 0:
            ws.send(json.dumps({"type": "unread", "content": {"count": len(unread), "message": unread[0]}}))
        while True:
            try:
                message = ws.receive()
                if message is None:
                    break
                try:
                    #message = re.escape(message)
                    #message = message.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                    #print ":>", message
                    f1 = open(app.config['UPLOAD_FOLDER'] + "chat_log.txt", "a")
                    f1.write(message)  # .encode('utf-8')
                    f1.close()
                    evt = json.loads(message)  # .encode('utf-8')
                    #print "type =", evt.get("type")
                    if evt.get("type") == "chat":
                        print "Content", json.dumps(evt.get("content"))
                        on_chat_message(uid, evt.get("content"))
                    if evt.get("type") == "read_chat":
                        rm = evt.get("content")
                        read_message(rm.get('sid'), rm.get('mid'))
                except:
                    traceback.print_exc()
                    print "Bad json", message, uid
            except:
                traceback.print_exc()
                break
        ws.close()
        print "User ", uid, "exit"
        rs.srem("users_online", uid)
        notify_online_status(uid, False)
        if participants.get(str(uid)) is not None:
            participants[str(uid)].remove(ws)
            if len(participants[str(uid)]) == 0:
                del participants[str(uid)]
    else:
        print "NO wsgi.websocket:("
    return "OK"


def notify_online_status(uid, is_online):
    followers = rs.smembers('user:' + str(uid) + ':followers')
    message = json.dumps({"type": "online_status", "content": {"user_id": uid, "online": is_online}})
    for f in followers:
        send_message_to_user(f, message)


def on_chat_message(uid, msg):
    rid = int(msg.get('rid', 0))
    if rid == 0 or len(msg.get('text', "")) == 0:
        return
    chid = "chat:message:%s:%d:" % (uid, rid)
    mid = rs.incr(chid + "counter")
    chid = chid + str(mid)
    score = calendar.timegm(datetime.utcnow().timetuple())
    chatm = {"id": mid, "text": msg.get('text'), 'is_read': False, 'sid': uid, 'rid': rid, "type": "chat"}
    rs.hmset(chid, chatm)
    rs.zadd("chat:user:%d:unread" % rid, chid, score)
    dialog = "chat:dialog:%d:%d" % (min(int(uid), rid), max(int(uid), rid))
    rs.zadd(dialog, chid, score)
    rs.zadd("chat:user:%s:dialogs" % uid, dialog, score)
    rs.zadd("chat:user:%d:dialogs" % rid, dialog, score)
    chatm["create_date"] = score
    message = json.dumps({"type": "chat", "content": chatm})
    send_message_to_user(uid, message)
    send_message_to_user(rid, message)
    unread = get_unread._original()
    unread_message = ""
    if len(unread) > 0:
        unread_message = json.dumps({"type": "unread", "content": {"count": len(unread), "message": unread[0]}})
        send_message_to_user(rid, unread_message)


def send_message_to_user(uid, message):
    wss = participants.get(str(uid))
    if wss is not None:
        for ws in wss:
            try:
                ws.send(message)
            except:
                pass


@api_route('/chat/read/<int:sid>/<int:mid>')
def read_message(sid, mid):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    chid = "chat:message:%d:%d:%d" % (sid, uid, mid)
    if rs.exists(chid) != 1:
        return -1
    if rs.hget(chid, "is_read") == "true":
        return 0
    rs.hset(chid, "is_read", 'true')
    rs.zrem("chat:user:%d:unread" % uid, chid)
    unread = get_unread._original()
    message = {"type": "unread", "content": {"count": len(unread)}}
    if len(unread) > 0:
        message["content"]["message"] = unread[0]
    send_message_to_user(uid, json.dumps(message))
    send_message_to_user(sid, json.dumps({"type": "read_chat", "content": {"mid": mid, "rid": int(uid)}}))
    return 1


@api_route('/chat/unread')
def get_unread():
    uid = loggedUserUid()
    if uid == 0:
        return -2
    if rs.exists("chat:user:%d:unread" % uid) != 1:
        return []
    offset = request.args.get("offset", 0)
    count = request.args.get("count", 10)
    rows = []
    lua = """local r1 = redis.call('ZREVRANGE', KEYS[1], KEYS[2], KEYS[3]);
for i = 1, table.getn(r1) do
  local chid = r1[i]
  r1[i] = {}
  r1[i][1] = redis.call('hget', chid, 'id')
  r1[i][2] = redis.call('hget', chid, 'text')
  r1[i][3] = redis.call('zscore', KEYS[1], chid)
  local uid = redis.call('hget', chid, 'sid')
  r1[i][4] = redis.call('get', 'users:' .. tostring(uid))
  r1[i][5] = redis.call('hget', chid, 'type')
end
return r1;"""
    ids = rs.eval(lua, 3, "chat:user:%d:unread" % uid, offset, offset + count)
    #ids = rs.sort('look:' + str(look_id) + ':comments', start=offset, num=count, get='#')
    for cmid in ids:
        cmnt = {'id': int(cmid[0]), 'text': cmid[1], 'create_date': int(cmid[2]), "type": cmid[4]}
        cmnt['user'] = json.loads(cmid[3])
        rows.append(cmnt)
    return rows


@api_route('/chat/dialogs')
def get_dialogs():
    uid = loggedUserUid()
    if uid == 0:
        return []
    if rs.exists("chat:user:%d:dialogs" % uid) != 1:
        return []
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 10))
    rows = []
    lua = """local r1 = redis.call('ZREVRANGE', KEYS[1], KEYS[2], KEYS[3]);
for i = 1, table.getn(r1) do
  local dialog = r1[i]
  local chid = redis.call('ZREVRANGE', dialog, 0, 0)[1];
  r1[i] = {}
  r1[i][1] = redis.call('hget', chid, 'id')
  r1[i][2] = redis.call('hget', chid, 'text')
  r1[i][3] = redis.call('zscore', dialog, chid)
  local uid = redis.call('hget', chid, 'sid')
  r1[i][4] = redis.call('get', 'users:' .. tostring(uid))
  local uid = redis.call('hget', chid, 'rid')
  r1[i][5] = redis.call('get', 'users:' .. tostring(uid))
  r1[i][6] = redis.call('sismember', 'users_online', uid)
  r1[i][7] = redis.call('hget', chid, 'is_read')
end
return r1;"""
    ids = rs.eval(lua, 3, "chat:user:%d:dialogs" % uid, offset, offset + count - 1)
    #ids = rs.sort('look:' + str(look_id) + ':comments', start=offset, num=count, get='#')
    for cmid in ids:
        cmnt = {'id': int(cmid[0]), 'text': cmid[1], 'create_date': int(cmid[2]), 'is_read': json.loads(cmid[6])}
        cmnt['user'] = json.loads(cmid[3])
        cmnt['user']['is_online'] = cmid[5]
        cmnt['companion'] = json.loads(cmid[3]) if uid != cmnt['user']['id'] else json.loads(cmid[4])
        rows.append(cmnt)
    return rows


@api_route('/chat/<int:sid>/history')
def get_chat_history(sid):
    uid = loggedUserUid()
    if uid == 0:
        return []
    dialog = "chat:dialog:%d:%d" % (min(int(uid), sid), max(int(uid), sid))
    if rs.exists(dialog) != 1:
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
  r1[i][4] = redis.call('hget', chid, 'sid')
  r1[i][5] = redis.call('hget', chid, 'rid')
  r1[i][6] = redis.call('hget', chid, 'is_read')
end
return r1;"""
    ids = rs.eval(lua, 3, dialog, offset, offset + count - 1)
    #ids = rs.sort('look:' + str(look_id) + ':comments', start=offset, num=count, get='#')
    for cmid in ids:
        cmnt = {'id': int(cmid[0]), 'text': cmid[1], 'create_date': int(cmid[2]), 'is_read': json.loads(cmid[5]), 'sid': int(cmid[3]), 'rid': int(cmid[4])}
        rows.append(cmnt)
    return rows


@api_route('/chat/test')
def chat_test():
    for p in participants:
        wss = participants[p]
        for ws in wss:
            try:
                ws.send(json.dumps("TEST"))
            except:
                ws.close()
    print "Participants: ", len(participants)
    return "OK"

'''
chat:message:fid:tid:id = hash{text, create_date, is_read}
chat:user:uid:unread         = zlist(msgids...)
chat:dialog:Minuid:Maxuid = zlist(msgids...)
chat:user:uid:dialogs = zlist(dialogids...)

def get_history(uid):
  sort(chat:dialog:uid:uid)
'''
