'''
Created on 8 june 2013

@author: piterson
'''
from warg import app, api_route, requires_auth
from flask import request
from warg.views import rs, ensure_dir
import json
#import time
import os
from datetime import datetime
from time import mktime
import httplib
import urllib
import hashlib

app_id = '541bb590158341e9e7675ffe10629c02'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and \
           filename.lower().rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def account_info(access_token, account_id):
    params = urllib.urlencode({'application_id': app_id, 'access_token': access_token,\
        'account_id': account_id, 'fields': 'account_id,created_at,nickname,private.friends'})
    conn = httplib.HTTPSConnection("api.worldoftanks.ru")
    conn.request("GET", "/wot/account/info/?" + params)
    res = conn.getresponse()
    data = json.loads(res.read())
    conn.close()
    return data


@app.route('/api/user/wot', methods=['POST', 'GET'])
def register_wot():
    access_token = request.args.get("access_token", None)
    if access_token is None:
        return json.dumps("No access token")
    wotuid = 'wot_user:' + request.args.get('account_id')
    print "wotuid", wotuid, access_token
    if rs.exists(wotuid) != 1:
        data = account_info(access_token, request.args.get('account_id'))
        if data['status'] == 'ok':
            insert_wot_user(data['data'][request.args.get('account_id')])
        else:
            return json.dumps("Error: " + data['error']['message'])
    if rs.hget(wotuid, 'virtual') == '1':
        rs.hset(wotuid, 'virtual', 0)
    uid = rs.hget(wotuid, 'uid')
    rs.srem("users:virtual", uid)
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
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " -resize x64 " + app.config['UPLOAD_FOLDER'] + name + "_s.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " -resize x90 " + app.config['UPLOAD_FOLDER'] + name + "_m.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + name + "_orig." + ext + " " + app.config['UPLOAD_FOLDER'] + name + ".jpg")
    os.unlink(app.config['UPLOAD_FOLDER'] + name + "_orig." + ext)


def insert_wot_user(profile, virtual=0):
    uid = rs.incr('users_counter')
    outfile = user_directory(uid)
    ext = 'jpg'
    try:
        urllib.urlretrieve(profile['photo_big'], app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext)
    except:
        os.system("cp %s %s" % (app.config['STATIC_FOLDER'] + 'no_avatar.jpg', app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig." + ext))
    process_user_image(outfile + str(uid), ext, uid)
    wotuid = 'wot_user:' + str(profile['account_id'])
    user_data = {'id': uid, 'avatar': outfile + str(uid), 'create_date': int(mktime(datetime.now().timetuple()))}
    for k in profile:
        if k != 'private':
            user_data[k] = profile[k]
    from warg.views.followers import followUserByUser
    if profile['private'] is not None:
        for fid in profile['private']['friends']:
            wotfid = 'wot_user:%d' % fid
            if rs.exists(wotfid) == 1:
                followUserByUser(rs.hget(wotfid, 'uid'), str(uid))
    rs.set("users:" + str(uid), json.dumps(user_data))
    rs.sadd("user_soc_links:" + str(uid), wotuid)
    rs.hmset(wotuid, {'uid': str(uid), 'profile': json.dumps(profile), "virtual": virtual})
    if virtual == 1:
        rs.sadd("users:virtual", uid)
    from warg.views.full_text import storeUserInIndex
    storeUserInIndex(user_data)
    return uid


@api_route('/user/avatar', methods=['POST'])
def add_user_avatar():
    uid = loggedUserUid()
    if uid == 0:
        return -2
    outfile = user_directory(uid)
    for f in request.files:
        _file = request.files.get(f)
        ensure_dir(app.config['UPLOAD_FOLDER'] + outfile)
        print "File: " + f, _file.filename
        if allowed_file(_file.filename):
            ext = _file.filename.rsplit('.', 1)[1]
            fname = outfile + str(uid)
            _file.save(app.config['UPLOAD_FOLDER'] + fname + "_orig." + ext)
            process_user_image(outfile + str(uid), ext, uid)
        break
    return uid


def loggedUserUid():
    #print "uSSID", request.cookies.get('uSSID')
    try:
        if request.cookies.get('uSSID') and rs.exists('ussid:' + request.cookies.get('uSSID')) == 1:
            uid = rs.hget('ussid:' + request.cookies.get('uSSID'), 'uid')
            uid = json.loads(rs.get("users:%s" % uid))['id']
            return uid  # str for capability with prev
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
        u['soc_links'] = list(rs.smembers('user_soc_links:' + str(user_id)))
        u['is_online'] = int(rs.sismember('users_online', user_id))
        #u = json.dumps(u)
    return u or {}


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

