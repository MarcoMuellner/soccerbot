import logging
from datetime import timedelta, datetime
import asyncio
from discord import Server
from pytz import UTC

from database.models import CompetitionWatcher,  DiscordServer, Season, Competition
from database.handler import updateOverlayData, updateMatches, getNextMatchDayObjects, getCurrentMatches
from database.handler import updateMatchesSingleCompetition, getAllSeasons, getAndSaveData
from support.helper import task
from discord_handler.client import client,toDiscordChannelName
from discord_handler.liveMatch import runMatchThread

logger = logging.getLogger(__name__)


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


async def removeOldChannels():
    deleteChannelList = []
    for i in client.get_all_channels():
        if "-matchday-" in i.name:
            logger.info("Deleting old channel {i.name}")
            deleteChannelList.append((i.server, i.name))

    for i in deleteChannelList:
        await deleteChannel(i[0], i[1])


schedulerInitRunning = asyncio.Event(loop=client.loop)


@task
async def runScheduler():
    """
    Starts the scheduler task, which will automatically create channels adnd update databases. Currently this is
    always done at 24:00 UTC. Should be called via create_task!
    """
    await client.wait_until_ready()
    while True:
        # take synchronization object, during update no live thread should run!
        schedulerInitRunning.set()
        targetTime = datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        logger.info("Initializing schedule for tomorrow")

        # update competitions, seasons etc. Essentially the data that is always there
        updateOverlayData()
        # update all matches for the monitored competitions
        updateMatches()

        # update schedulers that create and delete channels
        client.loop.create_task(updateMatchScheduler())
        schedulerInitRunning.clear()

        await asyncio.sleep(calculateSleepTime(targetTime))


@task
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

        # Get all matches that are nearly upcoming or currently running
        matchList = [i for i in getCurrentMatches() if i not in runningMatches]
        logger.debug(f"Current matchlist: {matchList}")
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


def calculateSleepTime(targetTime: datetime, nowTime: datetime = datetime.utcnow().replace(tzinfo=UTC)):
    """
    Calculates time between targetTime and nowTime in seconds
    """
    return (targetTime.replace(tzinfo=UTC) - nowTime).total_seconds()


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

@task
async def watchCompetition(competition: Competition, serverName: str):
    """
    Adds a compeitition to be monitored. Also updates matches and competitions accordingly.
    :param competition: Competition to be monitored.
    :param serverName: Name of the discord server
    """
    logger.info(f"Start watching competition {competition} on {serverName}")

    season = Season.objects.filter(competition=competition).order_by('start_date').last()
    if season == None:
        getAndSaveData(getAllSeasons, idCompetitions=competition.id)
        season = Season.objects.filter(competition=competition).order_by('start_date').last()
    server = DiscordServer(name=serverName)
    server.save()

    updateMatchesSingleCompetition(competition=competition, season=season)

    compWatcher = CompetitionWatcher(competition=competition,
                                     current_season=season, applicable_server=server, current_matchday=1)
    compWatcher.save()
    client.loop.create_task(updateMatchScheduler())
