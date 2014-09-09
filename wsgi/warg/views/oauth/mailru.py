from flask import Flask, redirect, url_for, session, request
from flask_oauth import OAuth


SECRET_KEY = 'development key'
DEBUG = True
#'client_id':710598
MAILRU_APP_ID = '710598'
MAILRU_APP_SECRET = '4f519bdfaa607149beceadd57fbaa6b6'


app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

mailru = oauth.remote_app('mailru',
    base_url='http://www.appsmail.ru/',
    request_token_url=None,
    access_token_url='https://connect.mail.ru/oauth/token',
    authorize_url='https://connect.mail.ru/oauth/authorize?response_type=code&',
    access_token_params={'grant_type': 'authorization_code'},
    access_token_method='POST',
    consumer_key=MAILRU_APP_ID,
    consumer_secret=MAILRU_APP_SECRET
)


('/')
def index():
    return redirect(url_for('login'))


('/login')
def login():
    session.clear()
    return mailru.authorize(callback=url_for('mailru_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))


('/login/authorized')
@mailru.authorized_handler
def mailru_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['oauth_token'] = (resp['access_token'], '')
    me = mailru.get('/me')
    return 'Logged in as id=%s name=%s email=%s redirect=%s' % \
        (me.data['id'], me.data['name'], me.data['email'], request.args.get('next'))


@mailru.tokengetter
def get_mailru_oauth_token():
    return session.get('oauth_token') 
  
if __name__ == '__main__':
    app.run()
