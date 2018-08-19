import time
from django.core.wsgi import get_wsgi_application
import os
import subprocess
import logging

from loghandler.loghandler import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

from database.models import Settings

logger.info("sleeping ...")
time.sleep(25)
logger.info("waking ...")


startCommand = Settings.objects.get(name="startCommando")
startCommand = startCommand.value.split(" ")
logger.info(startCommand)
p = subprocess.Popen(startCommand)