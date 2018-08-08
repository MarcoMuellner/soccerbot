import os
import logging
from django.core.wsgi import get_wsgi_application
import discord
import sys
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()
from discord_handler.handler import cmdHandler,client
from discord_handler.scheduler import schedulerInit
from loghandler.loghandler import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user.name} with id {client.user.id}")
    await schedulerInit()

@client.event
async def on_message(message : discord.Message):
    try:
        await client.send_message(message.channel, cmdHandler(message))
    except discord.errors.HTTPException:
        pass

logger.info("------------------Soccerbot is starting-----------------------")
client.loop.create_task(schedulerInit())
client.run('NDc0MjA5MTg0NzA4MTY1NjQy.DkNbcg.tphF6_RxXzRlylHn4mSPlIe49Zw')
