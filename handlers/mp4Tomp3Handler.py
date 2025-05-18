from helpers import logUtils as log
import traceback
import tornado.web
import asyncio
from helpers import config
from functions import *
import uuid

class handler(tornado.web.RequestHandler):
    async def get(self):
        request_msg(self)
        self.render("mp4tomp3.html", domain=config.domain, today=localtime())
        self.set_header("Ping", str(resPingMs(self)))

    async def post(self):
        try:
            request_msg(self)

            form = self.request.files.get("file", [])[0]
            isdl = int(self.get_body_argument("isdl", 0))
            bitrate = self.get_body_argument("bitrate", None)
            samplerate = self.get_body_argument("samplerate", None)
            channels = self.get_body_argument("channels", None)
            volume = self.get_body_argument("volume", None)
            with open(f'data/{form["filename"]}', 'wb') as f: f.write(form["body"])

            #FFmpeg 명령어 구성
            ex_cmd = ""
            if bitrate and re.match(r'^\d+k$', bitrate): ex_cmd += f"-b:a {bitrate} "
            if samplerate and samplerate.isdigit(): ex_cmd += f"-ar {samplerate} "
            if channels:
                try:
                    if float(channels) == 2.1: channels = 3
                    elif float(channels) == 5.1: channels = 6
                    elif float(channels) == 6.1: channels = 7
                    elif float(channels) == 7.1: channels = 8
                    ex_cmd += f"-ac {channels} "
                except: pass
            if volume and volume.isdigit(): ex_cmd += f"-filter:a volume={int(volume)/100} "

            job_id = str(uuid.uuid4()) #job_id 생성
            config.job_status_map[job_id] = {"status": "pending", "result": None, "progress": 0}
            self.write({"job_id": job_id, "url": f"https://{config.domain}/job_status?id={job_id}"}) #클라이언트에게 job_id 반환
            self.finish()

            async def background_task(): #백그라운드 작업 수행
                try:
                    result = await asyncio.to_thread(mp4Tomp3, f"data/{form["filename"]}", ex_cmd, job_id)
                    config.job_status_map[job_id] = {"status": "done", "result": f"https://{config.domain}/raw/{result}?dl={isdl}", "progress": 100}
                except Exception as e:
                    config.job_status_map[job_id] = {"status": "error", "result": str(e), "progress": -1}
            asyncio.create_task(background_task())
        finally: self.set_header("Ping", str(resPingMs(self)))