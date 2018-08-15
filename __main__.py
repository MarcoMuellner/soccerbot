import os
import logging
from django.core.wsgi import get_wsgi_application
import discord
import json
import sys
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()
from discord_handler.handler import runScheduler,runLiveThreader,removeOldChannels
from discord_handler.cdos import cmdHandler
from loghandler.loghandler import setup_logging
from discord_handler.client import client
from discord_handler import cdos


setup_logging()
logger = logging.getLogger(__name__)

@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user.name} with id {client.user.id}")
    await removeOldChannels()
    client.loop.create_task(runScheduler())
    client.loop.create_task(runLiveThreader())
    logger.info("Update complete")


@client.event
async def on_message(message : discord.Message):
    try:
        await cmdHandler(message)
    except discord.errors.HTTPException:
        pass

logger.info("------------------Soccerbot is starting-----------------------")
path = os.path.dirname(os.path.realpath(__file__))
try:
    with open(path+"/secret.json") as f:
        key = json.loads(f.read())['secret']
except:
    logger.error(f"You need to create the secret.json file and check if secret:key is available, path {path+'/secret.json'}")
    sys.exit()
client.run(key)
