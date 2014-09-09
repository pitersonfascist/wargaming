# -*- coding: utf-8 -*-
import feedparser
import urllib2
from BeautifulSoup import BeautifulSoup
import calendar

tsn_category_id = 794


def read_news():
    du = feedparser.parse('http://tsn.ua/rss')

    from uhelp.views.looks import getLooksArrBySet
    looks = getLooksArrBySet("category:%d:looks" % tsn_category_id, None, 0, 1)
    last_create = looks[0]['create_date'] if len(looks) > 0 else 0

    for uentry in du.entries:
        #locale.setlocale(locale.LC_ALL, 'en_US.utf8')
        # datetime.datetime.strptime(uentry.pubDate[:-6], "%a, %d %b %Y %H:%M:%S")
        if last_create > calendar.timegm(uentry['published_parsed']):
            break
        page = urllib2.urlopen(uentry.link)
        soup = BeautifulSoup(page)
        kvarg = {}
        kvarg['class'] = "news_text"
        for incident in soup('div', **kvarg):  # ="first text-page">
            #218xX -> original
            look = {"is_public": True, "category_id": tsn_category_id}
            look["image_urls"] = [tag.get('src').replace("218xX", "original") for tag in incident.findAll('img')]
            look["title"] = uentry.title
            look["source"] = uentry.link
            #look["short_descr"] = incident.p.string
            if incident.span is not None:
                look["descr"] = incident.span.string
            #"\n".join([tag.string or "" for tag in incident.findAll('p')])
            from uhelp.views.looks import create_look
            create_look(8, look)

