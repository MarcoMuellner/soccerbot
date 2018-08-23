from django.db.utils import IntegrityError
from datetime import timedelta,timezone,datetime
import logging
import enum
from typing import List,Dict,Union
from pytz import utc,UTC

from api.calls import getSpecificTeam,getAllFederations,getAllCountries,getAllCompetitions,getAllMatches,getAllSeasons
from database.models import Federation,Competition,CompetitionWatcher,Season,Match
from discord_handler.liveMatch import LiveMatch
from discord_handler.client import toDiscordChannelName

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
        startTime=query.first().date - timedelta(hours=1),
        endTime=query.last().date + timedelta(hours=3),
        matchdayString = f"{watcher.competition.clear_name} Matchday {query.first().matchday}"
    )

def compDict(competition : CompetitionWatcher) ->Dict[str,Dict[str,Union[List[LiveMatch],str]]]:
    """
    Creates Matchday objects that in turn are used by the Scheduler to check which and where
    matches should be created. This function assumes that all relevant matches are already in the
    database.
    For a given competition, the data is split up into its matchdays, given by the api. From there
    it creates an entry into the dict, that represents the matchdays for a given competition.
    Each matchday has the following entries:
    - start: The datetime a matchday "starts". This is one hour before the first match of the matchday.
    - end: The datetime a matchday "ends". This is three hours after the last match of a the matchday has ended.
    - channel_name: The channel in which these matches will post their updates.
    - channel_created: A flag that shows if the channel is created or not. Convinience for users outside
    of this function
    - passedMatches,currentMatches,upcomingMatches: Lists containing the actual LiveMatch objects (representing)
    a single match). See the class docu for further explanation there. passedMatches are Matches that are already
    passed from the point at this function is called, upcomingMatches are the upcoming ones and currentMatches are the
    currently running ones.
    :param competition: The competition for which you want to add the games.
    :return:
    """
    comp_name = competition.competition.clear_name
    matchDict = {}
    matchDayList = competition.current_season.match_set.values_list('matchday', flat=True).distinct()
    for md in matchDayList:
        matchDict[md] = {}
        matchList = Match.objects.filter(matchday=md).filter(competition=competition.competition) \
            .filter(season=competition.current_season).order_by('date')
        passedTime = (datetime.utcnow() - timedelta(hours=3)).replace(tzinfo=UTC)
        upcomingTime = (datetime.utcnow() + timedelta(hours=3)).replace(tzinfo=UTC)

        matchDict[md]['start'] = (matchList.first().date - timedelta(hours=1)).replace(tzinfo=UTC)
        matchDict[md]['end'] = (matchList.last().date + timedelta(hours=3)).replace(tzinfo=UTC)
        matchDict[md]['channel_name'] = toDiscordChannelName(f"{comp_name} Matchday {md}")
        matchDict[md]['channel_created'] = False
        matchDict[md]['passedMatches'] = [LiveMatch(obj) for obj in matchList.filter(date__lt=passedTime)]
        matchDict[md]['currentMatches'] = [LiveMatch(obj) for obj in matchList.filter(date__gt=passedTime)
                                                           .filter(date__lt=upcomingTime)]
        matchDict[md]['upcomingMatches'] = [LiveMatch(obj) for obj in matchList.filter(date__gt=upcomingTime)]
    return matchDict

def getNextMatchDayObjects() -> Dict[str,Dict[str,Dict]]:
    """
    Returns all Matchday objects for the current season for all competitions monitored by
    CompetitionWatcher. See the compDict function for a more proper explanation.
    :return: List of Matchday Objects
    """
    matchDict = {}
    for competition in CompetitionWatcher.objects.all():
        matchDict[competition.competition.clear_name] = compDict(competition)
    return matchDict



def getCurrentMatches() -> List[Match]:
    """
    Returns a list of matches that are currently or soon played
    :return:
    """
    retList = []

    for i in CompetitionWatcher.objects.all():
        updateMatchesSingleCompetition(i.competition,i.current_season)
        queryLive = Match.objects.filter(competition=i.competition).filter(match_status=MatchStatus.Live.value)
        queryLineups = Match.objects.filter(competition=i.competition).filter(match_status=MatchStatus.LineUps.value)
        retList +=  queryLive | queryLineups
    return retList



