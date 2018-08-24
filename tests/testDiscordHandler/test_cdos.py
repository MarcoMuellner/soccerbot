import pytest
from httmock import HTTMock

from discord_handler.cdo_meta import getParameters
from tests.testDatabase.test_handler import preUpdate
from tests.testAPI.test_calls import unifiedHttMock

def testCheckCompetitionParameter():
    result = getParameters("")
    assert isinstance(result,dict)
    result = getParameters("dummy")
    assert isinstance(result, dict)
    result = getParameters("!addCompetition")
    assert isinstance(result, dict)
    result = getParameters("!addCompetition Bundesliga")
    assert isinstance(result,dict)
    assert result["parameter0"] == "Bundesliga"
    assert "parameter1"not in result.keys()
    result = getParameters("!addCompetition Bundesliga,GER")
    assert isinstance(result, dict)
    assert result["parameter0"] == "Bundesliga"
    assert result["parameter1"] == "GER"

"""
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
"""