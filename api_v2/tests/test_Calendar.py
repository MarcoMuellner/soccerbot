import os
from django.core.wsgi import get_wsgi_application
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

import pytest

from ..obj.models import Calendar

@pytest.mark.django_db
def testStructue():
    Calendar.updateData()