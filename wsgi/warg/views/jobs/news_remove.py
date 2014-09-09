# -*- coding: utf-8 -*-
from uhelp.views import rs
from datetime import datetime
from time import mktime


def remove_old_news():
    oldnow = int(mktime(datetime.utcnow().timetuple())) - 5 * 24 * 3600
    from uhelp.views.looks import deleteLook
    rows = rs.sort("category:785:looks", by="look:*->create_date", get=['look:*->create_date', '#'])
    for i in range(0, len(rows) - 1):
        if i % 2 != 0 or rows[i] is None:
            continue
        if int(rows[i]) - oldnow > 0:
            break
        deleteLook._original(int(rows[i + 1]), 1)
