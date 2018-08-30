import praw
from praw.exceptions import ClientException
import os
import json
import asyncio
import logging
from typing import List, Union
from datetime import datetime, timedelta
import re

from discord_handler.client import client
from support.helper import task
from database.models import MatchEvents, Goal, Match

logger = logging.getLogger(__name__)

path = os.path.dirname(os.path.realpath(__file__)) + "/../"

reddit_available = True
try:
    with open(path + "secret.json") as f:
        fileDict = json.loads(f.read())
        reddit_id = fileDict['reddit_client_id']
        reddit_secret = fileDict['reddit_secret']
except (KeyError, FileNotFoundError):
    logger.warning("Reddit is not available. Please add a reddit_secret to the secret file")
    reddit_available = False
    reddit_secret = None
    reddit_id = None


class RedditEvent:
    def __init__(self, matchEvent, time: datetime, match: Match, callback: callable):
        self.matchEvent = matchEvent
        self.time = time
        self.match = match
        self.callback = callback

    def __str__(self):
        return f"{self.match.home_team}:{self.match.home_team}: {self.matchEvent} --> {self.matchEvent} at {self.time}"


class RedditParser:
    liveEventList: List[RedditEvent] = []
    updateRunning = asyncio.Event(loop=client.loop)
    try:
        reddit = praw.Reddit(client_id=reddit_id,
                             client_secret=reddit_secret,
                             user_agent='ubuntu:soccerbot:v1.0.0 (by /u/mamu7490)')
    except ClientException:
        reddit = None

    @staticmethod
    async def loop():
        while True:
            if not reddit_available:
                return
            RedditParser.updateRunning.set()
            i: RedditEvent
            for i in RedditParser.liveEventList:
                if i.matchEvent.event != MatchEvents.goal:
                    logger.info(f"Can't react to {i}, as we can only react to goals currently")
                    RedditParser.liveEventList.remove(i)
                    continue

                logger.debug(f"Checking {i}")
                newList = RedditParser.reddit.subreddit('soccer').new(limit=50)
                result = RedditParser.parseReddit(i, newList)
                if result is not None:
                    Goal(match=i.match, player=i.matchEvent.player, minute=i.matchEvent.minute, link=result).save()
                    await i.callback(i, result)
                    RedditParser.liveEventList.remove(i)

                if datetime.utcnow() - i.time > timedelta(minutes=15):
                    logger.info(f"Removing {i}, as 15 minutes are passed")
                    RedditParser.liveEventList.remove(i)
            RedditParser.updateRunning.clear()
            await asyncio.sleep(30)

    @staticmethod
    def parseReddit(event: RedditEvent, newList) -> Union[str, None]:
        for i in newList:
            if event.match.home_team.clear_name in i.title or event.match.away_team.clear_name in i.title or 'goal' in i.title:
                hTeam = event.match.home_team.clear_name.replace(" ", "|")
                aTeam = event.match.away_team.clear_name.replace(" ", "|")
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
                        minuteEvent = int(re.findall("(\d+)", event.matchEvent.minute)[0])
                        minuteTitle = int(re.findall("(\d+)", findList[0][3])[0])
                        if minuteEvent in range(minuteTitle - 1, minuteTitle + 1):
                            logger.info(
                                f"Eventhough minutes do not match, fuzzy search says yes. MinuteEvent {minuteEvent},MinuteTitle {minuteTitle}")
                            logger.info(f"URL is {i.url}")
                            return i.url
                        logger.info(f"Minute doesnt match: Expected: {event.matchEvent.minute}, got {findList[0][3]}")
                logger.info(f"Possible non catched event for {event} : {i.title}")
                logger.info(f"regex String: {regexString.pattern}")
        return None

    @staticmethod
    def addEvent(event: RedditEvent):
        RedditParser.updateRunning.wait()
        logger.debug(f"Adding {event} to events")
        RedditParser.liveEventList.append(event)
