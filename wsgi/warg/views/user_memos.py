# -*- coding: utf-8 -*-
from warg import api_route
from flask import request
from warg.views import rs
import json
from warg.views.users import loggedUserUid


@api_route('/user/<int:user_id>/memo', methods=['POST'])
def create_user_memo(user_id=0):
    uid = loggedUserUid()
    if uid == 0:
        return -2
    try:
        data = json.loads(request.stream.read())
    except:
        return -3
    rs.set("user:%s:memo:%s" % (user_id, uid), data)
    return 1