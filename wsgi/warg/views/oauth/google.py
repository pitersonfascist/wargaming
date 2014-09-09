from flask import redirect, url_for, session, request
from flask_oauth import OAuth
from uhelp import app
from uhelp.views import rs, ensure_dir
from uhelp.views.oauth import make_oauth_response
import json
import os
from datetime import datetime
from time import mktime
import urllib

GOOGLE_APP_ID = '914719034544.apps.googleusercontent.com'
GOOGLE_APP_SECRET = '8OzYvZJ1IXoxrHoqtNHbherg'

oauth = OAuth()

google = oauth.remote_app('google',
    base_url='https://www.googleapis.com/plus/v1',
    request_token_url=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_method='POST',
    access_token_params={'grant_type': 'authorization_code'},
    consumer_key=GOOGLE_APP_ID,
    consumer_secret=GOOGLE_APP_SECRET,
    request_token_params={'scope': 'https://www.googleapis.com/auth/plus.login https://www.googleapis.com/auth/userinfo.email','response_type': 'code'},
)


('/google/login')
def google_login():
    return google.authorize(callback=url_for('google_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


('/google/login/authorized')
@google.authorized_handler
def google_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_oauth_token'] = (resp['access_token'], '')
    #{u'organizations': [{u'startDate': u'2004', u'type': u'school', u'name': u'Taras Shevchenko University of Kiev', u'primary': True, u'title': u'theoretical physics'}], u'kind': u'plus#person', u'displayName': u'Petrenko Ievgenii', u'name': {u'givenName': u'Petrenko', u'familyName': u'Ievgenii'}, u'isPlusUser': True, u'url': u'https://plus.google.com/109727710196474425460', u'gender': u'male', u'image': {u'url': u'https://lh5.googleusercontent.com/-m38XEhGtz4E/AAAAAAAAAAI/AAAAAAAAAFs/BK6QELiDzKw/photo.jpg?sz=50'}, u'etag': u'"FS8hSDZUt39rsvp2gH0cFIHdkm8/Zj2vScZzbooi829PA67acOEiEAU"', u'verified': False, u'id': u'109727710196474425460', u'objectType': u'person'}
    from urllib2 import Request, urlopen, URLError

    headers = {'Authorization': 'OAuth '+ resp['access_token']}
    req = Request('https://www.googleapis.com/plus/v1/people/me',
                  None, headers)
    ereq = Request('https://www.googleapis.com/oauth2/v2/userinfo',
                  None, headers)
    try:
        res = urlopen(req)
        eres = urlopen(ereq)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        return res.read()

    data = json.loads(res.read())
    edata = json.loads(eres.read())
    data['email'] = edata['email']
    guid = 'soc_user:google:' + str(data['id'])
    if rs.exists(guid) != 1:
	insert_google_user(data)
    uid = rs.hget(guid, 'uid')
    return make_oauth_response(uid, False)
      
def insert_google_user(profile):
    if profile.get('image', None) is not None:
	photo_url = profile['image']['url'].replace("?sz=50", "")
    uid = rs.incr('users_counter')
    outfile = "users/"
    for i in range(0, 3):
	f = uid/200**(3-i)
	outfile = outfile + str(f) + "/"
    ensure_dir(app.config['UPLOAD_FOLDER'] + outfile)
    try:
	urllib.urlretrieve(photo_url, app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg")
    except:
	os.system("cp %s %s" % (app.config['STATIC_FOLDER'] + 'no_avatar.jpg', app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg"))
    os.system("convert " + app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg" + " -resize x32 " + app.config['UPLOAD_FOLDER'] + outfile + str(uid)+"_s.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg" + " -resize x90 " + app.config['UPLOAD_FOLDER'] + outfile + str(uid)+"_m.jpg")
    os.system("convert " + app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg" + " " + app.config['UPLOAD_FOLDER'] + outfile + str(uid)+".jpg")
    os.unlink(app.config['UPLOAD_FOLDER'] + outfile + str(uid) + "_orig.jpg")
    guid = 'soc_user:google:' + str(profile['id'])
    bstamp = 0
    try:
	bstamp = int(mktime(datetime.strptime(profile['birthday'], '%Y-%m-%d').timetuple()))
    except:
	pass
    user_data = {'id':uid, 'name':profile['displayName'], 'birthday':bstamp, 'avatar':outfile + str(uid), 'create_date': int(mktime(datetime.now().timetuple()))}
    rs.set("users:"+str(uid), json.dumps(user_data))
    rs.set("user:notifications:"+str(uid), 1)
    rs.sadd("user_soc_links:"+str(uid), guid)
    rs.hmset(guid, {'uid':str(uid), 'profile':json.dumps(profile)})
    from uhelp.views.full_text import storeUserInIndex
    storeUserInIndex(json.loads(json.dumps(user_data))) #unicode problems

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_oauth_token') 
  
