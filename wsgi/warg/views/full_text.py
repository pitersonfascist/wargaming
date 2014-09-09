# -*- coding: utf-8 -*-
from uhelp import api_route, app, requires_auth
from flask import request
from uhelp.views import rs
import json
import re
import os
import hashlib
import datetime
from time import mktime
from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.query import Term, And, Wildcard
from whoosh import sorting
from whoosh.writing import AsyncWriter
#from uhelp.views.users import loggedUserUid 786344400


@requires_auth
@api_route('/system/rebuildindex', methods=['GET'])
def rebuildIndex():
    rebuildLookIndex()
    rebuildUsersIndex()
    return 1


def createLooksSchema():
    schema = Schema(look_descr=TEXT(stored=True), look_date=DATETIME(sortable=True), look_score=NUMERIC(sortable=True), public=BOOLEAN, categories=TEXT(stored=False), look_id=ID(stored=True, unique=True))
    create_in(looksindex_dir, schema)


def rebuildLookIndex():
    createLooksSchema()
    lix = open_dir(looksindex_dir)
    writer = AsyncWriter(lix)

    looks_cnt = rs.scard("looks_ids")
    offset = 0
    from uhelp.views.looks import getLooksArrBySet
    while offset < looks_cnt + 20:
        looks = getLooksArrBySet("looks_ids", None, offset, 20)
        print "offset= ", offset
        for l in looks:
            storeLookInIndex(l, writer)
        offset += 20
    writer.commit()


def storeLookInIndex(l, writer=None, update=False):
    commit = False
    if writer is None:
        writer = AsyncWriter(lix)
        commit = True
    score = int(l.get('create_date') / 84600)
    categories = rs.smembers("look:" + str(l.get('id')) + ":categories")
    categories = u"_%s_" % u"_".join([k for k in categories])
    args = {"look_descr": "%s %s" % (l.get("title") or u"", l.get('descr') or u""), "look_date": datetime.datetime.fromtimestamp(l.get('create_date')),\
     "look_score": score, "public": l.get('is_public'), "look_id": unicode(l.get('id')), "categories": categories,}
    if not update:
        writer.add_document(**args)
    else:
        writer.update_document(**args)
    if commit:
        writer.commit()


def validate_indexes():
    from uhelp.views.looks import getLooksArrBySet
    writer = AsyncWriter(lix)
    looks_cnt = rs.scard("whoosh:looks:added")
    offset = 0
    while offset < looks_cnt + 20:
        looks = getLooksArrBySet("whoosh:looks:added", None, 0, 20)
        for l in looks:
            storeLookInIndex(l, writer)
            rs.srem("whoosh:looks:added", l["id"])
        offset += 20
    looks_cnt = rs.scard("whoosh:looks:updated")
    offset = 0
    while offset < looks_cnt + 20:
        looks = getLooksArrBySet("whoosh:looks:updated", None, 0, 20)
        for l in looks:
            storeLookInIndex(l, writer, True)
            rs.srem("whoosh:looks:updated", l["id"])
        offset += 20
    looks = rs.smembers("whoosh:looks:deleted")
    for l in looks:
        writer.delete_by_term("look_id", l)
        rs.srem("whoosh:looks:deleted", l)
    writer.commit()


@api_route('/system/index_look/<int:lid>/delete', methods=['GET'])
def delLookFromIndex(lid):
    #query = QueryParser("", lix.schema).parse("look_id:" + str(lid))
    writer = AsyncWriter(lix)
    writer.delete_by_term("look_id", str(lid))
    writer.commit()


def createUsersSchema():
    schema = Schema(name=TEXT(stored=True), birthday=DATETIME(sortable=True, stored=True), user_id=NUMERIC(stored=True, unique=True, sortable=True))
    create_in(usersindex_dir, schema)


def rebuildUsersIndex():
    createUsersSchema()
    uix = open_dir(usersindex_dir)
    writer = AsyncWriter(uix)

    users = rs.keys("users:*")
    users = rs.mget(users)
    for u in users:
        u = json.loads(u)
        storeUserInIndex(u, writer)
    writer.commit()


def storeUserInIndex(u, writer=None):
    commit = False
    if writer is None:
        writer = AsyncWriter(uix)
        commit = True
    writer.add_document(name=u.get('name'), birthday=datetime.datetime.fromtimestamp(u.get('birthday')), user_id=u.get('id'))
    if commit:
        writer.commit()


@app.route('/system/search/look', methods=['GET'])
def testlook():
    looks = searchlook._original()
    response = []
    for i in range(0, len(looks)):
        l = looks[i]
        response.append("<tr><td>" + str(l['id']) + ".</td><td><image src='/media/" + l['user']['avatar'] + "_m.jpg'/></br>"
                + l['user']["name"] + "</td>"
                + "<td><li/><b>" + (l['title'] or "") + "</b><br/>"
                + "<li/>" + (l['descr'] or "") + "<br/>"
                + "".join(["<image src='/media/" + img + "_s.jpg'/>" for img in l["images"]]) + "</td></tr>")
    return "<table>" + "".join(response) + "</table>"


@api_route('/look/search', methods=['GET'])
def searchlook():
    q = request.args.get("q", "").strip()  # repr
    re.sub("[^A-Za-z0-9]", " ", q)
    cat_id = request.args.get("category_id", '0')
    if len(q) == 0:
        from uhelp.views.looks import getCategoryLooks
        return getCategoryLooks._original(int(cat_id))
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 2000))
    with lix.searcher() as searcher:
        query = QueryParser("", lix.schema).parse(" AND ".join(["look_descr:*%s*" % _q for _q in q.split()]))  # QueryParser("name", ix.schema).parse("tash*")
        if int(cat_id) > 0:
            query = And([Wildcard(u"categories", "*_%s_*" % cat_id), query])
        query = And([Term('public', True), query])
        #print query
        #myfacet = sorting.FieldFacet("look_id", maptype=sorting.Count)
        look_score = sorting.FieldFacet("look_score", reverse=True)
        results = searcher.search_page(query, offset + 1, pagelen=count, sortedby=look_score)
        if results.offset / count < offset:
            return []
        lua = """local searched = loadstring('return ' .. KEYS[1])()
for i = 1, table.getn(searched) do
    redis.call('sadd', KEYS[2], tostring(searched[i]))
end
return 0"""
        tmp = hashlib.md5(str(mktime(datetime.datetime.now().timetuple()))).hexdigest() + "look_search_tmp"
        rs.eval(lua, 2, '{' + ','.join(str(hit['look_id']) for hit in results) + '}', tmp)
        from uhelp.views.looks import getLooksArrBySet
        looks = getLooksArrBySet(tmp, None, 0, count)
        rs.delete(tmp)
        return looks


@api_route('/system/search/user', methods=['GET'])
def testuser():
    q = request.args.get("q", "")  # repr
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 20))
    with uix.searcher() as searcher:
        query = QueryParser("name", uix.schema).parse("name:*%s*" % q)  # QueryParser("name", ix.schema).parse("tash*")
        #print query
        user_id = sorting.FieldFacet("user_id", reverse=True)
        results = searcher.search_page(query, offset + 1, pagelen=count, sortedby=user_id)
        r = "\n".join([str(hit['user_id']) + " " + hit['name'] for hit in results])
    return r


@api_route('/user/search', methods=['GET'], jsondump=False)
def searchuser():
    q = request.args.get("q", "")  # repr
    offset = int(request.args.get("offset", 0))
    count = int(request.args.get("count", 20))
    with uix.searcher() as searcher:
        query = QueryParser("name", uix.schema).parse("name:*%s*" % q)  # QueryParser("name", ix.schema).parse("tash*")
        #print query
        user_id = sorting.FieldFacet("user_id", reverse=True)
        results = searcher.search_page(query, offset + 1, pagelen=count, sortedby=user_id)
        if results.offset / count < offset:
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


looksindex_dir = app.config['UPLOAD_FOLDER'] + "whoosh/looks"
if not os.path.exists(looksindex_dir):
    os.makedirs(looksindex_dir)
    createLooksSchema()
lix = open_dir(looksindex_dir)
usersindex_dir = app.config['UPLOAD_FOLDER'] + "whoosh/users"
if not os.path.exists(usersindex_dir):
    os.makedirs(usersindex_dir)
    createUsersSchema()
uix = open_dir(usersindex_dir)