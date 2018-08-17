import os
import sys
import subprocess
import json

path = os.path.dirname(os.path.realpath(__file__))

def spawnAndWait(listObj):
    p = subprocess.Popen(listObj)
    p.wait()


with open(path+"/secret.json") as f:
    data = json.loads(f.read())
    user = data["git_user"]
    pw = data["git_pw"]

spawnAndWait(["git","-C",f"{path}", "pull" ,f"https://{user}:{pw}@github.com/muma7490/soccerbot.git","master"])
spawnAndWait([sys.executable,path+"/manage.py","migrate"])
spawnAndWait([sys.executable,"-m", "pip", "install", "-r", f"{path}/requirements.txt"])


