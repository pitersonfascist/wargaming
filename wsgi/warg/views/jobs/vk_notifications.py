'''
Created on 21 august 2013

@author: piterson
'''
from uhelp.views import rs
import httplib
import urllib
import json
import re


def send_notifications():
    print "send_notifications()"
    from uhelp.views.users import app_id, app_secret
    #https://oauth.vk.com/access_token?client_id=3684647&client_secret=bHyZfkwS4ogl4unvRQov&grant_type=client_credentials
    params = urllib.urlencode({'client_id': app_id, 'client_secret': app_secret, 'grant_type': 'client_credentials'})
    conn = httplib.HTTPSConnection("oauth.vk.com")
    conn.request("GET", "/access_token?" + params)
    res = conn.getresponse()
    data = res.read()
    resp = json.loads(data)
    if resp.get('access_token') is None:
        raise Exception("No token: " + resp.get('error_description'))
    keys = rs.keys("notification:vk:*")
    for key in keys:
        ntfn = rs.hget(key, "message")
        params = urllib.urlencode({'user_id': rs.hget(key, "user_id"), 'client_secret': app_secret, 'access_token': resp.get('access_token'), "message": ntfn})
        conn = httplib.HTTPSConnection("api.vk.com")
        conn.request("GET", "/method/secure.sendNotification?" + params)
        print rs.hget(key, "user_id"), ntfn
        print conn.getresponse().read()
        rs.delete(key)


def add_notification(user, friends):
    f1 = open("./templates/notification_user_add.txt")
    template = f1.readline().decode('utf-8')
    f1.close()
    user = json.loads(rs.get("users:" + str(user)))
    for f in friends:
        slinks = rs.smembers("user_soc_links:" + str(f["id"]))
        for sl in slinks:
            mtch = re.match(r'soc_user:vk:(?P<vkid>\d+)', sl)
            if mtch:
                #print mtch.group("vkid")
                ntfn = template % (user["name"])
                msg = rs.hget("notification:vk:" + str(f["id"]), "message") or ""
                #print "msg = ", msg + ntfn
                rs.hmset("notification:vk:" + str(f["id"]), {"message": msg + ntfn, "user_id": mtch.group("vkid")})
                break
    pass
