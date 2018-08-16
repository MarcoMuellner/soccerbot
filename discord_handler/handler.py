import logging
from datetime import timedelta, datetime
import asyncio
from discord import Server
from pytz import UTC
from typing import Tuple,Dict
from collections import OrderedDict

from database.models import CompetitionWatcher,  DiscordServer, Season, Competition
from database.handler import updateOverlayData, updateMatches, getNextMatchDayObjects, getCurrentMatches
from database.handler import updateMatchesSingleCompetition, getAllSeasons, getAndSaveData,compDict
from support.helper import task
from discord_handler.client import client,toDiscordChannelName

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

class Scheduler:
    matchDayObject = {}
    matchSchedulerRunning = asyncio.Event(loop=client.loop)
    maintananceSynchronizer = asyncio.Event(loop=client.loop)
    @staticmethod
    @task
    async def maintananceScheduler():
        """
        Starts the scheduler task, which will automatically create channels adnd update databases. Currently this is
        always done at 24:00 UTC. Should be called via create_task!
        """
        await client.wait_until_ready()
        while True:
            # take synchronization object, during update no live thread should run!
            Scheduler.maintananceSynchronizer.set()
            targetTime = datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)
            logger.info("Maintaining data")

            # update competitions, seasons etc. Essentially the data that is always there
            updateOverlayData()
            # update all matches for the monitored competitions
            updateMatches()

            Scheduler.maintananceSynchronizer.clear()
            await asyncio.sleep(calculateSleepTime(targetTime))

    @staticmethod
    @task
    async def matchScheduler():
        await client.wait_until_ready()
        Scheduler.matchDayObject = getNextMatchDayObjects()
        while True:
            Scheduler.matchSchedulerRunning.set()
            Scheduler.maintananceSynchronizer.wait()
            for competition,matchObject in Scheduler.matchDayObject.items():
                for md,data in matchObject.items():
                    currentTime = datetime.utcnow().replace(tzinfo=UTC)
                    if data['start'] < currentTime and data['end'] > currentTime:
                        await asyncCreateChannel(data['channel_name'])
                        for i in data['upcomingMatches']:
                            client.loop.create_task(i.runMatchThread())
                            data['currentMatches'].append(i)
                            data['upcomingMatches'].remove(i)

                        asyncio.sleep(5)

                        for i in data['currentMatches']:
                            if i.passed:
                                data['passedMatches'].append(i)
                                data['currentMatches'].remove(i)

                            if not i.passed and not i.running:
                                data['upcomingMatches'].append(i)
                                data['currentMatches'].remove(i)
                    elif data['end'] < currentTime:
                        await asyncDeleteChannel(data['channel_name'])
            Scheduler.matchSchedulerRunning.clear()
            await asyncio.sleep(60)

    @staticmethod
    def addCompetition(competition : CompetitionWatcher):
        Scheduler.matchSchedulerRunning.wait()
        Scheduler.matchDayObject[competition.competition.clear_name] = compDict(competition)

    @staticmethod
    @task
    async def removeCompetition(competition : CompetitionWatcher):
        Scheduler.matchSchedulerRunning.wait()
        #todo clear up channels
        del Scheduler.matchDayObject[competition.competition.clear_name]

    @staticmethod
    def findCompetitionMatchdayByChannel(channelName : str) -> Tuple[str,int]:
        for competition, matchObject in Scheduler.matchDayObject.items():
            for md, data in matchObject.items():
                if channelName == data['channel_name']:
                    return (competition,md)
    @staticmethod
    def getScores(competition : str, matchday : int) -> Dict:
        if competition not in Scheduler.matchDayObject.keys():
            logger.error(f"{competition} is not in matchday objects!")
            return {}

        if matchday not in Scheduler.matchDayObject[competition]:
            logger.error(f"Matchday {matchday} is not in matchday objects")
            return {}

        matches = Scheduler.matchDayObject[competition][matchday]

        retDict = OrderedDict()
        for match in matches['currentMatches']:
            if match.started:
                retDict[match.title] = match.goalList

        return retDict



def calculateSleepTime(targetTime: datetime, nowTime: datetime = datetime.utcnow().replace(tzinfo=UTC)):
    """
    Calculates time between targetTime and nowTime in seconds
    """
    return (targetTime.replace(tzinfo=UTC) - nowTime).total_seconds()


async def asyncCreateChannel(channelName: str,sleepPeriod: float = None):
    """
    Async wrapper to create channel
    :param sleepPeriod: Period to wait before channel can be created
    :param channelName: Name of the channel that will be created
    """
    logger.info(f"Initializing create Channel task for {channelName} in {sleepPeriod}")
    if sleepPeriod != None:
        await asyncio.sleep(sleepPeriod)
    await createChannel(list(client.servers)[0], channelName)


async def asyncDeleteChannel( channelName: str,sleepPeriod: float = None):
    """
    Async wrapper to delete channel
    :param sleepPeriod: Period to wait before channel can be deleted
    :param channelName: Name of the channel that will be deleted
    """
    logger.info(f"Initializing delete Channel task for {channelName} in {sleepPeriod}")
    if sleepPeriod != None:
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
    Scheduler.addCompetition(compWatcher)