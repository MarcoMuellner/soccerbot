import pytest
from soccerbot.api.calls import *

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
        assert i["id"] in federationKeys
        assert len(i) == 2
    resDict = {"IdConfederation":"Name","Name":[{"Description":"ClearName"}],"Dummy":"Dummy"}
    result = getFederations(resDict = resDict)
    assert isinstance(result,dict)
    assert "id" in result.keys()
    assert "clear_name" in result.keys()

@pytest.mark.parametrize("value",federationKeys)
def testGetCompetitions(value):
    result = getCompetitions(idFederation=value)
    assert isinstance(result, list)
    if value == "UEFA":
        identifier = [identifier['id'] for identifier in result]
        assert set(sampleCompetitionsKeys).issubset(identifier)

    for i in result:
        assert len(i) == 3

@pytest.mark.parametrize("value",sampleCompetitionsKeys)
def testGetSeasons(value):
    result = getSeasons(idCompetitions = value)
    assert isinstance(result, list)
    for i in result:
        assert len(i) == 6


def testGetTeams():
    result = getTeams()
    assert isinstance(result, list)
    for i in result:
        assert len(i) == 3

@pytest.mark.parametrize("value",sampleCompSeasonKeys)
def testGetMatches(value):
    result = getMatches(idCompetitions = value[0],idSeason = value[1])
    assert isinstance(result, list)
    for i in result:
        assert len(i) == 9
