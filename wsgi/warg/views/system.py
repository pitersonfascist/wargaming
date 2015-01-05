from warg import api_route, app, requires_auth
from warg.views import rs
import os


@requires_auth
@api_route('/empty/sessions')
def emptySessions():
    ussids = rs.keys("ussid:*")
    for ussid in ussids:
        rs.delete(ussid)
    return 1


@requires_auth
@api_route('/empty/db')
def emptyRedis():
    return str(rs.flushall())


@api_route('/system/info')
def systemInfo():
    info = rs.info()
    lua = """local r1 = redis.call('keys', 'users:*');
return table.getn(r1);"""
    stat = {"users": rs.eval(lua, 0) - rs.scard("users:virtual")}
    #users = rs.keys("users:*")
    stat["battles"] = rs.zcard("battles_ids")
    stat["groups"] = rs.zcard("group_ids")
    stat["clans"] = rs.zcard("clan_ids")
    stat["online"] = rs.scard("users_online")
    stat["max_online"] = rs.get("stat:max_online")
    stat["disk_usage"] = getFolderSize(app.config['UPLOAD_FOLDER'])
    stat["redis_usage"] = info['used_memory_human']
    #print "SYSTEM: ", os.popen("du -hs " + app.config['UPLOAD_FOLDER']).read().split()[0]
    return stat


def getFolderSize(folder):
    return os.popen("du -hs " + app.config['UPLOAD_FOLDER']).read().split()[0]
    #total_size = os.path.getsize(folder)
    #for item in os.listdir(folder):
        #itempath = os.path.join(folder, item)
        #if os.path.isfile(itempath):
            #total_size += os.path.getsize(itempath)
        #elif os.path.isdir(itempath):
            #total_size += getFolderSize(itempath)
    #return total_size


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0