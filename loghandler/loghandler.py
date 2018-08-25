import os
import json
import logging.config
import discord

path = os.path.dirname(os.path.realpath(__file__)) + "/"

def setup_logging(
    default_path=path+'logsettings.json',
    default_level=logging.DEBUG,
):
    '''Setup logging configuration

    '''

    logging.getLogger("requests").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)
    logging.getLogger("prawcore").setLevel(logging.INFO)
    logger = logging.getLogger('discord')
    logger.setLevel(logging.ERROR)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    pathLogSettings = default_path
    if os.path.exists(pathLogSettings):
        with open(pathLogSettings, 'rt') as f:
            config = json.load(f)
        for i in ['info_file_handler','debug_file_handler','error_file_handler']:
            config['handlers'][i]['filename'] = path + "../" + config['handlers'][i]['filename']

        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
