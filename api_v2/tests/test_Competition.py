import os
from django.core.wsgi import get_wsgi_application
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

import pytest

from ..obj.models import Competition,Federation

@pytest.mark.django_db
def testStructue():
    if len(Federation.objects.all()) == 0:
        Federation.initData()

    for i in Federation.objects.all():
        Competition.initData(i)