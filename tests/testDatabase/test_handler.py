
"""
import os
from django.core.wsgi import get_wsgi_application
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()
from datetime import datetime,timedelta,timezone
import pytz

import pytest
from httmock import all_requests, HTTMock

from database.handler import *
from database.models import DiscordServer
from tests.testAPI.test_calls import unifiedHttMock

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass

getAndSaveDataList = [
    (getAllFederations,{}),
    (getAllCountries,{}),
    (getAllCompetitions,{'idFederation':'UEFA'}),
    (getAllSeasons, {'idCompetitions':2000000019}),
    (getAllMatches, {'idCompetitions': 2000000019,'idSeason':2000011119}),
]

@pytest.mark.parametrize("values",getAndSaveDataList)
def testGetAndSaveData(values):
    with HTTMock(unifiedHttMock):
        getAndSaveData(values[0],**values[1])

def testUpdateOverlayData():
    with HTTMock(unifiedHttMock):
        updateOverlayData()

def testUpdateMatches():
    with HTTMock(unifiedHttMock):
        updateMatches()

@pytest.fixture
def preUpdate():
    getAndSaveData(getAllFederations)
    getAndSaveData(getAllCountries)
    getAndSaveData(getAllCompetitions, idFederation="UEFA")
    getAndSaveData(getAllSeasons, idCompetitions=2000000019)
    comp = Competition.objects.get(id=2000000019)
    season = Season.objects.get(id=2000011119)
    getAndSaveData(getAllMatches, idCompetitions=comp.id, idSeason=season.id)
    return comp,season

def testUpdateMatchesSingleCompetition(preUpdate):
    with HTTMock(unifiedHttMock):
        comp,season = preUpdate
        updateMatchesSingleCompetition(comp,season)

def testCreateMatchDayObject(preUpdate):
    with HTTMock(unifiedHttMock):
        comp,season = preUpdate
        compWatcher = CompetitionWatcher(competition=comp,
                                         current_season=season, applicable_server=DiscordServer(name="temp"), current_matchday=1)

        match = Match.objects.all()
        result = createMatchDayObject(match,compWatcher)
        assert isinstance(result,MatchDayObject)

utc=pytz.UTC

"""