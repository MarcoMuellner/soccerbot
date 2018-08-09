import os
from django.core.wsgi import get_wsgi_application
# Django specific settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# Ensure settings are read
application = get_wsgi_application()

import pytest
from httmock import all_requests, HTTMock

from database.handler import *
from tests.testAPI.test_calls import loadJsonFile

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass

path = os.path.dirname(os.path.realpath(__file__)) + "/../testAPI/testFiles/"

getAndSaveDataList = [
    (getAllFederations,{},loadJsonFile(path + "federation.json")),
    (getAllCountries,{},loadJsonFile(path + "countries.json")),
    (getAllCompetitions,{'idFederation':'UEFA'},loadJsonFile(path + "competitions.json")),
    (getAllSeasons, {'idCompetitions':2000000019}, loadJsonFile(path + "seasons.json")),
    (getAllMatches, {'idCompetitions': 2000000019,'idSeason':2000011119}, loadJsonFile(path + "matches.json")),
]

@pytest.mark.parametrize("values",getAndSaveDataList)
def testGetAndSaveData(values):
    @all_requests
    def httpMocker(url,request):
        if request.path_url == '/api/v1/confederations':
            content = loadJsonFile(path + "federation.json")
        else:
            content = values[2]
        return {
            "status_code":200,
            "content":content
        }

    with HTTMock(httpMocker):
        getAndSaveData(values[0],**values[1])

