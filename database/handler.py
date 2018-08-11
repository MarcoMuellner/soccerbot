from django.db.utils import IntegrityError
import datetime
from datetime import timedelta,timezone
import logging
import enum
from typing import List
from pytz import utc
from django.db.models import Q

from api.calls import getSpecificTeam,getAllFederations,getAllCountries,getAllCompetitions,getAllMatches,getAllSeasons
from database.models import Federation,Competition,CompetitionWatcher,Season,Match

logger = logging.getLogger(__name__)

class MatchStatus(enum.Enum):
    """
    Status as defined by Fifa API
    """
    Played = 0
    ToBePlayed = 1
    Live = 3
    LineUps = 12
    Abandoned = 4
    Postponed = 7
    Cancelled = 8
    Suspended = 99

class MatchDayObject:
    """
    Matchday object, representing the necessary data for Matchdays
    """
    def __init__(self, startTime: datetime, endTime: datetime, matchdayString: str):
        self.startTime = startTime
        self.endTime = endTime
        self.matchdayString = matchdayString

def getAndSaveData(func : callable, **kwargs):
    """
    Takes a getAll function defined in api.calls and iterates over the result, and storing the objects to the DB.
    It has various special handling functions, for example it looks up ForeignKeyErrors.
    :param func: Function to be executed and read from
    :param kwargs: parameters to the function, created as kwargs
    """
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

def updateOverlayData():
    """
    The relevant overlay data (Federations, Countries, Competitions and watched seasons) is refreshed from the API.
    """
    logger.info("Updating competitions")
    getAndSaveData(getAllFederations)
    getAndSaveData(getAllCountries)
    for federation in Federation.objects.all():
        getAndSaveData(getAllCompetitions, idFederation=federation.id)

    for watcher in CompetitionWatcher.objects.all():
        getAndSaveData(getAllSeasons, idCompetitions=watcher.competition.id)

def updateMatches():
    """
    Update the data for the matches stored as monitored in the database from the API.
    """
    logger.info("Updating matches")
    for watcher in CompetitionWatcher.objects.all():
        for season in Season.objects.filter(competition=watcher.competition):
            logger.debug(f"Competition: {str(watcher.competition.clear_name.encode('utf-8'))}"
                         f",Season: {season.clear_name.encode('utf-8')}")
            updateMatchesSingleCompetition(competition=watcher.competition, season=season)

def updateMatchesSingleCompetition(competition : Competition, season : Season):
    """
    Updates a single full competition. This reads all relevant matches of the given competition and season and stores
    it in the database
    :param competition: The relevant competition object from database.models
    :param season: The relevant season object from database.models
    """
    logger.info(f"Updating {competition.clear_name}, season {season.clear_name}")
    getAndSaveData(getAllMatches, idCompetitions=competition.id, idSeason=season.id)

def createMatchDayObject(query,watcher):
    """
    Creates a Matchday object from a query. It takes the delta between the earliest and latest match, plus some time
    at the borders to define a Matchday. It also generates a matchday from the name of the competition and its
    given matchday
    :param query: A query of matches consisting of database.models.Match objects
    :param watcher: The watcher (database.models.CompetitionWatcher) object
    :return: new MatchdayObject with start and endtime as well as the matchdaystring
    """
    return MatchDayObject(
        startTime=query.first().date - timedelta(hours=3),
        endTime=query.last().date + timedelta(hours=5),
        matchdayString = f"{watcher.competition.clear_name} Matchday {query.first().matchday}"
    )

def getNextMatchDayObjects() -> List[MatchDayObject]:
    """
    Returns the next matchday objects between the current (i.e. time that the function is called) time and +24 hours.
    It also creates Matchday objects for currently played games
    :return: List of Matchday Objects containing the next relevant Matchday objects
    """
    today = datetime.datetime.now(timezone.utc).today()
    tomorrow = today + timedelta(days=1)
    retList = []
    for i in CompetitionWatcher.objects.all():
        query = Match.objects.filter(competition=i.competition).filter(date__lte=utc.localize(tomorrow))\
            .filter(date__gte=utc.localize(today)).filter(~Q(match_status=MatchStatus.Live.value)).order_by('date')

        query = Match.objects.filter(competition=i.competition).filter(match_status=MatchStatus.Live.value) | query

        if len(query) != 0:
            retList.append(createMatchDayObject(query,i))

    return retList

def getCurrentMatches() -> List[Match]:
    """
    Returns a list of matches that are currently or soon played
    :return:
    """
    today = datetime.datetime.now(timezone.utc).today() -timedelta(hours=1)
    later = today + timedelta(hours=1)
    retList = []

    for i in CompetitionWatcher.objects.all():
        queryUpcoming = Match.objects.filter(competition=i.competition).filter(date__lte=utc.localize(later))\
            .filter(date__gte=utc.localize(today)).order_by('date').filter(~Q(match_status=MatchStatus.Live.value))

        queryLive = Match.objects.filter(competition=i.competition).filter(match_status=MatchStatus.Live.value)
        retList += queryUpcoming | queryLive
    return retList



