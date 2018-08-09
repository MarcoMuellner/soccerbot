from api.calls import *
from sqlite3 import IntegrityError
from django.db.utils import IntegrityError
from api.calls import getSpecificTeam
import datetime
from datetime import timedelta
import logging
import asyncio
import enum

logger = logging.getLogger(__name__)


class MatchDayObject:
    def __init__(self, startTime: datetime, endTime: datetime, matchdayString: str):
        self.startTime = startTime
        self.endTime = endTime
        self.matchdayString = matchdayString

class MatchStatus(enum.Enum):
    Played = 0
    ToBePlayed = 1
    Live = 3
    LineUps = 12
    Abandoned = 4
    Postponed = 7
    Cancelled = 8
    Suspended = 99


def getAndSaveData(func : callable, **kwargs):
    if len(kwargs) == 0:
        data = func()
    else:
        data = func(**kwargs)
    for i in data:
        try:
            i.save()
            if i._meta.label != 'database.Match':
                logger.debug(f"Saving {func.__name__}: {i}")
        except IntegrityError:
            if i._meta.label == 'database.Match':
                try:
                    home_team = getSpecificTeam(i.home_team_id)
                    away_team = getSpecificTeam(i.away_team_id)
                    home_team.save()
                    away_team.save()
                    i.save()
                except NameError:
                    pass
            elif i._meta.label == 'database.Competition':
                logger.warning(f"{i.association_id} has no country! Will not save country")
                continue
            else:
                raise IntegrityError(f"Foreign Key constraint failed for {i._meta.label}")

def updateCountries():
    logger.info("Updating countries")

    pass

def updateCompetitions():
    logger.info("Updating competitions")
    getAndSaveData(getFederations)
    getAndSaveData(getCountries)
    for federation in Federation.objects.all():
        getAndSaveData(getCompetitions, idFederation=federation.id)

    for watcher in CompetitionWatcher.objects.all():
        getAndSaveData(getSeasons, idCompetitions=watcher.competition.id)

def updateMatches():
    logger.info("Updating matches")
    for watcher in CompetitionWatcher.objects.all():
        for season in Season.objects.filter(competition=watcher.competition):
            logger.debug(f"Competition: {str(watcher.competition.clear_name.encode('utf-8'))}"
                         f",Season: {season.clear_name.encode('utf-8')}")
            updateMatchesSingleCompetition(competition=watcher.competition, season=season)

def updateMatchesSingleCompetition(competition : Competition, season : Season):
    logger.info(f"Updating {competition.clear_name}, season {season.clear_name}")
    getAndSaveData(getMatches, idCompetitions=competition.id, idSeason=season.id)

def createMatchDayObject(query,watcher):
    return MatchDayObject(
        startTime=query.first().date - timedelta(hours=3),
        endTime=query.last().date + timedelta(hours=5),
        matchdayString = f"{watcher.competition.clear_name} Matchday {query.first().matchday}"
    )

def getNextMatchDays() -> List[MatchDayObject]:
    today = datetime.datetime.now().today()
    tomorrow = today + timedelta(days=1)
    retList = []
    for i in CompetitionWatcher.objects.all():
        query = Match.objects.filter(competition=i.competition).filter(date__lte=tomorrow).filter(date__gte=today).order_by('date')

        if len(query) != 0:
            retList.append(createMatchDayObject(query,i))

        query = Match.objects.filter(competition=i.competition).filter(match_status=MatchStatus.Live.value)

        if len(query) != 0:
            retList.append(createMatchDayObject(query,i))
    return retList
