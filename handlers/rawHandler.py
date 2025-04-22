from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *
import os

class handler(tornado.web.RequestHandler):
    async def get(self, file: str):
        try:
            request_msg(self)
            try: IDM(self, f"data/{file}")
            except FileNotFoundError: send404(self, [i for i in os.listdir("data") if file in i])
        finally: self.set_header("Ping", str(resPingMs(self)))