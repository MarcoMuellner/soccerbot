import praw
import os
import json
import asyncio
import logging
from typing import List,Union
from datetime import datetime,timedelta
import re

from discord_handler.client import client
from support.helper import task
from database.models import MatchEvents

logger = logging.getLogger(__name__)

path = os.path.dirname(os.path.realpath(__file__))+"/../"

reddit_available = True

with open(path+"secret.json") as f:
    try:
        reddit_secret = json.loads(f.read())['reddit_secret']
    except:
        logger.warning("Reddit is not available. Please add a reddit_secret to the secret file")
        reddit_available = False



reddit = praw.Reddit(client_id='3ikffhiRzJC3cA',
                     client_secret=reddit_secret,
                     user_agent='ubuntu:soccerbot:v0.4.0 (by /u/mamu7490)')

class RedditEvent:
    def __init__(self,matchEvent, time : datetime, home_team : str , away_team, callback : callable):
        self.matchEvent = matchEvent
        self.time = time
        self.home_team = home_team
        self.away_team = away_team
        self.callback = callback

    def __str__(self):
        return f"{self.home_team}:{self.away_team}: {self.matchEvent} --> {self.matchEvent} at {self.time}"

class RedditParser:
    liveEventList : List[RedditEvent] = []
    updateRunning = asyncio.Event(loop=client.loop)
    reddit = praw.Reddit(client_id='3ikffhiRzJC3cA',
                     client_secret=reddit_secret,
                     user_agent='ubuntu:soccerbot:v0.4.0 (by /u/mamu7490)')

    @staticmethod
    @task
    async def loop():
        while True:
            if not reddit_available:
                return
            RedditParser.updateRunning.set()
            newList = RedditParser.reddit.subreddit('soccer').new(limit=10)
            for i in RedditParser.liveEventList:
                if i.matchEvent.event != MatchEvents.goal:
                    logger.info(f"Can't react to {i}, as we can only react to goals currently")
                    RedditParser.liveEventList.remove(i)
                    continue

                result = RedditParser.parseReddit(i,newList)
                if result is not None:
                    i.callback(i,result)
                    RedditParser.liveEventList.remove(i)

                if datetime.utcnow() - i.time > timedelta(minutes=15):
                    logger.info(f"Removing {i}, as 15 minutes are passed")
                    RedditParser.liveEventList.remove(i)
            RedditParser.updateRunning.clear()
            await asyncio.sleep(30)

    @staticmethod
    def parseReddit(event : RedditEvent,newList) -> Union[str,None]:
        for i in newList:
            if event.home_team.clear_name in i.title or event.away_team.clear_name in i.title or 'goal' in i.title:
                hTeam = event.home_team.clear_name.replace(" ","|")
                aTeam = event.away_team.clear_name.replace(" ","|")
                regexString = re.compile(rf"({hTeam})(.+-.+)({aTeam}).+(\s\d+.+)")
                findList = regexString.findall(i.title)
                if len(findList) != 0:
                    logger.info(f"Matched something: {hTeam}:{aTeam}, score {findList[0][1]}, minute {findList[0][3]}")
                    logger.info(f"Match minute is {event.matchEvent.minute}")
                    if event.matchEvent.minute in findList[0][3]:
                        logger.info(f"Event matches!")
                        logger.info(f"URL is {i.url}")
                        return i.url
                    else:
                        logger.info(f"Minute doesnt match: Expected: {event.matchEvent.minute}, got {findList[0][3]}")
                logger.info(f"Possible non catched event for {event} : {i}")
        return None

    @staticmethod
    def addEvent(event : RedditEvent):
        RedditParser.updateRunning.wait()

        RedditParser.liveEventList.append(event)