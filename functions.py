import os
import shutil
import re
import time
from datetime import datetime
import json
import traceback
import threading
from helpers import logUtils as log
from helpers import config
import geoip2.database
from yt_dlp import YoutubeDL

def exceptionE(msg=""): e = traceback.format_exc(); log.error(f"{msg} \n{e}"); return e

def getIP(self):
    if "X-Real-IP" in self.request.headers: return self.request.headers.get("X-Real-IP") #Added from nginx
    elif "CF-Connecting-IP" in self.request.headers: return self.request.headers.get("CF-Connecting-IP")
    elif "X-Forwarded-For" in self.request.headers: return self.request.headers.get("X-Forwarded-For")
    else: return self.request.remote_ip

def IPtoFullData(IP): #전체 정보를 가져오기 위한 코드
    reader = geoip2.database.Reader("GeoLite2-City.mmdb")
    try:
        res = reader.city(IP)
        data = {
            "ip": IP,
            "city": res.city.name,
            "region": res.subdivisions.most_specific.name,
            "country": res.country.iso_code,
            "country_full": res.country.name,
            "continent": res.continent.code,
            "continent_full": res.continent.name,
            "loc": f"{res.location.latitude},{res.location.longitude}",
            "postal": res.postal.code if res.postal.code else ""
        }
    except geoip2.errors.AddressNotFoundError:
        data = {
            "ip": IP, "city": "Unknown", "region": "Unknown", "country": "XX", "country_full": "Unknown", "continent": "Unknown", "continent_full": "Unknown", "loc": "Unknown", "postal": "Unknown"
        }
        log.error(f"주어진 IP 주소 : {IP} 를 찾을 수 없습니다.")
    except:
        data = {
            "ip": IP, "city": "Unknown", "region": "Unknown", "country": "XX", "country_full": "Unknown", "continent": "Unknown", "continent_full": "Unknown", "loc": "Unknown", "postal": "Unknown"
        }
        exceptionE("국가코드 오류 발생")
    finally: reader.close()
    return data

def getRequestInfo(self):
    IsCloudflare = IsNginx = IsHttp = False
    real_ip = getIP(self)
    try:
        request_url = self.request.headers["X-Forwarded-Proto"] + "://" + self.request.host + self.request.uri
        country_code = self.request.headers["Cf-Ipcountry"]
        IsCloudflare = IsNginx = True
        Server = "Cloudflare"
    except Exception as e:
        log.warning(f"cloudflare를 거치지 않음, real_ip는 nginx header에서 가져옴 | e = {e}")
        try:
            request_url = self.request.headers["X-Forwarded-Proto"] + "://" + self.request.host + self.request.uri
            IsNginx = True
            if config.OSisWindows:
                try: Server = os.popen("nginx.exe -v 2>&1").read().split(":")[1].strip()
                except: ngp = os.getcwd().replace(os.getcwd().split("\\")[-1], "nginx/nginx.exe").replace("\\", "/"); Server = os.popen(f'{ngp} -v 2>&1').read().split(":")[1].strip()
            else: Server = os.popen("nginx -v 2>&1").read().split(":")[1].strip()
        except Exception as e:
            log.warning(f"http로 접속시도함 | cloudflare를 거치지 않음, real_ip는 http 요청이라서 바로 뜸 | e = {e}")
            request_url = self.request.protocol + "://" + self.request.host + self.request.uri
            IsHttp = True
            Server = self._headers.get("Server")
        country_code = IPtoFullData(real_ip)["country"]
    client_ip = self.request.remote_ip
    try: User_Agent = self.request.headers["User-Agent"]
    except: User_Agent = ""; log.error("User-Agent 값이 존재하지 않음!")
    try: Referer = self.request.headers["Referer"]; log.info("Referer 값이 존재함!")
    except: Referer = ""
    return real_ip, request_url, country_code, client_ip, User_Agent, Referer, IsCloudflare, IsNginx, IsHttp, Server

def request_msg(self):
    print("")
    real_ip, request_url, country_code, client_ip, User_Agent, Referer, IsCloudflare, IsNginx, IsHttp, Server = getRequestInfo(self)
    log.info(f"Request from IP: {real_ip}, {client_ip} ({country_code}) | URL: {request_url} | From: {User_Agent} | Referer: {Referer}")

def resPingMs(self):
    pingMs = (time.time() - self.request._start_time) * 1000
    log.chat(f"{pingMs} ms")
    return pingMs

def send404(self, fileLists: list):
    self.set_status(404); self.set_header("Content-Type", "text/html")
    self.render("404.html", fileLists=fileLists)
    self.set_header("Ping", str(resPingMs(self)))

def send429(self, ttl: int):
    self.set_status(429); self.set_header("Content-Type", "text/html")
    self.render("429.html", ttl=ttl)
    self.set_header("Ping", str(resPingMs(self)))

IDMConnects = {}
def IDM22(self, path):
    IP = getIP(self)
    filename = path.split("/")[-1]
    self.set_header('Content-Type', pathToContentType(path)["Content-Type"])
    self.set_header('Content-Disposition', f'inline; filename="{filename}"')
    self.set_header("Accept-Ranges", "bytes")
    if "Range" in self.request.headers:
        IDMConnects[IP] = 1 if not IDMConnects.get(IP) else IDMConnects[IP] + 1
        log.debug(f"IDMConnects[{IP}] = {IDMConnects[IP]} | {type(IDMConnects[IP])}")
        if IDMConnects[IP] > 16: send429(self, -1); return False
        idm = True
        log.info("분할 다운로드 활성화!")
        Range = self.request.headers["Range"].replace("bytes=", "").split("-")
        fileSize = os.path.getsize(path)
        start = int(Range[0])
        end = fileSize - 1 if not Range[1] else int(Range[1])
        contentLength = end - start + 1

        log.info({"Content-Range": f"bytes {start}-{end}/{fileSize}", "Content-Length": contentLength})
        self.set_status(206) if start != 0 or (start == 0 and Range[1]) else self.set_status(200)
        self.set_header("Content-Length", contentLength)
        self.set_header("Content-Range", f"bytes {start}-{end}/{fileSize}")
        with open(path, "rb") as f:
            f.seek(start); self.write(f.read(contentLength) if start != 0 or (start == 0 and Range[1]) else f.read())
        if IDMConnects[IP] > 1: IDMConnects[IP] -= 1
        else: del IDMConnects[IP]
    else:
        idm = False
        with open(path, 'rb') as f: self.write(f.read())
    return idm
def IDM(self, path, dl = 0):
    IP = getIP(self)
    chunk_size = 1024 * 1024 # MB 청크
    filename = path.split("/")[-1]
    self.set_header('Content-Type', pathToContentType(path)["Content-Type"])
    dl = "inline" if not dl else "attachment"
    self.set_header('Content-Disposition', f'{dl}; filename="{filename}"')
    self.set_header("Accept-Ranges", "bytes")
    if "Range" in self.request.headers:
        IDMConnects[IP] = 1 if not IDMConnects.get(IP) else IDMConnects[IP] + 1
        log.debug(f"IDMConnects[{IP}] = {IDMConnects[IP]} | {type(IDMConnects[IP])}")
        if IDMConnects[IP] > 16: send429(self, -1); return False
        idm = True
        log.info("분할 다운로드 활성화!")
        Range = self.request.headers["Range"].replace("bytes=", "").split("-")
        fileSize = os.path.getsize(path)
        start = int(Range[0])
        end = fileSize - 1 if not Range[1] else int(Range[1])
        contentLength = end - start + 1

        log.info({"Content-Range": f"bytes {start}-{end}/{fileSize}", "Content-Length": contentLength})
        self.set_status(206) if start != 0 or (start == 0 and Range[1]) else self.set_status(200)
        self.set_header("Content-Length", contentLength)
        self.set_header("Content-Range", f"bytes {start}-{end}/{fileSize}")
        with open(path, "rb") as f:
            f.seek(start)
            while start <= end:
                chunk = f.read(min(chunk_size, contentLength))
                self.write(chunk)
                start += len(chunk)
                if start > end: break
            self.finish() #모든 데이터 전송 후 종료
        if IDMConnects[IP] > 1: IDMConnects[IP] -= 1
        else: del IDMConnects[IP]
    else:
        idm = False
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk: break
                self.write(chunk)
            self.finish()
    return idm

def pathToContentType(path, isInclude=False):
    if path == 0: return None
    fn, fe = os.path.splitext(os.path.basename(path));
    ffln = path.replace(f"/{path.split('/')[-1]}", "")
    fln = os.path.splitext(os.path.basename(ffln.split('/')[-1]))[0]
    if config.OSisWindows:
        while fln.endswith("."): fln = fln[:-1]

    if isInclude and ".aac" in path.lower() or not isInclude and path.lower().endswith(".aac"): ct, tp = ("audio/aac", "audio")
    elif isInclude and ".apng" in path.lower() or not isInclude and path.lower().endswith(".apng"): ct, tp = ("image/apng", "image")
    elif isInclude and ".avif" in path.lower() or not isInclude and path.lower().endswith(".avif"): ct, tp = ("image/avif", "image")
    elif isInclude and ".avi" in path.lower() or not isInclude and path.lower().endswith(".avi"): ct, tp = ("video/x-msvideo", "video")
    elif isInclude and ".bin" in path.lower() or not isInclude and path.lower().endswith(".bin"): ct, tp = ("application/octet-stream", "file")
    elif isInclude and ".css" in path.lower() or not isInclude and path.lower().endswith(".css"): ct, tp = ("text/css", "file")
    elif isInclude and ".gif" in path.lower() or not isInclude and path.lower().endswith(".gif"): ct, tp = ("image/gif", "image")
    elif isInclude and ".html" in path.lower() or not isInclude and path.lower().endswith(".html"): ct, tp = ("text/html", "file")
    elif isInclude and ".ico" in path.lower() or not isInclude and path.lower().endswith(".ico"): ct, tp = ("image/x-icon", "image")
    elif isInclude and ".jfif" in path.lower() or not isInclude and path.lower().endswith(".jfif"): ct, tp = ("image/jpeg", "image")
    elif isInclude and ".jpeg" in path.lower() or not isInclude and path.lower().endswith(".jpeg"): ct, tp = ("image/jpeg", "image")
    elif isInclude and ".jpg" in path.lower() or not isInclude and path.lower().endswith(".jpg"): ct, tp = ("image/jpeg", "image")
    elif isInclude and ".js" in path.lower() or not isInclude and path.lower().endswith(".js"): ct, tp = ("text/javascript", "file")
    elif isInclude and ".json" in path.lower() or not isInclude and path.lower().endswith(".json"): ct, tp = ("application/json", "file")
    elif isInclude and ".mp3" in path.lower() or not isInclude and path.lower().endswith(".mp3"): ct, tp = ("audio/mpeg", "audio")
    elif isInclude and ".mp4" in path.lower() or not isInclude and path.lower().endswith(".mp4"): ct, tp = ("video/mp4", "video")
    elif isInclude and ".mpeg" in path.lower() or not isInclude and path.lower().endswith(".mpeg"): ct, tp = ("audio/mpeg", "audio")
    elif isInclude and ".oga" in path.lower() or not isInclude and path.lower().endswith(".oga"): ct, tp = ("audio/ogg", "audio")
    elif isInclude and ".ogg" in path.lower() or not isInclude and path.lower().endswith(".ogg"): ct, tp = ("application/ogg", "audio")
    elif isInclude and ".ogv" in path.lower() or not isInclude and path.lower().endswith(".ogv"): ct, tp = ("video/ogg", "video")
    elif isInclude and ".ogx" in path.lower() or not isInclude and path.lower().endswith(".ogx"): ct, tp = ("application/ogg", "audio")
    elif isInclude and ".opus" in path.lower() or not isInclude and path.lower().endswith(".opus"): ct, tp = ("audio/opus", "audio")
    elif isInclude and ".png" in path.lower() or not isInclude and path.lower().endswith(".png"): ct, tp = ("image/png", "image")
    elif isInclude and ".svg" in path.lower() or not isInclude and path.lower().endswith(".svg"): ct, tp = ("image/svg+xml", "image")
    elif isInclude and ".tif" in path.lower() or not isInclude and path.lower().endswith(".tif"): ct, tp = ("image/tiff", "image")
    elif isInclude and ".tiff" in path.lower() or not isInclude and path.lower().endswith(".tiff"): ct, tp = ("image/tiff", "image")
    elif isInclude and ".ts" in path.lower() or not isInclude and path.lower().endswith(".ts"): ct, tp = ("video/mp2t", "video")
    elif isInclude and ".txt" in path.lower() or not isInclude and path.lower().endswith(".txt"): ct, tp = ("text/plain", "file")
    elif isInclude and ".wav" in path.lower() or not isInclude and path.lower().endswith(".wav"): ct, tp = ("audio/wav", "audio")
    elif isInclude and ".weba" in path.lower() or not isInclude and path.lower().endswith(".weba"): ct, tp = ("audio/webm", "audio")
    elif isInclude and ".webm" in path.lower() or not isInclude and path.lower().endswith(".webm"): ct, tp = ("video/webm", "video")
    elif isInclude and ".webp" in path.lower() or not isInclude and path.lower().endswith(".webp"): ct, tp = ("image/webp", "image")
    elif isInclude and ".zip" in path.lower() or not isInclude and path.lower().endswith(".zip"): ct, tp = ("application/zip", "file")
    elif isInclude and ".flv" in path.lower() or not isInclude and path.lower().endswith(".flv"): ct, tp = ("video/x-flv", "video")
    elif isInclude and ".wmv" in path.lower() or not isInclude and path.lower().endswith(".wmv"): ct, tp = ("video/x-ms-wmv", "video")
    elif isInclude and ".mkv" in path.lower() or not isInclude and path.lower().endswith(".mkv"): ct, tp = ("video/x-matroska", "video")
    elif isInclude and ".mov" in path.lower() or not isInclude and path.lower().endswith(".mov"): ct, tp = ("video/quicktime", "video")

    elif isInclude and ".osz" in path.lower() or not isInclude and path.lower().endswith(".osz"): ct, tp = ("application/x-osu-beatmap-archive", "file")
    elif isInclude and ".osr" in path.lower() or not isInclude and path.lower().endswith(".osr"): ct, tp = ("application/x-osu-replay", "file")
    elif isInclude and ".osu" in path.lower() or not isInclude and path.lower().endswith(".osu"): ct, tp = ("application/x-osu-beatmap", "file")
    elif isInclude and ".osb" in path.lower() or not isInclude and path.lower().endswith(".osb"): ct, tp = ("application/x-osu-storyboard", "file")
    elif isInclude and ".osk" in path.lower() or not isInclude and path.lower().endswith(".osk"): ct, tp = ("application/x-osu-skin", "file")

    else: ct, tp = ("application/octet-stream", "?")
    return {"Content-Type": ct, "foldername": fln, "fullFoldername": ffln, "filename": fn, "extension": fe, "fullFilename": fn + fe, "type": tp, "path": path}

####################################################################################################

def folder_check(): os.makedirs("data", exist_ok=True)

def autoDel():
    def wk():
        while config.autoDelete:
            now = datetime.now()
            if now.weekday() == 0 and now.hour == 0:
                for d in os.listdir("data"):
                    try: os.remove(f"data/{d}"); log.info(f"data/{d} 삭제완료!")
                    except PermissionError: log.error(f"data/{d} 사용중임!")
                    except: exceptionE(f"data/{d}")
            time.sleep(1800)
    threading.Thread(target=wk).start()

#######################################################################################################################################

def localtime(): return time.localtime()

def getYTID(YTLink: str) -> str:
    YTURLPT = r"(https?://)?(www\.)?(m\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)(?P<YTID>[\w-]{11})"
    return re.match(YTURLPT, YTLink).group("YTID")

def getInfo(YTID: str) -> dict:
    with YoutubeDL({'quiet': True, 'cookies': 'cookies.txt'}) as ydl: info = ydl.extract_info(YTID, download=False)
    auInfo = 0; viInfo = {}
    for i in info.get('formats', []):
        if i["audio_ext"] == "mp4": auInfo = i['format_id']
        elif i["video_ext"] == "mp4": viInfo[str(i["height"])] = i["format_id"]
    return {
        "YTID": YTID,
        "YTURL": f"https://youtu.be/{YTID}",
        "viInfo": dict(reversed(viInfo.items())),
        "auInfo": auInfo,
        "duration": info.get('duration'),
        "title": f"{info.get('channel')} - {info.get('title')}",
        "thumb": info.get('thumbnail')
    }

def saveVideo(YTID: str, hei: int, info: dict, job_id: str) -> str:
    outtmpl = f'data/{YTID}-{hei}p.mp4'
    if os.path.isfile(outtmpl): config.job_status_map[job_id] = {"status": "done", "result": outtmpl, "progress": 100}; return outtmpl
    log.info(f"{outtmpl} 영상 다운로드 중...")
    """ def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            progress = int(downloaded * 100 / total)
            config.job_status_map[job_id] = {"status": "downloading", "result": None, "progress": progress}
        elif d['status'] == 'finished':
            config.job_status_map[job_id] = {"status": "processing", "result": None, "progress": 99} """
    
    # 다운로드 단계 추적용
    current_stage = {"step": "video"}
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            raw_progress = int(downloaded * 100 / total)
            if current_stage["step"] == "video": progress = int(raw_progress * 0.5)
            elif current_stage["step"] == "audio": progress = int(50 + raw_progress * 0.45)
            else: progress = 95
            config.job_status_map[job_id] = {"status": "downloading", "result": None, "progress": progress}

        elif d['status'] == 'finished':
            if current_stage["step"] == "video": current_stage["step"] = "audio"  # 다음 단계로 전환
            elif current_stage["step"] == "audio": config.job_status_map[job_id] = {"status": "processing", "result": None, "progress": 95}
    ydl_opts = {
        "nocheckcertificate": True,
        'format': f"{info['viInfo'][str(hei)]}+{info['auInfo']}",
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }],
        'progress_hooks': [progress_hook],
        'quiet': False,
        'cookies': 'cookies.txt'
    }
    with YoutubeDL(ydl_opts) as ydl: ydl.download(YTID)
    config.job_status_map[job_id] = {"status": "processing", "result": None, "progress": 99}
    return outtmpl

def saveAudio(YTID: str, info: dict, job_id: str) -> str:
    outtmpl = f'data/{YTID}.mp3'
    if os.path.isfile(outtmpl): return outtmpl
    log.info(f"{YTID} 음원 다운로드 중...")
    ydl_opts = {
        "nocheckcertificate": True,
        'format': info['auInfo'],
        'outtmpl': f'data/{YTID}',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'cookies': 'cookies.txt'
    }
    with YoutubeDL(ydl_opts) as ydl: ydl.download(YTID)
    return outtmpl