import errno
import sys
import time
import traceback
import mimetools
from datetime import datetime
import gevent
#from gevent.http import HTTPServer
from gevent.hub import GreenletExit
import logging
import logging.handlers
#import gevent.pywsgi#  WSGIHand
#from gevent.pywsgi import *
from geventwebsocket.handler import WebSocketHandler
import hashlib
 

MAX_REQUEST_LINE = 8192
# Weekday and month names for HTTP date/time formatting; always English!
_WEEKDAYNAME = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHNAME = [None,  # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_INTERNAL_ERROR_STATUS = '500 Internal Server Error'
_INTERNAL_ERROR_BODY = 'Internal Server Error'
_INTERNAL_ERROR_HEADERS = [('Content-Type', 'text/plain'),
                           ('Connection', 'close'),
                           ('Content-Length', str(len(_INTERNAL_ERROR_BODY)))]
_REQUEST_TOO_LONG_RESPONSE = "HTTP/1.0 414 Request URI Too Long\r\nConnection: close\r\nContent-length: 0\r\n\r\n"
_BAD_REQUEST_RESPONSE = "HTTP/1.0 400 Bad Request\r\nConnection: close\r\nContent-length: 0\r\n\r\n"
_CONTINUE_RESPONSE = "HTTP/1.1 100 Continue\r\n\r\n"

# The policy that is sent to the clients.
POLICY = """<cross-domain-policy><allow-access-from domain="*" to-ports="*" /></cross-domain-policy>\0"""
 
# The string the client has to send in order to receive the policy.
POLICYREQUEST = "<policy-file-request"


class TlsSMTPHandler(logging.handlers.SMTPHandler):

    msgs = {}

    def emit(self, record):
        """
        Emit a record.
 
        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            import string # for tls add this line
            try:
                from email.utils import formatdate
            except ImportError:
                formatdate = self.date_time
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            msg = self.format(record)
            requestline = msg.split('\n')[0]
            h = hashlib.md5(requestline).hexdigest()
            if self.msgs.get(h) is None:
                self.msgs[h] = 1
            else:
                return
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                            self.fromaddr,
                            string.join(self.toaddrs, ","),
                            self.getSubject(record),
                            formatdate(), msg)
            if self.username:
                smtp.ehlo() # for tls add this line
                smtp.starttls() # for tls add this line
                smtp.ehlo() # for tls add this line
                smtp.login(self.username, self.password)
            #smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            pass
        except:
            self.handleError(record)


class CustomWSGIHandler(WebSocketHandler):
    
    msgs = {}
    
    def __init__(self, socket, address, server, rfile=None):
        super(CustomWSGIHandler, self).__init__(socket, address, server, rfile)
        gm = TlsSMTPHandler(("smtp.rambler.ru", 587), 'gamer_blin@rambler.ru', ['ievgeniip@gmail.com'], 'Wargaming service Error', ('gamer_blin@rambler.ru', 'agafochka'))
        gm.setLevel(logging.ERROR)
        #self.logger = logging.getLogger()
        self.logger.addHandler(gm)

    def handle_error(self, type, value, tb):
        if not issubclass(type, GreenletExit):
            requestline = getattr(self, 'requestline', '')
            self.server.loop.handle_error(self.environ, type, value, tb)
            self.logger.exception(requestline)
            #h = hashlib.md5(requestline).hexdigest()
            #if self.msgs.get(h) is None:
                #self.msgs[h] = 1
                #self.logger.exception(requestline)
                ##self.wsgi_input._discard()
                ##sys.exc_clear()
        del tb
        if self.response_length:
            self.close_connection = True
        else:
            self.start_response(_INTERNAL_ERROR_STATUS, _INTERNAL_ERROR_HEADERS[:])
            self.write(_INTERNAL_ERROR_BODY)

#logger = logging.getLogger()
 
#gm = TlsSMTPHandler(("smtp.gmail.com", 587), 'bugs@theulook.com', ['ievgeniip@gmail.com'], 'uError found!', ('ievgeniip@gmail.com', 'afibcn13'))
#gm = TlsSMTPHandler(("smtp.rambler.ru", 587), 'gamer_blin@rambler.ru', ['ievgeniip@gmail.com'], 'ULook Crash message', ('gamer_blin@rambler.ru', 'agafochka'))
#gm.setLevel(logging.ERROR)
 
#logger.addHandler(gm)
 
#try:
#    1/0
#except:
#    logger.exception('FFFFFFFFFFFFFFFFFFFFFFFUUUUUUUUUUUUUUUUUUUUUU-') 
