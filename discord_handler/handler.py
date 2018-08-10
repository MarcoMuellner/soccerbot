import logging
from datetime import timedelta, timezone, datetime
import asyncio
from discord import Message, Server, Client, Channel
from typing import Union,Tuple,List

from database.models import *
from database.handler import updateMatchesSingleCompetition, getAllSeasons, getAndSaveData
from database.handler import updateOverlayData, updateMatches, getNextMatchDayObjects, getCurrentMatches
from support.helper import DiscordCommando
from api.calls import makeMiddlewareCall, DataCalls
from support.helper import log_return

client = Client()

logger = logging.getLogger(__name__)


def toDiscordChannelName(name: str) -> str:
    """
    Converts a string to a discord channel like name -> all lowercase and no spaces
    :param name:
    :return:
    """
    if name == None:
        return None
    return name.lower().replace(" ", "-")
    pass


async def createChannel(server: Server, channelName: str):
    """
    Creates a channel on the discord server.
    :param server: Server object --> relevant server for the channel
    :param channelName: Name of the channel that is to be created
    """
    for i in client.get_all_channels():
        if i.name == toDiscordChannelName(channelName) and i.server == server:
            logger.info(f"Channel {channelName} already available ")
            return
    logger.info(f"Creating channel {channelName} on {server.name}")
    await client.create_channel(server, channelName)


async def deleteChannel(server: Server, channelName: str):
    """
    Deletes a channel on the discord server
    :param server: Server object --> relevant server for the channel
    :param channelName: Name of the channel that is to be deleted
    """
    for i in client.get_all_channels():
        if i.name == toDiscordChannelName(channelName) and i.server == server:
            logger.info(f"Deleting channel {toDiscordChannelName(channelName)} on {server.name}")
            await client.delete_channel(i)
            break


async def watchCompetition(competition: Competition, serverName: str):
    """
    Adds a compeitition to be monitored. Also updates matches and competitions accordingly.
    :param competition: Competition to be monitored.
    :param serverName: Name of the discord server
    """
    logger.info(f"Start watching competition {competition} on {serverName}")

    season = None
    while season == None:
        season = Season.objects.filter(competition=competition).order_by('start_date').last()
        if season == None:
            getAndSaveData(getAllSeasons, idCompetitions=competition.id)
    server = DiscordServer(name=serverName)
    server.save()

    updateMatchesSingleCompetition(competition=competition, season=season)

    compWatcher = CompetitionWatcher(competition=competition,
                                     current_season=season, applicable_server=server, current_matchday=1)
    compWatcher.save()
    client.loop.create_task(updateMatchScheduler())


@log_return
async def cmdHandler(msg: Message) -> str:
    """
    Receives commands and handles it according to allCommandos. Commandos are automatically parsed from the code.
    :param msg: message from the discord channel
    :return:
    """
    for cdos in DiscordCommando.allCommandos():
        if msg.content.startswith(cdos.commando):
            if msg.author.bot:
                logger.info("Ignoring {msg.content}, because bot")
                return
            logger.info(f"Handling {cdos.commando}")
            try:
                return await cdos.fun(msg)
            except TypeError:
                return await cdos.fun()


schedulerInitRunning = asyncio.Event(loop=client.loop)


async def runScheduler():
    """
    Starts the scheduler task, which will automatically create channels adnd update databases. Currently this is
    always done at 24:00 UTC. Should be called via create_task!
    """
    await client.wait_until_ready()
    while True:
        # take synchronization object, during update no live thread should run!
        schedulerInitRunning.set()
        targetTime = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) + timedelta(days=1)
        logger.info("Initializing schedule for tomorrow")

        # update competitions, seasons etc. Essentially the data that is always there
        updateOverlayData()
        # update all matches for the monitored competitions
        updateMatches()

        # update schedulers that create and delete channels
        client.loop.create_task(updateMatchScheduler())
        schedulerInitRunning.clear()

        await asyncio.sleep(calculateSleepTime(targetTime))


async def runLiveThreader():
    """
    Starts the LiveThreader task, that automatically posts updates from matches to its according matches.
    :todo: remove matches from runningMatches
    :return:
    """
    await client.wait_until_ready()
    runningMatches = []

    while True:
        schedulerInitRunning.wait()

        #Get all matches that are nearly upcoming or currently running
        matchList = [i for i in getCurrentMatches() if i not in runningMatches]
        for match in matchList:
            logger.info(f"Starting match between {match.home_team.clear_name} and {match.away_team.clear_name}")

            client.loop.create_task(runMatchThread(match))
            runningMatches.append(match)
        await asyncio.sleep(60)


async def updateMatchScheduler():
    """
    Creates tasks that create and delete channels at specific times.
    """
    logger.info("Updating match schedule")
    for i in getNextMatchDayObjects():
        client.loop.create_task(asyncCreateChannel(calculateSleepTime(i.startTime), i.matchdayString))
        client.loop.create_task(asyncDeleteChannel(calculateSleepTime(i.endTime), i.matchdayString))
    logger.info("End update schedule")


def calculateSleepTime(targetTime: datetime, nowTime: datetime = datetime.now(timezone.utc)):
    """
    Calculates time between targetTime and nowTime in seconds
    """
    return (targetTime - nowTime).total_seconds()


async def asyncCreateChannel(sleepPeriod: float, channelName: str):
    """
    Async wrapper to create channel
    :param sleepPeriod: Period to wait before channel can be created
    :param channelName: Name of the channel that will be created
    """
    logger.info(f"Initializing create Channel task for {channelName} in {sleepPeriod}")
    await asyncio.sleep(sleepPeriod)
    await createChannel(list(client.servers)[0], channelName)


async def asyncDeleteChannel(sleepPeriod: float, channelName: str):
    """
    Async wrapper to delete channel
    :param sleepPeriod: Period to wait before channel can be deleted
    :param channelName: Name of the channel that will be deleted
    """
    logger.info(f"Initializing delete Channel task for {channelName} in {sleepPeriod}")
    await asyncio.sleep(sleepPeriod)
    await deleteChannel(list(client.servers)[0], channelName)


async def sendToChannel(channel : Channel, msg : str):
    """
    Sends a message to a given channel
    :param channel: Channel object where we want to send the stuff to
    :param msg: msg that is to be sent
    """
    await client.send_message(channel, msg)


async def runMatchThread(match : Union[str,Match]):
    """
    Start a match threader for a given match. Will read the live data from the middleWare API (data.fifa.com) every
    20 seconds and post the events to the channel that corresponds to the match. This channel has to be created
    previously.
    :param match: Match object. Can be the id of the match or the Match object. Will only post to discord channels
    if the object is a database.models.Match object
    """
    pastEvents = []
    eventList = []

    if isinstance(match, int):
        matchid = match
        channelName = None
    elif isinstance(match, Match):
        matchid = match.id
        channelName = toDiscordChannelName(f"{match.competition.clear_name} Matchday {match.matchday}")
    else:
        raise ValueError("Match needs to be Match instance or int")
    while True:
        data = makeMiddlewareCall(DataCalls.liveData + f"/{matchid}")

        newEvents, pastEvents = parseEvents(data["match"]["events"], pastEvents)
        eventList += newEvents

        for i in eventList:
            for channel in client.get_all_channels():
                if channel.name == channelName:
                    await sendToChannel(channel, i)
                    try:
                        eventList.remove(i)
                    except ValueError:
                        pass
                    logger.info(f"Posting event: {i}")

        if data["match"]["isFinished"]:
            logger.info(f"Match {match} finished!")
            break

        await asyncio.sleep(20)


def parseEvents(data: list, pastEvents=list) -> Tuple[List,List]:
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
            if event['eventCode'] == 3:  # Goal!
                retEvents.append(f"{event['minute']}: Goal! {event['playerName']} scores for {event['teamName']}")
            elif event['eventCode'] == 4:  # Substitution!
                retEvents.append(
                    f"{event['minute']}: Substition! {event['playerName']} changes for {event['playerToName']}")
            elif event['eventCode'] == 1:
                retEvents.append(f"{event['minute']}: Yellow card for {event['playerName']}")
            elif event['eventCode'] == 14:
                retEvents.append(f"{event['minute']}: End of the first half")
            elif event['eventCode'] == 13:
                ret = f"{event['minute']}: Kickoff"
                ret += " in the first half" if event['phaseDescriptionShort'] == "1H" else " in the second half"
                retEvents.append(ret)
            else:
                print(f"EventId {event['eventCode']} with descr {event['eventDescription']} not handled!")
        pastEvents = data
    return retEvents, pastEvents
