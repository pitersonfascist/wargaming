# -*- coding: utf-8 -*-
from warg import api_route, app, requires_auth
from flask import request
from warg.views import rs
import json
import os
import hashlib
import datetime
from time import mktime
from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh import sorting
from whoosh.writing import AsyncWriter
#from warg.views.users import loggedUserUid 786344400


@requires_auth
@api_route('/system/rebuildindex', methods=['GET'])
def rebuildIndex():
    rebuildUsersIndex()
    rebuildBattleIndex()
    return 1


def createUsersSchema():
    schema = Schema(nickname=TEXT(stored=True), account_id=NUMERIC(stored=True, unique=True, sortable=True), user_id=NUMERIC(stored=True, unique=True, sortable=True))
    create_in(usersindex_dir, schema)


def createBattleSchema():
    schema = Schema(id=NUMERIC(stored=True, unique=True, sortable=True), descr=TEXT(stored=True), battle_date=NUMERIC(stored=True, sortable=True))
    #, type=TEXT(stored=True), privacy=TEXT(stored=True)
    create_in(battlesindex_dir, schema)


def rebuildUsersIndex():
    createUsersSchema()
    uix = open_dir(usersindex_dir)
    writer = AsyncWriter(uix)

    users = rs.keys("users:*")
    users = rs.mget(users)
    for u in users:
        if u is not None:
            u = json.loads(u)
            storeUserInIndex(u, writer)
    writer.commit()


def rebuildBattleIndex():
    createBattleSchema()
    bix = open_dir(battlesindex_dir)
    writer = AsyncWriter(bix)

    #battles = rs.keys("battle:*")
    #battles = rs.mget(battles)
    #for u in users:
        #u = json.loads(u)
        #storeUserInIndex(u, writer)
    writer.commit()


def storeUserInIndex(u, writer=None):
    commit = False
    if writer is None:
        writer = AsyncWriter(uix)
        commit = True
    writer.add_document(nickname=u.get('nickname'), account_id=u.get('account_id'), user_id=u.get('id'))
    if commit:
        writer.commit()


def storeBattleInIndex(b, writer=None):
    commit = False
    if writer is None:
        writer = AsyncWriter(bix)
        commit = True
    writer.add_document(id=b.get('id'), descr=b.get('descr'), battle_date=u.get('battle_date'))
    if commit:
        writer.commit()


@api_route('/system/search/user', methods=['GET'])
def testuser():
    q = request.args.get("q", "")  # repr
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 20))
    with uix.searcher() as searcher:
        query = QueryParser("nickname", uix.schema).parse("nickname:*%s*" % q)  # QueryParser("nickname", ix.schema).parse("tash*")
        #print query
        user_id = sorting.FieldFacet("user_id", reverse=True)
        results = searcher.search_page(query, offset + 1, pagelen=count, sortedby=user_id)
        r = "\n".join([str(hit['user_id']) + " " + hit['nickname'] for hit in results])
    return r


@api_route('/user/search', methods=['GET'], jsondump=False)
def searchuser():
    q = request.args.get("q", "")  # repr
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 20))
    with uix.searcher() as searcher:
        query = QueryParser("nickname", uix.schema).parse("nickname:*%s*" % q)  # QueryParser("name", ix.schema).parse("tash*")
        #print query
        user_id = sorting.FieldFacet("user_id", reverse=True)
        results = searcher.search_page(query, max(offset / count, 0) + 1, pagelen=count, sortedby=user_id)
        print results.offset, count, offset, max(offset / count, 0) + 1
        if results.offset < offset:
            return "[]"
        tmp = hashlib.md5(str(mktime(datetime.datetime.now().timetuple()))).hexdigest() + "user_search_tmp"
        lua = """local searched = loadstring('return ' .. KEYS[1])()
for i = 1, table.getn(searched) do
    redis.call('sadd', KEYS[2], tostring(searched[i]))
end
local arr = redis.call('sort', KEYS[2], 'GET', 'users:*')
return arr"""
        res = rs.eval(lua, 2, '{' + ','.join(str(hit['user_id']) for hit in results) + '}', tmp)
        rs.delete(tmp)
        r = ",".join(res)
    return "[" + r + "]"


usersindex_dir = app.config['UPLOAD_FOLDER'] + "whoosh/users"
if not os.path.exists(usersindex_dir):
    os.makedirs(usersindex_dir)
    createUsersSchema()
uix = open_dir(usersindex_dir)

battlesindex_dir = app.config['UPLOAD_FOLDER'] + "whoosh/battles"
if not os.path.exists(battlesindex_dir):
    os.makedirs(battlesindex_dir)
    createBattleSchema()
bix = open_dir(battlesindex_dir)