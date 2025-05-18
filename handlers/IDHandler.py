from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *
import os
import json
import uuid

class handler(tornado.web.RequestHandler):
    async def get(self, ID1: str = None):
        try:
            request_msg(self)
            ID2 = self.get_argument("v", None)
            if not (ID1 or ID2): self.write("NO")
            info = await asyncio.to_thread(getInfo, ID1 or ID2)
            self.render("selector.html", domain=config.domain, today=localtime(), info=info, hei=info["viInfo"].keys(), info_json=json.dumps(info))
        finally: self.set_header("Ping", str(resPingMs(self)))

    async def post(self, ID1: str = None):
        try:
            request_msg(self)
            ID2 = self.get_argument("v", None)
            if not (ID1 or ID2): self.write("NO")
            hei = int(self.get_body_argument("hei"))
            info = json.loads(self.get_body_argument("info"))
            isdl = int(self.get_body_argument("isdl"))

            job_id = str(uuid.uuid4()) #job_id 생성
            config.job_status_map[job_id] = {"status": "pending", "result": None, "progress": 0}
            self.write({"job_id": job_id, "url": f"https://{config.domain}/job_status?id={job_id}"}) #클라이언트에게 job_id 반환
            self.finish()

            async def background_task(): #백그라운드 작업 수행
                try:
                    if hei: result = await asyncio.to_thread(saveVideo, ID1 or ID2, hei, info, job_id)
                    else: result = await asyncio.to_thread(saveAudio, ID1 or ID2, info, job_id)
                    config.job_status_map[job_id] = {"status": "done", "result": f"https://{config.domain}/raw/{result}?dl={isdl}", "progress": 100}
                except Exception as e:
                    config.job_status_map[job_id] = {"status": "error", "result": str(e), "progress": -1}
            asyncio.create_task(background_task())
        finally: self.set_header("Ping", str(resPingMs(self)))