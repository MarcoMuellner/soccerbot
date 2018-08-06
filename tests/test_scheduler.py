import pytest

from discord_handler.scheduler import *
from dateutil import parser


def testCalculateSleepTime():
    now = parser.parse("2018-07-29 09:00:00")
    later = parser.parse("2018-07-29 09:00:00")

    diff = (now-later).total_seconds()

    assert diff == calculateSleepTime(later,now)