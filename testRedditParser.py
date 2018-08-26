import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

from api.reddit import RedditParser,RedditEvent
from database.models import Match,Competition,CompetitionWatcher
from datetime import datetime
from loghandler.loghandler import setup_logging

competition = Competition.objects.filter(clear_name="Premier League").first()
compWatcher = CompetitionWatcher.objects.filter(competition=competition).first()

setup_logging()

with open("parseRedditRes.txt") as f:
    newList = f.readlines()

class dummyReddit:
    def __init__(self,title,url):
        self.title = title
        self.url = url

objList = []
for i in newList:
    objList.append(dummyReddit(i,i))
def callbackFun(x,y):
    print(x,y)

for i in Match.objects.filter(competition=competition).filter(matchday=3).filter(season=compWatcher.current_season):
    ev = RedditEvent("dummy",datetime.utcnow(),i.home_team,i.away_team,callbackFun)
    RedditParser.parseReddit(ev,objList)

