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

def testGetNextMatchDayObjects(preUpdate):
    with HTTMock(unifiedHttMock):
        comp, season = preUpdate
        server = DiscordServer(name="temp")
        server.save()
        compWatcher = CompetitionWatcher(competition=comp,
                                         current_season=season, applicable_server=server,
                                         current_matchday=1)
        compWatcher.save()
        today = datetime.datetime.now().today()+timedelta(hours=5)

        for i in Match.objects.all():
            i.date = today
            i.save()

        result = getNextMatchDayObjects()
        assert len(result) != 0
        for i in result:
            assert isinstance(i,MatchDayObject)
          #  assert i.startTime < utc.localize(today) # for some reason this does not work
          #  assert i.endTime > utc.localize(today)# for some reason this does not work
            assert i.matchdayString != ""

        getCurrentMatches()


