from flask import url_for, session, request
from flask_oauth import OAuth
from uhelp import app, api_route
from uhelp.views import rs
from uhelp.views.oauth import make_oauth_response
import json
import os
from datetime import datetime
from time import mktime
import urllib

#Facebook app integration
#http://ukaszblog.com/creating-facebook-flash-as3-js-application-part1-login-authorization-and-getting-user-data/

FACEBOOK_APP_ID = '666370860120323'
FACEBOOK_APP_SECRET = 'f2ee0daa5420ddcef0d4e2f0bc040308'

oauth = OAuth()

facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': 'email,user_birthday'}
)


@app.route('/api/facebook/login')
def facebook_login():
    session.clear()
    return facebook.authorize(callback=url_for('facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


@app.route('/api/facebook/login/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    return process_fb_login(resp['access_token'])


@app.route('/api/facebook/applogin')
def facebook_applogin():
    if request.args.get("access_token", None) is None:
        print "No fb access token"
        return app.make_response("0")
    return process_fb_login(request.args.get("access_token", None), False)


def process_fb_login(access_token, oauth=True):
    session['fb_oauth_token'] = (access_token, '')
    me = facebook.get('/me')
    if me.data.get("id", None) is None:
        return app.make_response("0")
    session.clear()
    #print "User data ", me.data
    fbuid = 'soc_user:fb:' + str(me.data['id'])
    if rs.exists(fbuid) != 1:
        insert_fb_user(me.data)
    uid = rs.hget(fbuid, 'uid')
    if oauth:
        return make_oauth_response(uid, False)
    else:
        from uhelp.views.users import make_login_response
        return make_login_response(uid, False)


def insert_fb_user(profile):
    photo_url = "https://graph.facebook.com/%s/picture?type=large" % profile['id']
    uid = rs.incr('users_counter')
    from uhelp.views.users import user_directory, process_user_image
    outfile = user_directory(uid)
    try:
        urllib.urlretrieve(photo_url, app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg")
    except:
        os.system("cp %s %s" % (app.config['STATIC_FOLDER'] + 'no_avatar.jpg', app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg"))
    process_user_image(outfile + str(uid), "jpg", uid)
    fbuid = 'soc_user:fb:' + str(profile['id'])
    bstamp = 0
    try:
        bstamp = int(mktime(datetime.strptime(profile['birthday'], '%m/%d/%Y').timetuple()))
    except:
        pass
    user_data = {'id': uid, 'name': profile['name'], 'birthday': bstamp, 'avatar': outfile + str(uid), 'create_date': int(mktime(datetime.now().timetuple()))}
    rs.set("users:" + str(uid), json.dumps(user_data))
    rs.set("user:notifications:" + str(uid), 1)
    rs.sadd("user_soc_links:" + str(uid), fbuid)
    rs.hmset(fbuid, {'uid': str(uid), 'profile': json.dumps(profile)})
    from uhelp.views.full_text import storeUserInIndex
    storeUserInIndex(json.loads(json.dumps(user_data)))  # unicode problems


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('fb_oauth_token')

#{'username': 'petrenko.ievgenii', 'first_name': 'Ievgenii', 'last_name': 'Petrenko', 'verified': True,
#'name': 'Ievgenii Petrenko', 'locale': 'ru_RU', 'hometown': {'id': '114603081888764', 'name': 'Tashkent, Uzbekistan'},
#'work': [{'employer': {'id': '214151925284360', 'name': 'Notan'}}], 'email': 'gamer_blin@rambler.ru',
#'updated_time': '2013-06-18T12:29:54+0000', 'link': 'https://www.facebook.com/petrenko.ievgenii',
#'location': {'id': '111227078906045', 'name': 'Kyiv, Ukraine'}, 'gender': 'male', 'timezone': 3,
#'education': [{'school': {'id': '108036059231019', 'name': 'Kyiv National Taras Shevchenko University'},
#'type': 'High School'}, {'school': {'id': '110479652307621', 'name': 'Taras Shevchenko University of Kyiv'},
#'type': 'College', 'year': {'id': '136328419721520', 'name': '2009'}}], 'id': '100000973972781'}