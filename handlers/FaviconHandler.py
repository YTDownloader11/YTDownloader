from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *

class handler(tornado.web.RequestHandler):
    async def get(self):
        request_msg(self)
        self.set_header('Content-Type', pathToContentType("static/img/favicon.ico")["Content-Type"])
        with open("static/img/favicon.ico", 'rb') as f: self.write(f.read())
        self.set_header("Ping", str(resPingMs(self)))