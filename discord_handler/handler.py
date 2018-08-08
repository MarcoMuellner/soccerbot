import logging
from database.models import *
from discord import Message, Server,Client
from database.handler import updateMatchesSingleCompetition,getSeasons,getAndSaveData
from database.handler import updateCompetitions,updateMatches,getNextMatchDays
import datetime
from datetime import timedelta,timezone

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
        season = Season.objects.filter(competition=competition).order_by('start_date').first()
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
    if msg.content.startswith(DiscordCmds.addComp):
        logger.info(f"Handling {DiscordCmds.addComp}")

        parameterSplit = msg.content.split("#")
        data = parameterSplit[0].split(" ")
        competition_string = ""

        for i in data[1:]:
            if competition_string == "":
                competition_string += i
            else:
                competition_string += " " + i

        logger.debug(f"Competition: {competition_string}, full: {parameterSplit}")

        if len(data) < 2:
            return "Add competition needs the competition as a Parameter!"

        comp = Competition.objects.filter(clear_name=competition_string)

        logger.debug(f"Available competitions: {comp}")

        if len(comp) == 0:
            return f"Can't find competition {competition_string}"

        if len(comp) != 1:
            if len(parameterSplit) == 1:
                names = [existing_com.clear_name for existing_com in comp]
                countryCodes = [existing_com.association for existing_com in comp]
                name_code = list(zip(names, countryCodes))
                return f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."
            else:
                comp = Competition.objects.filter(clear_name=competition_string,association=parameterSplit[1])
                if len(comp) != 1:
                    names = [existing_com.clear_name for existing_com in comp]
                    countryCodes = [existing_com.association for existing_com in comp]
                    name_code = list(zip(names,countryCodes))
                    return f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."

        watcher = CompetitionWatcher.objects.filter(competition=comp.first())

        logger.debug(f"Watcher objects: {watcher}")

        if len(watcher) != 0:
            return f"Allready watching {competition_string}"

        await watchCompetition(comp.first(), msg.server)

        return (f"Start watching competition {competition_string}")


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
    await asyncio.wait(tasksCreate)
    await asyncio.wait(tasksDelete) #this doesnt work yet, waits for createTasks to complete
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