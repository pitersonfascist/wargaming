# -*- coding: utf-8 -*-
import feedparser
import urllib2
from BeautifulSoup import BeautifulSoup
import calendar
import re

tv24_category_id = 799


def read_news():
    du = feedparser.parse('http://24tv.ua/rss/tag/1119.xml')

    from uhelp.views.looks import getLooksArrBySet
    looks = getLooksArrBySet("category:%d:looks" % tv24_category_id, None, 0, 1)
    last_create = looks[0]['create_date'] if len(looks) > 0 else 0

    for uentry in du.entries:
        #locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        # datetime.datetime.strptime(uentry.pubDate[:-6], "%a, %d %b %Y %H:%M:%S")
        if last_create > calendar.timegm(uentry['published_parsed']):
            break
        page = urllib2.urlopen(uentry.link)
        soup = BeautifulSoup(page)
        kvarg = {}
        kvarg['class'] = "news-text"
        p = re.compile('\?.*')
        look = {"is_public": True, "category_id": tv24_category_id}
        for incident in soup('div', **kvarg):  # ="first text-page">
            look["descr"] = incident.p.string if incident.p is not None else u""
        images = []
        for incident in soup("div", id="newsPhotoItems"):
            images = [p.sub('', img["src"]).replace("100x75_DIR", "640x480_DIR") for img in incident.findAll("img")]
        for incident in soup('h3', **kvarg):  # ="first text-page">
            look["descr"] = incident.string
        for incident in soup("div", style="width:420px;height:315px;"):
            images.extend([p.sub('', img["src"]) for img in incident.findAll("img")])
        look["image_urls"] = images
        look["title"] = uentry.title
        look["source"] = uentry.link
        from uhelp.views.looks import create_look
        create_look(7, look)


