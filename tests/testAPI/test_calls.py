import pytest
from api.calls import *
from database.models import *
from httmock import all_requests, HTTMock
from typing import Dict
import json
import os
"""
@urlmatch(netloc=r'(.*\.)?google\.com$')
def google_mock(url, request):
    return 'Feeling lucky, punk?'

with HTTMock(google_mock):
    r = requests.get('http://google.com/')
    print(r.content)  # 'Feeling lucky, punk?'
"""
def loadJsonFile(fileName:str)->Dict:
    with open(fileName) as f:
        data = f.read()
    return json.loads(data)

class TestObj:
    def __init__(self,param1,param2):
        self.param1 = param1
        self.param2 = param2


def callFunc(resDict : Dict):
    return TestObj(resDict["param1"],resDict["param2"])

path = os.path.dirname(os.path.realpath(__file__))+"/testFiles/"

apiCallList = [
    (ApiCalls.federations, {}, loadJsonFile(path + "federation.json")),
    (ApiCalls.competitions, {'owner': 'UEFA','count': 1000, 'footballType': 0}
     , loadJsonFile(path + "competitions.json")),
    (ApiCalls.seasons, {'idCompetition': '2000000019','count': 1000}, loadJsonFile(path + "seasons.json")),
    (ApiCalls.matches, {'idCompetition': '2000000019','idSeason': '2000011119','count': 1000}
     , loadJsonFile(path + "matches.json")),
    (ApiCalls.teams, {}, loadJsonFile(path + "teams.json")),
    (ApiCalls.countries, {}, loadJsonFile(path + "countries.json")),
]

getCallList = [
    (Federation, {}, loadJsonFile(path + "federation.json"),getFederations),
    (Competition, {"idFederation":"UEFA"}, loadJsonFile(path + "competitions.json"),getCompetitions),
    (Season, {'idCompetitions': '2000000019'}, loadJsonFile(path + "seasons.json"),getSeasons),
    (Match, {'idCompetitions': '2000000019','idSeason': '2000011119'}, loadJsonFile(path + "matches.json"),getMatches),
    (Team, {}, loadJsonFile(path + "teams.json"),getTeams),
    (Association, {}, loadJsonFile(path + "countries.json"),getCountries),
    (Team, [1885546], loadJsonFile(path + "specificTeam.json"),getSpecificTeam),
]

def testAPICallObjects():
    """
    Checking API keywords.
    """
    for key,values in ApiCalls.__dict__.items():
        if key == "api_home" or key.startswith("__"):
            continue
        with pytest.raises(ValueError):
            int(values) #simple check, should raise ValueError if it is really a string

        assert values[-1] != "/" # no backslash at end!

def testDataCallObjects():
    """
    Checking Data keywords.
    """
    for key,values in DataCalls.__dict__.items():
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
        "param1":"param1",
        "param2":"param2"
    } #sample Dict
    reqList = [testDict for i in range(0,100)] #sample list

    result = loop(callFunc,reqList)

    assert isinstance(result,list) #checking if list is returned

    for i in result:
        assert isinstance(i,TestObj) #checking if conversion worked correctly
        assert i.param1 == "param1"
        assert i.param2 == "param2"

@pytest.mark.parametrize("values", apiCallList)
def testMakeAPICall(values):
    """
    Tries all different request possibilities for the API
    :param values:  --> Objects
    """
    @all_requests
    def httpMocker(url,request):
        return {'status_code': 200,
         'content': values[2]}

    with HTTMock(httpMocker):
        result = makeAPICall(values[0],values[1])
        assert isinstance(result,list)

def testMakeMiddlewareCall():
    """
    Tries the live dataset for the Middleware
    """
    @all_requests
    def httpMocker(url,request):
        return {'status_code':200,
                'content':loadJsonFile(path+"live.json")}

    with HTTMock(httpMocker):
        result = makeMiddlewareCall(DataCalls.liveData)
        assert isinstance(result,dict)

@pytest.mark.parametrize("values", getCallList)
def testGetCalls(values):
    """
    Tries all Federations
    """
    @all_requests
    def httpMocker(url,request):
        if request.path_url == '/api/v1/confederations':
            content = loadJsonFile(path + "federation.json")
        else:
            content = values[2]

        return {'status_code':200,
                'content':content}


    with HTTMock(httpMocker):
        try:
            feds = values[3](**values[1])
        except:
            feds = values[3](*values[1])
        if values[3] != getSpecificTeam:
            assert isinstance(feds,list)
            for i in feds:
                assert isinstance(i,values[0])
        else:
            assert isinstance(feds,Team)
