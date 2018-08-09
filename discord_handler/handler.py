import logging
from database.models import *
from discord import Message, Server,Client
from database.handler import updateMatchesSingleCompetition,getSeasons,getAndSaveData
from database.handler import updateCompetitions,updateMatches,getNextMatchDays
import datetime
from datetime import timedelta,timezone
from support.helper import DiscordCommando

client = Client()
from support.helper import log_return
import asyncio

logger = logging.getLogger(__name__)

class DiscordCmds:
    addComp = "!addCompetition"

def toDiscordName(name:str)->str:
    return name.lower().replace(" ","-")
    pass


async def createChannel(server: Server, channelName : str):
    for i in client.get_all_channels():
        if i.name == toDiscordName(channelName) and i.server == server:
            logger.info(f"Channel {channelName} already available ")
            return
    logger.info(f"Creating channel {channelName} on {server.name}")
    await client.create_channel(server,channelName)


async def deleteChannel(server: Server, channelName: str):
    for i in client.get_all_channels():
        if i.name == toDiscordName(channelName) and i.server == server:
            logger.info(f"Deleting channel {toDiscordName(channelName)} on {server.name}")
            await client.delete_channel(i)
            break


async def watchCompetition(competition, serverName):
    logger.info(f"Start watching competition {competition} on {serverName}")

    season = None
    while season == None:
        season = Season.objects.filter(competition=competition).order_by('start_date').last()
        if season == None:
            getAndSaveData(getSeasons, idCompetitions=competition.id)
    server = DiscordServer(name=serverName)
    server.save()

    updateMatchesSingleCompetition(competition=competition,season=season)

    compWatcher = CompetitionWatcher(competition=competition,
                                     current_season=season, applicable_server=server, current_matchday=1)
    compWatcher.save()
    await updateMatchScheduler()

@log_return
async def cmdHandler(msg: Message):

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

async def schedulerInit():
    while(True):
        targetTime = datetime.datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) + timedelta(days=1)
        logger.info("Initializing schedule for tomorrow")
        updateCompetitions()
        updateMatches()
        await updateMatchScheduler()
        await asyncio.sleep(calculateSleepTime(targetTime))


async def updateMatchScheduler():
    logger.info("Updating match schedule")
    tasksCreate = [asyncCreateChannel(calculateSleepTime(i.startTime),i.matchdayString) for i in getNextMatchDays()]
    tasksDelete = [asyncDeleteChannel(calculateSleepTime(i.endTime), i.matchdayString) for i in getNextMatchDays()]
    if tasksCreate != []:
        await asyncio.wait(tasksCreate)
    if tasksDelete != []:
        await asyncio.wait(tasksDelete) #todo this doesnt work yet, waits for createTasks to complete
    logger.info("End update schedule")

def calculateSleepTime(targetTime:datetime,nowTime :datetime = datetime.datetime.now(timezone.utc)):
    return (targetTime-nowTime).total_seconds()

async def asyncCreateChannel(sleepPeriod:float, channelName:str):
    logger.info(f"Initializing create Channel task for {channelName} in {sleepPeriod}")
    await asyncio.sleep(sleepPeriod)
    await createChannel(list(client.servers)[0],channelName)

async def asyncDeleteChannel(sleepPeriod:float, channelName:str):
    logger.info(f"Initializing delete Channel task for {channelName} in {sleepPeriod}")
    await asyncio.sleep(sleepPeriod)
    await deleteChannel(list(client.servers)[0],channelName)