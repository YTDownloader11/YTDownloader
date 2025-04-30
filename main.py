import os
import traceback
import tornado.ioloop
import tornado.web
from helpers import logUtils as log
from helpers import config
from helpers import getmmdb

from functions import *
from handlers import MainHandler, FaviconHandler, StaticHandler, robots_txt, IDHandler, JobStatusHandler, rawHandler

def exceptionE(msg=""): e = traceback.format_exc(); log.error(f"{msg} \n{e}"); return e

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler.handler),
        (r"/(?:shorts/)?([\w-]{11})", IDHandler.handler),
        (r"/watch", IDHandler.handler),
        (r"/job_status", JobStatusHandler.handler),
        (r"/raw/data/(.*)", rawHandler.handler),

        (r"/favicon.ico", FaviconHandler.handler),
        (r"/static/(.*)", StaticHandler.handler),
        (r"/robots.txt", robots_txt.handler),
    ],
    template_path="templates",
    debug=config.debug)

if __name__ == "__main__":
    getmmdb.dl()
    folder_check(); autoDel()
    app = make_app()
    app.listen(config.port)
    log.info(f"Server Listen on http://localhost:{config.port} Port | OS = {'Windows' if config.OSisWindows else 'UNIX'}")
    tornado.ioloop.IOLoop.current().start()