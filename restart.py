import time
from django.core.wsgi import get_wsgi_application
import os
import subprocess

# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

from database.models import Settings

time.sleep(25)


startCommand = Settings.objects.get(name="startCommando")
startCommand = startCommand.value.split(" ")
print(startCommand)
p = subprocess.Popen(startCommand)