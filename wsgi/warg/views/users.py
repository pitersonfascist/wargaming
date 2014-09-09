'''
Created on 8 june 2013

@author: piterson
'''
from uhelp import app, api_route, requires_auth
from flask import request, Response
from uhelp.views import rs, ensure_dir
import vkontakte
import json
#import time
import os
from datetime import datetime
from time import mktime
import calendar
import httplib
import urllib
import hashlib

app_id = '4394961'
app_secret = 'sPouhHAL955t7fjVllBw'


@app.route('/api/user/vk', methods=['POST', 'GET'])
def register_vk():
    if request.args.get("code", None) is None:
        return json.dumps("No code")
    params = urllib.urlencode({'client_id': 4396091, 'code': request.args.get("code"), 'client_secret': 'eDeWLToLuffLO4hWveIW', \
    'redirect_uri': 'http://uhelp-piterson.rhcloud.com/api/user'})
    conn = httplib.HTTPSConnection("oauth.vk.com")
    conn.request("GET", "/access_token?" + params)
    res = conn.getresponse()
    data = res.read()
    resp = json.loads(data)
    if resp.get('access_token') is None:
        return json.dumps("No token: " + resp.get('error_description'))
    vkuid = 'soc_user:vk:' + str(resp['user_id'])
    print "token", resp.get('access_token')
    if rs.exists(vkuid) != 1:
        vk = vkontakte.API(token=resp.get('access_token'))
        profiles = vk.getProfiles(fields='uid,education,first_name,last_name,sex,bdate,city,country,timezone,photo_big')
        if len(profiles) > 0:
            profile = profiles[0]
        else:
            return json.dumps("Wrong access token: " + resp.get('access_token'))
        insert_vk_user(profile)
    uid = rs.hget(vkuid, 'uid')

    return make_login_response(uid, False)
    #return HttpResponse(simplejson.dumps(uid), mimetype='application/json')


def make_login_response(uid, expire=True):
    response = app.make_response(json.dumps(uid))
    #if request.cookies.get('uSSID') is None:
    response.headers['Content-type'] = 'application/json'
    ussid = hashlib.md5(str(mktime(datetime.now().timetuple())) + str(uid)).hexdigest()
    rs.hmset('ussid:' + ussid, {'uid': uid})
    if expire:
        rs.expire('ussid:' + ussid, 12 * 3600)
    response.set_cookie('uSSID', value=ussid)
    return response


def user_directory(uid):
    outfile = "users/"
    for i in range(0, 3):
        f = uid / 200 ** (3 - i)
        outfile = outfile + str(f) + "/"
    ensure_dir(app.config['UPLOAD_FOLDER'] + outfile)
    return outfile


def process_user_image(name, ext, uid):
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " -resize x32 " + app.config['UPLOAD_FOLDER'] + name + "_s.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " -resize x90 " + app.config['UPLOAD_FOLDER'] + name + "_m.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " " + app.config['UPLOAD_FOLDER'] + name + ".jpg")
    os.unlink(app.config['UPLOAD_FOLDER'] + name + "_orig." + ext)


def insert_vk_user(profile):
    ext = profile['photo_big'].split(".")[-1]
    uid = rs.incr('users_counter')
    outfile = user_directory(uid)
    try:
        urllib.urlretrieve(profile['photo_big'], app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext)
    except:
        os.system("cp %s %s" % (app.config['STATIC_FOLDER'] + 'no_avatar.jpg', app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext))
    process_user_image(outfile + str(uid), ext, uid)
    vkuid = 'soc_user:vk:' + str(profile['uid'])
    bstamp = 0
    try:
        bstamp = int(mktime(datetime.strptime(profile['bdate'], '%d.%m.%Y').timetuple()))
    except:
        pass
    user_data = {'id':uid, 'name':profile['first_name']+' ' + profile['last_name'], 'birthday':bstamp, 'avatar':outfile + str(uid), 'create_date': int(mktime(datetime.now().timetuple()))}
    rs.set("users:" + str(uid), json.dumps(user_data))
    rs.set("user:notifications:" + str(uid), 1)
    rs.sadd("user_soc_links:" + str(uid), vkuid)
    rs.hmset(vkuid, {'uid': str(uid), 'profile': json.dumps(profile)})
    #md5(viewer_id(uid)+'_'+app_id+'_'+app_secret_key),
    auth_key = hashlib.md5(app_id + '_' + str(profile['uid']) + '_' + app_secret).hexdigest()
    rs.hmset('soc_auth:vk:' + auth_key, {'uid': str(uid)})
    from uhelp.views.full_text import storeUserInIndex
    storeUserInIndex(user_data)


@app.route('/api/user/vk2', methods=['POST'])
def register_native_vk():
    try:
        data = json.loads(request.stream.read())
    except:
        return json.dumps("Wrong json")
    if data.get('auth_key') is None:
        return json.dumps("Wrong auth_key!")
    if data.get('uid') is None:
        return json.dumps("Wrong profile data!")
    appid = app_id if data.get('app_id') is None else data.get('app_id')
    auth_key2 = hashlib.md5(appid + '_' + str(data['uid']) + '_' + app_secret).hexdigest()
    #auth key for primary app
    _auth_key = hashlib.md5(app_id + '_' + str(data['uid']) + '_' + app_secret).hexdigest()
    #print auth_key2, data.get('auth_key')
    if data['auth_key'] != auth_key2:
        return json.dumps("Wrong auth_key")
    if rs.exists('soc_auth:vk:' + _auth_key) != 1:
        insert_vk_user(data)
    uid = rs.hget('soc_auth:vk:' + _auth_key, 'uid')
    uid = json.loads(rs.get("users:%s" % uid))['id']
    return make_login_response(uid)


@requires_auth
@api_route('/user/create', methods=['POST'])
def add_user_by_admin():
    try:
        profile = json.loads(request.stream.read())
    except:
        return "Wrong json"
    ext = profile['photo_big'].split(".")[-1]
    uid = rs.incr('users_counter')
    outfile = user_directory(uid)
    try:
        urllib.urlretrieve(profile['photo_big'], app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext)
    except:
        os.system("cp %s %s" % (app.config['STATIC_FOLDER'] + 'no_avatar.jpg', app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext))
    process_user_image(outfile + str(uid), ext, uid)
    bstamp = 0
    try:
        bstamp = int(mktime(datetime.strptime(profile['bdate'], '%d.%m.%Y').timetuple()))
    except:
        pass
    user_data = {'id': uid, 'name': profile['name'], 'birthday': bstamp, 'avatar': outfile + str(uid), 'create_date': int(calendar.timegm(datetime.utcnow().timetuple()))}
    rs.set("users:" + str(uid), json.dumps(user_data))
    from uhelp.views.full_text import storeUserInIndex
    storeUserInIndex(user_data)
    return uid


def loggedUserUid():
    #print "uSSID", request.cookies.get('uSSID')
    try:
        if request.cookies.get('uSSID') and rs.exists('ussid:' + request.cookies.get('uSSID')) == 1:
            uid = rs.hget('ussid:' + request.cookies.get('uSSID'), 'uid')
            uid = json.loads(rs.get("users:%s" % uid))['id']
            return str(uid)  # str for capability with prev
    except:
        pass
    return 0


@api_route('/user', methods=['GET'])
def loggedUser():
    uid = loggedUserUid()
    return detail._original(uid)


@api_route('/user/<int:user_id>')
def detail(user_id):
    #return request.headers.get('Cookie')
    u = None
    if (user_id is not None) and rs.exists('users:' + str(user_id)) == 1:
        u = rs.get('users:' + str(user_id))
        u = json.loads(rs.get("users:" + str(user_id)))
        u['followers'] = rs.scard('user:' + str(user_id) + ':followers')
        u['is_follow'] = int(rs.sismember('user:' + str(user_id) + ':followers', loggedUserUid()))
        u['looks'] = rs.scard('user_looks:' + str(user_id))
        u['soc_links'] = list(rs.smembers('user_soc_links:' + str(user_id)))
        u['is_online'] = int(rs.sismember('users_online', user_id))
        #u = json.dumps(u)
    return u or {}


@api_route('/user_merge/<int:user_id>')
def user_merge(user_id):
    #soc_auth:vk:  returns user id from json
    #sessions from old user   returns user id from json
    #likes, del comments, owners
    if rs.exists("users:" + str(user_id)) != 1:
        return Response(json.dumps(-1), mimetype='application/json')
    uid = loggedUserUid()
    if uid == 0:
        return Response(json.dumps(-2), mimetype='application/json')
    #user_looks
    rs.sunionstore('user_looks:' + str(uid), 'user_looks:' + str(uid), 'user_looks:' + str(user_id))
    #user_following_looks
    rs.sunionstore('user:' + str(uid) + ':follownig_looks', 'user:' + str(uid) + ':follownig_looks', 'user:' + str(user_id) + ':follownig_looks')
    #following
    folowing = rs.smembers('user:' + str(user_id) + ':following')
    for f in folowing:
        rs.srem('user:%s:followers' % f, user_id)
        rs.sadd('user:%s:followers' % f, uid)
    rs.sunionstore('user:' + str(uid) + ':following', 'user:' + str(uid) + ':following', 'user:' + str(user_id) + ':following')
    #followers
    rs.sunionstore('user:' + str(uid) + ':followers', 'user:' + str(uid) + ':followers', 'user:' + str(user_id) + ':followers')
    #messages
    msgs = rs.keys("chat:message:%d:*" % user_id)
    for m in msgs:
        if rs.type(m) == "hash":
            rs.hset(m, 'sid', uid)
    msgs = rs.keys("chat:message:*:%d:*" % user_id)
    for m in msgs:
        if rs.type(m) == "hash":
            rs.hset(m, 'rid', uid)
    #dialogs
    print "chat:user:%s:unread" % uid, "chat:user:%d:unread" % user_id
    rs.zunionstore("chat:user:%s:unread" % uid, ("chat:user:%s:unread" % uid, "chat:user:%d:unread" % user_id))
    rs.zunionstore("chat:user:%s:dialogs" % uid, ("chat:user:%s:dialogs" % uid, "chat:user:%d:dialogs" % user_id))
    #soc links
    slinks = rs.smembers('user_soc_links:%d' % user_id)
    for slink in slinks:
        rs.hset(slink, "uid", uid)
    rs.sunionstore('user_soc_links:%s' % uid, 'user_soc_links:%s' % uid, 'user_soc_links:%d' % user_id)
    #set user linked
    user = json.loads(rs.get("users:%d" % user_id))
    user['id'] = uid
    rs.set("users:%d" % user_id, json.dumps(user))
    return 1


@app.route('/api/user/logout')
def logout():
    ussid = request.cookies.get('uSSID')
    if ussid is None:
        return app.make_response(json.dumps(0))
    response = app.make_response(json.dumps(1))
    rs.delete('ussid:' + ussid)
    response.set_cookie('uSSID', value=None)
    return response


@app.route('/api/user/<int:user_id>/fake_login')
@requires_auth
def fake_login(user_id):
    return make_login_response(str(user_id))

