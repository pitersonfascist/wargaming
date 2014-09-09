# -*- coding: utf-8 -*-
import feedparser
import urllib2
from BeautifulSoup import BeautifulSoup
import calendar

espresso_category_id = 795


def read_news():
    du = feedparser.parse('http://espreso.tv/rss')

    from uhelp.views.looks import getLooksArrBySet
    looks = getLooksArrBySet("category:%d:looks" % espresso_category_id, None, 0, 1)
    last_create = looks[0]['create_date'] if len(looks) > 0 else 0

    for uentry in du.entries:
        #locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        # datetime.datetime.strptime(uentry.pubDate[:-6], "%a, %d %b %Y %H:%M:%S")
        #print last_create, calendar.timegm(uentry['published_parsed']), last_create - calendar.timegm(uentry['published_parsed'])
        if last_create > calendar.timegm(uentry['published_parsed']):
            break
        page = urllib2.urlopen(uentry.link)
        soup = BeautifulSoup(page)
        kvarg = {}
        kvarg['class'] = "photo-wrap"
        images = []
        for incident in soup('div', **kvarg):  # ="first text-page">
            images = ["http://espreso.tv" + tag.get('src') for tag in incident.findAll('img')]
        kvarg['class'] = "first text-page"
        for incident in soup('div', **kvarg):  # ="first text-page">
            look = {"is_public": True, "category_id": espresso_category_id}
            images.extend([tag.get('src') for tag in incident.findAll('img')])
            look["image_urls"] = images
            look["title"] = uentry.title
            look["source"] = uentry.link
            #look["short_descr"] = incident.p.string
            look["descr"] = incident.p.string
            #"\n".join([tag.string or "" for tag in incident.findAll('p')])
            from uhelp.views.looks import create_look
            create_look(6, look)
