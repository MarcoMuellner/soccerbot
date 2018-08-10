import logging
from database.models import *
from discord import Message, Server,Client
from database.handler import updateMatchesSingleCompetition,getAllSeasons,getAndSaveData
from database.handler import updateOverlayData,updateMatches,getNextMatchDayObjects,getCurrentMatches
import datetime
from datetime import timedelta,timezone
from support.helper import DiscordCommando
from api.calls import makeMiddlewareCall,DataCalls

client = Client()
from support.helper import log_return
import asyncio

logger = logging.getLogger(__name__)

class DiscordCmds:
    addComp = "!addCompetition"

def toDiscordName(name:str)->str:
    if name == None:
        return None
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
            getAndSaveData(getAllSeasons, idCompetitions=competition.id)
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

schedulerInitRunning = asyncio.Event(loop=client.loop)

async def schedulerInit():
    await client.wait_until_ready()
    while(True):
        schedulerInitRunning.set()
        targetTime = datetime.datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) + timedelta(days=1)
        logger.info("Initializing schedule for tomorrow")
        updateOverlayData()
        updateMatches()
        client.loop.create_task(updateMatchScheduler())
        schedulerInitRunning.clear()
        await asyncio.sleep(calculateSleepTime(targetTime))

async def matchChecker():
    await client.wait_until_ready()
    schedulerInitRunning.wait()
    runningMatches = []
    while(True):
        matchList = [i for i in getCurrentMatches() if i not in runningMatches]
        for match in matchList:
            logger.info(f"Starting match between {match.home_team.clear_name} and {match.away_team.clear_name}")
            client.loop.create_task(runMatchThread(match))
            runningMatches.append(match)
        await asyncio.sleep(60)


async def updateMatchScheduler():
    logger.info("Updating match schedule")
    for i in getNextMatchDayObjects():
        client.loop.create_task(asyncCreateChannel(calculateSleepTime(i.startTime), i.matchdayString))
        client.loop.create_task(asyncDeleteChannel(calculateSleepTime(i.endTime), i.matchdayString))
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

async def sendToChannel(channel,msg):
    await client.send_message(channel,msg)

async def runMatchThread(match):
    pastEvents = []
    eventList = []

    if isinstance(match,int):
        matchid = match
        channelName = None
    elif isinstance(match,Match):
        matchid = match.id
        channelName = toDiscordName(f"{match.competition.clear_name} Matchday {match.matchday}")
    else:
        raise ValueError("Match needs to be Match instance or int")
    while True:
        # api/v1/live/football/{idCompetition}/{idSeason}/{idStage}/{idMatch}
        data = makeMiddlewareCall(DataCalls.liveData+f"/{matchid}")

        newEvents,pastEvents = parseEvents(data["match"]["events"],pastEvents)
        eventList += newEvents

        for i in eventList:
            for channel in client.get_all_channels():
                if channel.name == channelName:
                    await sendToChannel(channel,i)
                    try:
                        eventList.remove(i)
                    except ValueError:
                        pass
                    print(i)

        if data["match"]["isFinished"]:
            print("Match finished!")
            break
        await asyncio.sleep(20)


def parseEvents(data:list,pastEvents = list):
    retEvents = []
    if data != pastEvents:
        diff = [i for i in data if i not in pastEvents]
        for event in reversed(diff):
            if event['eventCode'] == 3: #Goal!
                retEvents.append(f"{event['minute']}: Goal! {event['playerName']} scores for {event['teamName']}")
            elif event['eventCode'] == 4: #Substitution!
                retEvents.append(f"{event['minute']}: Substition! {event['playerName']} changes for {event['playerToName']}")
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
    return retEvents,pastEvents