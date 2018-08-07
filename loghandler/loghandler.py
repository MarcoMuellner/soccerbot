import os
import json
import logging.config
import discord

def setup_logging(
    default_path='loghandler/logsettings.json', 
    default_level=logging.DEBUG,
):
    '''Setup logging configuration

    '''

    logging.getLogger("requests").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)
    logger = logging.getLogger('discord')
    logger.setLevel(logging.ERROR)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
