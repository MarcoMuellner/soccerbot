import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

from database.models import Match
import datetime
from datetime import timedelta

from database.handler import MatchStatus

today = datetime.datetime.utcnow().today()
tomorrow = today + timedelta(days=1)

print(Match.objects.filter(date__lte=tomorrow).filter(date__gte=today).filter(competition_id=2000001041))

print(Match.objects.filter(match_status=MatchStatus.Live.value))

#match = Match.objects.get(id=300451279)

liveMatch = LiveMatch(300451301)
liveMatch.loop()