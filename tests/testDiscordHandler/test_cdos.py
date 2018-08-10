import pytest
from httmock import HTTMock

from discord_handler.cdos import *
from tests.testDatabase.test_handler import preUpdate
from tests.testAPI.test_calls import unifiedHttMock

def testCheckCompetitionParameter():
    result = checkCompetitionParameter("")
    assert isinstance(result,str)
    result = checkCompetitionParameter("dummy")
    assert isinstance(result, str)
    result = checkCompetitionParameter("!addCompetition")
    assert isinstance(result, str)
    result = checkCompetitionParameter("!addCompetition Bundesliga")
    assert isinstance(result,dict)
    assert result["competition"] == "Bundesliga"
    assert result["association"] == None
    result = checkCompetitionParameter("!addCompetition Bundesliga#GER")
    assert isinstance(result, dict)
    assert result["competition"] == "Bundesliga"
    assert result["association"] == "GER"

@pytest.mark.asyncio
def testCdoAddCompetition():
    with HTTMock(unifiedHttMock):
        pass


@pytest.mark.asyncio
def testCdoRemoveCompetition():
    with HTTMock(unifiedHttMock):
        pass

@pytest.mark.asyncio
def testCdoShowMonitoredCompetitions():
    with HTTMock(unifiedHttMock):
        pass

@pytest.mark.asyncio
def testCdoListCompetitionByCountry():
    with HTTMock(unifiedHttMock):
        pass

@pytest.mark.asyncio
def testCdoGetHelp():
    with HTTMock(unifiedHttMock):
        pass
