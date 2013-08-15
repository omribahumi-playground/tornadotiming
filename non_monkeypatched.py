#!/usr/bin/python
import tornado
import tornado.ioloop
import tornado.web
import tornado.gen
import datetime
import time
import tornadotiming
import logging

logging.basicConfig(level=logging.DEBUG)

class MainHandler(tornadotiming.TimingRequestHandler):
    @tornadotiming.coroutine
    def get(self):
        for i in xrange(0, 10):
            yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, datetime.timedelta(milliseconds=1000))
            if i == 5:
                time.sleep(2)
            self.write("Hello, world\r\n")
            self.flush()

    def post(self):
        for i in xrange(0, 10):
            self.write("Hello, world\r\n")
            self.flush()
            time.sleep(1)

application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
