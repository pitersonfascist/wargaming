from flask import Flask, redirect, url_for, session, request
from flask_oauth import OAuth


SECRET_KEY = 'development key'
DEBUG = True
TWITTER_APP_ID = '1Im5HGwZ6yj4OM062vhsqQ'
TWITTER_APP_SECRET = 'a1iKOkexGPzs7O7KqYJ8nxzNALD5d0fA2e4qRFpA'


app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

twitter = oauth.remote_app('twitter',
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    access_token_method='POST',
    consumer_key=TWITTER_APP_ID,
    consumer_secret=TWITTER_APP_SECRET
)


('/')
def index():
    return redirect(url_for('login'))


('/login')
def login():
    session.clear()
    return twitter.authorize(callback=url_for('twitter_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))

('/login/authorized')
@twitter.authorized_handler
def twitter_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['oauth_token'] = (resp['oauth_token'], '')
    session['oauth_secret'] = (resp['oauth_token_secret'], '')
    print "resp= ", resp, resp['screen_name']
    #return redirect(next_url)
    me = twitter.get('account/verify_credentials.json')
    print "me = ", me.data
    return 'Logged in as id=%s name=%s email=%s redirect=%s' % \
        (me.data['id'], me.data['name'], me.data['email'], request.args.get('next'))


@twitter.tokengetter
def get_twitter_oauth_token():
    return session.get('oauth_token') 
  
if __name__ == '__main__':
    app.run()
