import os
from dotenv import load_dotenv

#other
OSisWindows = os.name == "nt"

#job
job_status_map = {}

def envchk():
    if not os.path.isfile(".env"):
        if OSisWindows: os.system('copy ".env copy" .env && notepad .env')
        else: os.system('sudo cp ".env copy" .env && sudo vim .env')
        exit()

try: #.env
    load_dotenv(override=True)
    domain = os.getenv("domain")
    port = int(os.getenv("port"))
    mmdbID = os.getenv("mmdbID")
    mmdbKey = os.getenv("mmdbKey")
    autoDelete = eval(os.getenv("autoDelete"))
    debug = eval(os.getenv("debug"))
    isfixWithMsg = eval(os.getenv("isfixWithMsg"))
    isfix = any(isfixWithMsg)
except: envchk()