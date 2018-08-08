import asyncio
from discord_handler.handler import client,createChannel,deleteChannel
from database.handler import updateCompetitions,getNextMatchDays
import datetime
import logging
from datetime import timedelta,timezone

logger = logging.getLogger(__name__)


async def schedulerInit():
    while(True):
        logger.info("Initializing schedule for tomorrow")
        targetTime = datetime.datetime.now(timezone.utc).replace(hour=0,minute=0,second=0)+timedelta(days=1)
        updateCompetitions()
        for i in getNextMatchDays():
            logger.info(f"Initializing task for {i.matchdayString} from {i.startTime} to {i.endTime}")
            await asyncCreateChannel(calculateSleepTime(i.startTime),i.matchdayString)
            await asyncDeleteChannel(calculateSleepTime(i.endTime),i.matchdayString)
        await asyncio.sleep(calculateSleepTime(targetTime))

def calculateSleepTime(targetTime:datetime,nowTime :datetime = datetime.datetime.now(timezone.utc)):
    return (targetTime-nowTime).total_seconds()

async def asyncCreateChannel(sleepPeriod:float, channelName:str):
    await asyncio.sleep(sleepPeriod)
    await createChannel(list(client.servers)[0],channelName)

async def asyncDeleteChannel(sleepPeriod:float, channelName:str):
    await asyncio.sleep(sleepPeriod)
    await deleteChannel(list(client.servers)[0],channelName)
