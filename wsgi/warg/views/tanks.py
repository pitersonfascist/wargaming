# -*- coding: utf-8 -*-
from warg import api_route, requires_auth
from warg.views import rs
from warg.views.users import app_id
import json
import urllib, httplib


@requires_auth
@api_route('/system/tanks/update', methods=['GET'])
def update_tanks():
    conn = httplib.HTTPSConnection("api.worldoftanks.ru")
    params = urllib.urlencode({'application_id': app_id})
    conn.request("GET", "/wot/encyclopedia/tanks/?" + params)
    res = conn.getresponse()
    data = json.loads(res.read())
    print data
    conn.close()
    if data['status'] == 'ok':
        process_tanks(data['data'])
        return len(rs.keys('tank:*'))
    else:
        return json.dumps("Error: " + data['error']['message'])


def process_tanks(tanks):
    for tank_id in tanks:
        tank = tanks[tank_id]
        rs.set("tank:%s" % tank_id, json.dumps(tank))


@api_route('/system/tanks', methods=['GET'], jsondump=False)
def get_tanks():
    tanks = rs.keys('tank:*')
    tanks = rs.mget(tanks or [])
    return '[' + ','.join(tanks) + ']'