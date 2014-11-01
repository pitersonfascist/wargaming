# -*- coding: utf-8 -*-
from flask import Flask, send_file, redirect, request, Response  # url_for,
from functools import wraps
#from SMTPHandler import TlsSMTPHandler
from apscheduler.scheduler import Scheduler
#import logging
import os
import httplib
import json
import urlparse
import requests
import logging

app = Flask(__name__)
app.config.from_pyfile('../app.cfg')
app.debug = True

# Start the scheduler
logging.basicConfig()
sched = Scheduler()
sched.start()

print "___init___", __name__
# Schedules job_function to be run on the each 8 hours


def api_response(f, jsondump):
    @wraps(f)
    def decorated(*args, **kwargs):
        res = f(*args, **kwargs)
        return Response(json.dumps(res) if jsondump else res, mimetype='application/json')
    decorated._original = f
    return decorated


def api_route(route, jsondump=True, **kwargs):
    route = "/api" + route
    def api_decorator(func):
        return app.route(route, **kwargs)(api_response(func, jsondump))
    return api_decorator


@app.errorhandler(404)
def not_found(error):
    return "404 error", 404


@api_route('/help', methods=['GET'])
def help():
    """Print available functions."""
    func_list = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = rule.methods
            func_list.append({"endpoint": rule.rule, "methods": ','.join(methods - set(["HEAD", "OPTIONS"])), "doc": app.view_functions[rule.endpoint].__doc__})
    return func_list


@app.route('/media/<path:filename>')
def base_static(filename):
    if os.path.isfile(app.config['UPLOAD_FOLDER'] + filename):
        return send_file(app.config['UPLOAD_FOLDER'] + filename)
    else:
        return not_found(None)


@api_route('/crash', methods=['POST'], jsondump=False)
def send_crash():
    data = request.stream.read()
    headers = {}
    for k in request.headers:
        if k[0] in ['Content-Length', 'Content-Type', 'X-Bugsense-Api-Key']:
            headers[k[0]] = k[1]
    conn = httplib.HTTPConnection("www.bugsense.com:80") #https://bugsense.appspot.com/api/errors 
    conn.request("POST", "/api/errors", data, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()
    return data


@app.route('/api/externalimage')
def get_externalimage():
    try:
        url = request.args.get('url')
        r = requests.get(url)
        return Response(r.content, mimetype=r.headers['Content-Type'])
        #req = urllib2.Request(url)
        #response = urllib2.urlopen(req)
        #return Response(response.read(), mimetype=response.info().getheader('Content-Type'))
    except:
        return Response('')


@app.route('/api/externalupload', methods=['POST'])
def make_externalupload():
    #try:
    #import time
    from datetime import datetime
    from time import mktime
    import hashlib
    from uLOOK.views.users import loggedUserUid
    from uLOOK.views import ensure_dir
    uid = loggedUserUid()
    url = request.form['url']
    url = urlparse.unquote(url).decode('utf8')
    photo = request.files.get("photo")
    ext = photo.filename.rsplit('.', 1)[1]
    tmp = hashlib.md5(str(mktime(datetime.now().timetuple())) + str(uid)).hexdigest()
    ensure_dir(app.config['UPLOAD_FOLDER'] + "tmp/")
    photo.save(app.config['UPLOAD_FOLDER'] + "tmp/" + tmp + "." + ext)
    files = {"photo": (photo.filename, open(app.config['UPLOAD_FOLDER'] + "/tmp/" + tmp + "." + ext, 'rb'))}
    r = requests.post(url, files=files)
    os.unlink(app.config['UPLOAD_FOLDER'] + "tmp/" + tmp + "." + ext)
    return Response(r.text, mimetype=r.headers['Content-Type'])
    #return Response('12345')
    #except:
    #    return Response('')


@app.route('/', methods=['GET'])
@app.route('/<path:filename>', methods=['GET'])
def root_static(filename=None):
    if filename is None:
        return redirect('/index.html')
    else:
        if os.path.isfile(app.config['STATIC_FOLDER'] + filename):
            return send_file(app.config['STATIC_FOLDER'] + filename)
        else:
            return not_found(None)


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == 'adminko'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/<path:filename>')
@requires_auth
def admin_pages(filename=None):
    return send_file(app.config['STATIC_FOLDER'] + "admin/" + filename)


from warg.views.jobs.battle_reminder import startup_initialize as battle_reminder_init
battle_reminder_init()