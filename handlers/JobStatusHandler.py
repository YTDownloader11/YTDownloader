from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *

class handler(tornado.web.RequestHandler):
    def get(self):
        job_id = self.get_argument("id", None)
        if not job_id or job_id not in config.job_status_map:
            self.set_status(404); self.write({"error": "job_id not found"})
            return
        self.write(config.job_status_map[job_id])
