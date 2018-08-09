import os
import logging
from django.core.wsgi import get_wsgi_application
import discord
import sys
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()
from discord_handler.handler import cmdHandler,client,schedulerInit
from loghandler.loghandler import setup_logging
from support.helper import parseCommandoFunctions
from discord_handler import cdos


setup_logging()
logger = logging.getLogger(__name__)

@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user.name} with id {client.user.id}")
    parseCommandoFunctions(cdos)
    await schedulerInit()
    logger.info("Update complete")


@client.event
async def on_message(message : discord.Message):
    try:
        await client.send_message(message.channel, await cmdHandler(message))
    except discord.errors.HTTPException:
        pass

logger.info("------------------Soccerbot is starting-----------------------")
client.run('NDc0MjA5MTg0NzA4MTY1NjQy.DkNbcg.tphF6_RxXzRlylHn4mSPlIe49Zw')
