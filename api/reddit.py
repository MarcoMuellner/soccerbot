import praw
import os
import json
import asyncio
import logging
from typing import List,Union
from datetime import datetime

from discord_handler.client import client
from support.helper import task

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
        return f"{self.home_team}:{self.away_team}: {self.matchEvent.minute} --> {self.matchEvent.event} at {self.time}"

class RedditParser:
    teamList : List[RedditEvent] = []
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
            for i in RedditParser.teamList:
                result = RedditParser.parseReddit(i)
                if result is not None:
                    i.callback(i,result)
                    RedditParser.teamList.remove(i)

                #need to remove event here if it is longer passed than 30 minutes
            RedditParser.updateRunning.clear()
            await asyncio.sleep(30)

    @staticmethod
    def parseReddit(event : RedditEvent) -> Union[str,None]:
        for i in RedditParser.reddit.subreddit('soccer').new(limits=10):
            if event.home_team in i.title or event.away_team in i.title or 'goal' in i.title:
                logger.info(f"Possible event for {i}")
                logger.info(i.title)
        return None

    @staticmethod
    def addEvent(event : RedditEvent):
        RedditParser.updateRunning.set()

        RedditParser.teamList.append(event)

        RedditParser.updateRunning.clear()