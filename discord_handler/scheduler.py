import asyncio
from asyncio import BaseEventLoop
import discord
from discord_handler.handler import client,createChannel,deleteChannel
from database.handler import updateDB,getNextMatchDays
import datetime


async def schedulerInit():
    targetTime = datetime.datetime.now().replace(hour=0,minute=0,second=0)
    await updateDBTask(calculateSleepTime(targetTime))
    for i in getNextMatchDays():
        await asyncCreateChannel(calculateSleepTime(i.startTime),i.matchdayString)
        await asyncDeleteChannel(calculateSleepTime(i.startTime),i.matchdayString)

def calculateSleepTime(targetTime:datetime,nowTime :datetime = datetime.datetime.now()):
    return (targetTime-nowTime).total_seconds()

async def asyncCreateChannel(sleepPeriod:float, channelName:str):
    asyncio.sleep(sleepPeriod)
    createChannel(client.get_server(),channelName)

async def asyncDeleteChannel(sleepPeriod:float, channelName:str):
    asyncio.sleep(sleepPeriod)
    deleteChannel(client.get_server(),channelName)

async def updateDBTask(sleepPeriod:float):
    asyncio.sleep(sleepPeriod)
    updateDB()
    await schedulerInit()