import asyncio
from asyncio import BaseEventLoop
import discord
from discord_handler.handler import client,createChannel,deleteChannel
from database.handler import updateDB
import datetime


async def schedulerInit():
    pass

def timerTask():
    pass

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
    timerTask()