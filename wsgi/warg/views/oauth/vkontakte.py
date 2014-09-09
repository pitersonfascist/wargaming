from flask import url_for, session, request
from flask_oauth import OAuth
from uhelp import app
from uhelp.views import rs, ensure_dir
from uhelp.views.oauth import make_oauth_response


VKONTAKTE_APP_ID = '3684318'
VKONTAKTE_APP_SECRET = 'Cyz8STP65cPVU5sdePvH'

oauth = OAuth()

vkontakte = oauth.remote_app('vkontakte',
    base_url='https://api.vk.com/',
    request_token_url=None,
    access_token_url='https://oauth.vk.com/access_token',
    authorize_url='https://oauth.vk.com/authorize',
    consumer_key=VKONTAKTE_APP_ID,
    consumer_secret=VKONTAKTE_APP_SECRET,
    request_token_params={'scope': 'email,uid,education,first_name,last_name,sex,bdate,city,country,timezone,photo_big'}
)

('/vkontakte/login')
def vkontakte_login():
    return vkontakte.authorize(callback=url_for('vkontakte_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


('/vkontakte/login/authorized')
@vkontakte.authorized_handler
def vkontakte_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['vk_oauth_token'] = (resp['access_token'], '')
    print "user_id", resp['user_id']
    vkuid = 'soc_user:vk:' + str(resp['user_id'])
    if rs.exists(vkuid) != 1:
	me = vkontakte.get('/method/users.get?user_ids=%d&fields=uid,education,first_name,last_name,sex,bdate,city,country,timezone,photo_big' % resp['user_id'])
	print "me=", me.data
	from uhelp.views.users import insert_vk_user
	insert_vk_user(me.data['response'][0])
    uid = rs.hget(vkuid, 'uid')
    return make_oauth_response(uid, False)
    #return make_login_response(uid, False)


@vkontakte.tokengetter
def get_vkontakte_oauth_token():
    return session.get('vk_oauth_token') 
