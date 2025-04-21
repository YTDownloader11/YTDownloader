import os
from dotenv import load_dotenv

#other
OSisWindows = os.name == "nt"

def envchk():
    if not os.path.isfile(".env"):
        if OSisWindows: os.system('copy ".env copy" .env && notepad .env')
        else: os.system('sudo cp ".env copy" .env && sudo vim .env')
        exit()

try: #.env
    load_dotenv()
    domain = os.getenv("domain")
    port = int(os.getenv("port"))
    mmdbID = os.getenv("mmdbID")
    mmdbKey = os.getenv("mmdbKey")
    debug = eval(os.getenv("debug"))
except: envchk()

#job
job_status_map = {} #job_id -> {"status": "pending" | "done" | "error", "result": ...}