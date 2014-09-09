from uhelp import app
from uhelp.views import rs
from flask import redirect, request, url_for
from datetime import datetime
from time import mktime
from urlparse import urlparse, urljoin
import hashlib


def make_oauth_response(uid, expire=True):
    response = app.make_response(redirect_back('vk_app_index'))
    ussid = hashlib.md5(str(mktime(datetime.now().timetuple())) + uid).hexdigest()
    rs.hmset('ussid:' + ussid, {'uid': uid})
    if expire:
        rs.expire('ussid:' + ussid, 12 * 3600)
    response.set_cookie('uSSID', value=ussid)
    return response


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


def redirect_back(endpoint, **values):
    target = request.args.get('next')
    if not target or not is_safe_url(target):
        target = url_for(endpoint, **values)
    return redirect(target)