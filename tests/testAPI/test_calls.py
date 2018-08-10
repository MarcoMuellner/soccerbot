import pytest
from api.calls import *
from database.models import *
from httmock import all_requests, HTTMock
from typing import Dict
import json
import os


def loadJsonFile(fileName: str) -> Dict:
    with open(fileName) as f:
        data = f.read()
    return json.loads(data)


class TestObj:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2


def callFunc(resDict: Dict):
    return TestObj(resDict["param1"], resDict["param2"])


path = os.path.dirname(os.path.realpath(__file__)) + "/testFiles/"

apiCallList = [
    (ApiCalls.federations, {}),
    (ApiCalls.competitions, {'owner': 'UEFA', 'count': 1000, 'footballType': 0}),
    (ApiCalls.seasons, {'idCompetition': '2000000019', 'count': 1000}),
    (ApiCalls.matches, {'idCompetition': '2000000019', 'idSeason': '2000011119', 'count': 1000}),
    (ApiCalls.teams, {}),
    (ApiCalls.countries, {}),
]

getCallList = [
    (Federation, {}, getAllFederations),
    (Competition, {"idFederation": "UEFA"}, getAllCompetitions),
    (Season, {'idCompetitions': '2000000019'}, getAllSeasons),
    (Match, {'idCompetitions': '2000000019', 'idSeason': '2000011119'},getAllMatches),
    (Team, {}, getAllTeams),
    (Association, {},  getAllCountries),
    (Team, [1885546],  getSpecificTeam),
]

def unifiedHttMock(url,request):
    print(request.path_url)
    if ApiCalls.federations in request.path_url:
        data = loadJsonFile(path + "federation.json")
    elif ApiCalls.competitions in request.path_url:
        data = loadJsonFile(path + "competitions.json")
    elif ApiCalls.seasons in request.path_url:
        data = loadJsonFile(path + "seasons.json")
    elif ApiCalls.matches in request.path_url:
        data = loadJsonFile(path + "matches.json")
    elif ApiCalls.teams in request.path_url:
        data = loadJsonFile(path + "teams.json")
    elif ApiCalls.countries in request.path_url:
        data = loadJsonFile(path + "countries.json")
    elif ApiCalls.specificTeam in request.path_url:
        data = loadJsonFile(path+ "specificTeam.json")
    elif DataCalls.liveData in request.path_url:
        data = loadJsonFile(path + "live.json")
    else:
        data = {}
    return {'status_code': 200,
            'content': data}


def testAPICallObjects():
    """
    Checking API keywords.
    """
    for key, values in ApiCalls.__dict__.items():
        if key == "api_home" or key.startswith("__"):
            continue
        with pytest.raises(ValueError):
            int(values)  # simple check, should raise ValueError if it is really a string

        assert values[-1] != "/"  # no backslash at end!


def testDataCallObjects():
    """
    Checking Data keywords.
    """
    for key, values in DataCalls.__dict__.items():
        if key == "data_home" or key.startswith("__"):
            continue
        with pytest.raises(ValueError):
            int(values)

        assert values[-1] != "/"


def testLoop():
    """
    Tests the helper loop function
    """
    testDict = {
        "param1": "param1",
        "param2": "param2"
    }  # sample Dict
    reqList = [testDict for i in range(0, 100)]  # sample list

    result = loop(callFunc, reqList)

    assert isinstance(result, list)  # checking if list is returned

    for i in result:
        assert isinstance(i, TestObj)  # checking if conversion worked correctly
        assert i.param1 == "param1"
        assert i.param2 == "param2"


@pytest.mark.parametrize("values", apiCallList)
def testMakeAPICall(values):
    """
    Tries all different request possibilities for the API
    :param values:  --> Objects
    """
    with HTTMock(unifiedHttMock):
        result = makeAPICall(values[0], values[1])
        assert isinstance(result, list)


def testMakeMiddlewareCall():
    """
    Tries the live dataset for the Middleware
    """
    with HTTMock(unifiedHttMock):
        result = makeMiddlewareCall(DataCalls.liveData)
        assert isinstance(result, dict)


@pytest.mark.parametrize("values", getCallList)
def testGetCalls(values):
    """
    Tries all Federations
    """

    with HTTMock(unifiedHttMock):
        try:
            feds = values[2](**values[1])
        except:
            feds = values[2](*values[1])
        if values[2] != getSpecificTeam:
            assert isinstance(feds, list)
            for i in feds:
                assert isinstance(i, values[0])
        else:
            assert isinstance(feds, Team)
