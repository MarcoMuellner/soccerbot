import asyncio
from discord_handler.handler import client,createChannel,deleteChannel
from database.handler import updateDB,getNextMatchDays
import datetime
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


async def schedulerInit():
    while(True):
        logger.info("Initializing schedule for tomorrow")
        targetTime = datetime.datetime.now().replace(hour=0,minute=0,second=0)+timedelta(days=1)
        updateDB()
        for i in getNextMatchDays():
            logger.info(f"Initializing task for {i.matchdayString} from {i.startTime} to {i.endTime}")
            await asyncCreateChannel(calculateSleepTime(i.startTime),i.matchdayString)
            await asyncDeleteChannel(calculateSleepTime(i.startTime),i.matchdayString)
        await asyncio.sleep(calculateSleepTime(targetTime))

def calculateSleepTime(targetTime:datetime,nowTime :datetime = datetime.datetime.now()):
    return (targetTime-nowTime).total_seconds()

async def asyncCreateChannel(sleepPeriod:float, channelName:str):
    await asyncio.sleep(sleepPeriod)
    createChannel(client.get_server(),channelName)

async def asyncDeleteChannel(sleepPeriod:float, channelName:str):
    await asyncio.sleep(sleepPeriod)
    deleteChannel(client.get_server(),channelName)