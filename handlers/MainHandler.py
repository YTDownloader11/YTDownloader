
from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *

class handler(tornado.web.RequestHandler):
    async def get(self):
        request_msg(self)
        self.render("index.html", domain=config.domain, today=localtime())
        self.set_header("Ping", str(resPingMs(self)))