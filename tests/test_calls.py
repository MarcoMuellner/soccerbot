import pytest
from soccerbot.api.calls import *

def testGetFederations():
    result = getFederations()
    assert isinstance(result,dict)