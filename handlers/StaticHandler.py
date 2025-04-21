from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *

class handler(tornado.web.RequestHandler):
    async def get(self, item):
        request_msg(self)
        self.set_header("Content-Type", pathToContentType(item)["Content-Type"])
        with open(f"static/{item}", 'rb') as f: self.write(f.read())
        self.set_header("Ping", str(resPingMs(self)))