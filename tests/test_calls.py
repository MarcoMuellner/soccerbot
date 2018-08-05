import pytest
from api.calls import *
from database.models import *

federationKeys = ["CONMEBOL",
                  "UEFA",
                  "AFC",
                  "OFC",
                  "CAF",
                  "CONCACAF"]

sampleCompetitionsKeys = [2000000019,#Bundesliga
                          2000000000,#Premier League
                          2000000026,#Seria A
                          2000000037,#La Liga
                         ]

sampleCompSeasonKeys = [(2000000019,2000011119)]

def testGetFederations():
    result = getFederations()
    assert isinstance(result,list)
    assert len(result) == 6
    for i in result:
        assert i.id in federationKeys
    resDict = {"IdConfederation":"Name","Name":[{"Description":"ClearName"}],"Dummy":"Dummy"}
    result = getFederations(resDict = resDict)
    assert isinstance(result,Federation)

@pytest.mark.parametrize("value",federationKeys)
def testGetCompetitions(value):
    result = getCompetitions(idFederation=value)
    assert isinstance(result, list)
    for i in result:
        assert isinstance(i,Competition)

@pytest.mark.parametrize("value",sampleCompetitionsKeys)
def testGetSeasons(value):
    result = getSeasons(idCompetitions = value)
    assert isinstance(result, list)
    for i in result:
        assert isinstance(i,Season)


def testGetTeams():
    result = getTeams()
    assert isinstance(result, list)
    for i in result:
        assert isinstance(i,Team)

@pytest.mark.parametrize("value",sampleCompSeasonKeys)
def testGetMatches(value):
    result = getMatches(idCompetitions = value[0],idSeason = value[1])
    assert isinstance(result, list)
    for i in result:
        assert isinstance(i,Match)
