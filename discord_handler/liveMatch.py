import asyncio
from discord import Channel,Embed
from typing import Dict,Union,Tuple,List
from collections import OrderedDict
from django.core.exceptions import ObjectDoesNotExist
import logging
from json.decoder import JSONDecodeError
from datetime import datetime,timedelta
from pytz import UTC

from database.models import Match,MatchEvents,MatchEventIcon
from api.calls import makeMiddlewareCall,DataCalls
from discord_handler.client import client,toDiscordChannelName
from support.helper import task

logger = logging.getLogger(__name__)

class MatchEventData:
    def __init__(self, event: MatchEvents, minute: str, team: str, player: str, playerTo: str):
        self.event = event
        self.minute = minute
        self.team = team
        self.player = player
        self.playerTo = playerTo


class LiveMatch:
    def __init__(self,match : Match):
        self.match = match
        self.passed = False
        self.running = False
        self.started = False
        homeTeam = match.home_team.clear_name
        awayTeam = match.away_team.clear_name
        self.title = f"**{homeTeam}** - : - **{awayTeam}**"
        self.goalList = []

    @task
    async def runMatchThread(self):
        """
        Start a match threader for a given match. Will read the live data from the middleWare API (data.fifa.com) every
        20 seconds and post the events to the channel that corresponds to the match. This channel has to be created
        previously.
        :param match: Match object.  Will  post to discord channels if the object is a database.models.Match object
        """
        pastEvents = []
        eventList = []
        sleepTime = 600

        matchid = self.match.id
        channelName = toDiscordChannelName(f"{self.match.competition.clear_name} Matchday {self.match.matchday}")

        lineupsPosted = False
        while True:
            try:
                data = makeMiddlewareCall(DataCalls.liveData + f"/{matchid}")
            except JSONDecodeError:
                break

            if data["match"]["isFinished"]:
                logger.info(f"Match {self.match} allready passed")
                break

            self.running = True

            if not lineupsPosted and data["match"]["hasLineup"]:
                try:
                    for channel in client.get_all_channels():
                        if channel.name == channelName:
                            await LiveMatch.postLineups(channel, self.match, data["match"])
                            lineupsPosted = True
                            sleepTime = 20
                except RuntimeError:
                    logger.warning("Size of channels has changed")

            newEvents, pastEvents = LiveMatch.parseEvents(data["match"]["events"], pastEvents)
            eventList += newEvents

            for i in eventList:
                try:
                    for channel in client.get_all_channels():
                        if channel.name == channelName:
                            self.started = True
                            self.title,goalString = await LiveMatch.sendMatchEvent(channel, self.match, i)
                            self.goalList.append(goalString)
                            try:
                                eventList.remove(i)
                            except ValueError:
                                pass
                            logger.info(f"Posting event: {i}")
                except RuntimeError:
                    logger.warning("Size of channels has changed!")
                    break

            if data["match"]["isFinished"]:
                logger.info(f"Match {match} finished!")
                break

            await asyncio.sleep(sleepTime)

        now = datetime.utcnow().replace(tzinfo=UTC)
        if now < (self.match.date + timedelta(hours=3)).replace(tzinfo=UTC):
            self.passed = True
        self.running = False
        self.started = False

    @staticmethod
    async def postLineups(channel: Channel, match: Match, data: Dict):
        lineup = OrderedDict()
        for i in ['home', 'away']:
            lineup[i] = OrderedDict()
            lineup[i]['starting'] = []
            lineup[i]['bench'] = []
            lineup[i]['coach'] = []
            for player in data['lineups']['teams'][i]:
                playerInfo = OrderedDict()
                playerInfo['name'] = player['personName']
                playerInfo['number'] = player['shirtNumber']
                playerInfo['captain'] = player['isCaptain']
                playerInfo['gk'] = player['isGoalKeeper']

                if player['isCoach']:
                    lineup[i]['coach'].append(playerInfo)
                elif player['startingLineUp']:
                    lineup[i]['starting'].append(playerInfo)
                else:
                    lineup[i]['bench'].append(playerInfo)

        def getLineupPlayerString(teamString):
            def listPlayers(position):
                lineupString = ""
                for startingPlayer in lineup[teamString][position]:
                    lineupString += f"**{startingPlayer['number']}** - {startingPlayer['name']}"
                    if startingPlayer['gk']:
                        lineupString += f" (GK) "
                    if startingPlayer['captain']:
                        lineupString += f"(C) "
                    lineupString += "\n"
                return lineupString

            lineupString = "**Starting lineup:**\n"
            lineupString += listPlayers('starting')
            # lineupString += "\n**Bench:**\n"
            # lineupString += listPlayers('bench')
            lineupString += f"\n\n**Coach:\n{lineup[teamString]['coach'][0]['name']}**\n\n\n  "
            return lineupString

        homeString = getLineupPlayerString('home')
        awayString = getLineupPlayerString('away')

        embObj = Embed(title="Lineups", description=f"**{match.home_team.clear_name} vs {match.away_team.clear_name}**")

        embObj.add_field(name=match.home_team.clear_name, value=homeString)
        embObj.add_field(name=match.away_team.clear_name, value=awayString)

        try:
            await client.send_message(channel, embed=embObj)
        except:
            asyncio.sleep(10)
            for i in client.get_all_channels():
                if channel.name == i.name:
                    await client.send_message(channel, embed=embObj)

    @staticmethod
    async def beautifyEvent(event,match):
        data = makeMiddlewareCall(DataCalls.liveData + f"/{match.id}")['match']
        homeTeam = data['teamHomeName']
        awayTeam = data['teamAwayName']

        if event.event == MatchEvents.goal:
            if event.team == homeTeam:
                goalString = f"[{data['scoreHome']}] : {data['scoreAway']}"
            else:
                goalString = f"{data['scoreHome']} : [{data['scoreAway']}]"
        else:
            goalString = f"{data['scoreHome']} : {data['scoreAway']}"

        title = f"**{homeTeam}** {goalString} **{awayTeam}**"
        try:
            val = MatchEventIcon.objects.get(event=event.event.value).eventIcon
        except ObjectDoesNotExist:
            val = ""
        content = f"{val}{event.minute}"

        if event.event == MatchEvents.kickoffFirstHalf:
            content += " **KICKOFF** The match is underway!"
        elif event.event == MatchEvents.kickoffSecondHalf:
            content += " **KICKOFF** Second Half!"
        elif event.event == MatchEvents.firstHalfEnd:
            content += " **HALF TIME!**"
        elif event.event == MatchEvents.secondHalfEnd:
            content += " Second half has ended."
        elif event.event == MatchEvents.matchOver:
            content += "**FULL TIME**!"
        elif event.event == MatchEvents.goal:
            goalString =content+ f" {event.player}"
            content += f" **GOAL**! {event.player} scores for **{event.team}**"
        elif event.event == MatchEvents.yellowCard:
            content += f" **YELLOW CARD:** {event.player}(**{event.team}**)"
        elif event.event == MatchEvents.yellowRedCard:
            content += f" **SECOND YELLOW CARD**: {event.player}(**{event.team}**)"
        elif event.event == MatchEvents.redCard:
            content += f" **RED CARD**: {event.player} (**{event.team}**)"
        elif event.event == MatchEvents.substitution:
            content += f" **SUBSTITUTION** **{event.team}**:{event.player} **IN**, {event.playerTo} **OUT**"
        elif event.event == MatchEvents.missedPenalty:
            content += f" **PENALTY MISSED!** {event.player} has missed a penalty **({event.team})"
        else:
            logger.error(f"Event {event.event} not handled. No message is send to server!")
            return

        return title,content,goalString

    @staticmethod
    async def sendMatchEvent(channel: Channel, match: Match, event: MatchEventData):
        """
        This function encapsulates the look and feel of the message that is sent when a matchEvent happens.
        It will build the matchString, the embed object, etc. and than send it to the appropiate channel.
        :param channel: The channel where we want to send things to
        :param match: The match that this message applies to (Metadata!)
        :param event: The actual event that happened. It consists of a MatchEvents enum and a DataDict, which in
        itself contains the minute, team and player(s) the event applies to.
        """

        title,content,goalString = LiveMatch.beautifyEvent(event,match)
        embObj = Embed(title=title, description=content)
        embObj.set_author(name=match.competition.clear_name)

        try:
            await client.send_message(channel, embed=embObj)
        except:
            asyncio.sleep(10)
            for i in client.get_all_channels():
                if i.name == channel.name:
                    await client.send_message(i, embed=embObj)

        return title,goalString

    @staticmethod
    def parseEvents(data: list, pastEvents=list) -> Tuple[List[MatchEventData], List]:
        """
        Parses the event list from the middleware api. The code below should be self explanatory, every eventCode
        represents a certain event.
        :param data: data that is to be parsed
        :param pastEvents: all events that already happened
        :return: Returns two lists: the events that are new, as well as a full list of all events that already happened
        including the new ones.
        """
        retEvents = []
        if data != pastEvents:
            diff = [i for i in data if i not in pastEvents]
            for event in reversed(diff):
                eventData = MatchEventData(event=MatchEvents.none,
                                           minute=event['minute'],
                                           team=event['teamName'],
                                           player=event['playerName'],
                                           playerTo=event['playerToName'],
                                           )
                if event['eventCode'] == 3:  # Goal!
                    eventData.event = MatchEvents.goal
                elif event['eventCode'] == 4:  # Substitution!
                    eventData.event = MatchEvents.substitution
                elif event['eventCode'] == 1:
                    ev = MatchEvents.yellowCard if event['eventDescriptionShort'] == "Y" else MatchEvents.redCard
                    eventData.event = ev
                elif event['eventCode'] == 2:
                    eventData.event = MatchEvents.yellowRedCard
                elif event['eventCode'] == 5:
                    eventData.event = MatchEvents.missedPenalty
                elif event['eventCode'] == 14:
                    ev = MatchEvents.firstHalfEnd if event[
                                                         'phaseDescriptionShort'] == "1H" else MatchEvents.secondHalfEnd
                    eventData.event = ev
                elif event['eventCode'] == 13:
                    ev = MatchEvents.kickoffFirstHalf if event[
                                                             'phaseDescriptionShort'] == "1H" else MatchEvents.kickoffSecondHalf
                    eventData.event = ev
                else:
                    logger.error(f"EventId {event['eventCode']} with descr {event['eventDescription']} not handled!")
                    logger.error(f"TeamName: {event['teamName']}")
                    continue
                retEvents.append(eventData)
            pastEvents = data
        return retEvents, pastEvents

