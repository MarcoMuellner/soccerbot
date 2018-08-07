from api.calls import *
from sqlite3 import IntegrityError
from django.db.utils import IntegrityError
from api.calls import getSpecificTeam
import datetime
from datetime import timedelta


class MatchDayObject:
    def __init__(self, startTime: datetime, endTime: datetime, matchdayString: str):
        self.startTime = startTime
        self.endTime = endTime
        self.matchdayString = matchdayString


def getAndSaveData(func, **kwargs):
    if len(kwargs) == 0:
        data = func()
    else:
        data = func(**kwargs)
    for i in data:
        try:
            i.save()
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
            else:
                raise IntegrityError(f"Foreign Key constraint failed for {i._meta.label}")


def updateDB():
    getAndSaveData(getFederations)
    for federation in Federation.objects.all():
        getAndSaveData(getCompetitions, idFederation=federation.id)

    for competition in Competition.objects.all():
        getAndSaveData(getSeasons, idCompetitions=competition.id)

    getAndSaveData(getTeams)

    for competition in Competition.objects.all():
        for season in Season.objects.filter(competition=competition):
            print(f"Competition: {competition.clear_name},Season: {season.clear_name}")
            getAndSaveData(getMatches, idCompetitions=competition.id, idSeason=season.id)


def getNextMatchDays() -> List[MatchDayObject]:
    today = datetime.datetime.now().today()
    tomorrow = today + timedelta(days=1)
    retList = []
    for i in CompetitionWatcher.objects.all():
        query = Match.objects.filter(competition=i).filter(date__lte=tomorrow).filter(date__gte=today).sort_by('date')

        startTime = query.first() - timedelta(hour=1)
        endTime = query.first() - timedelta(hour = 1)
        matchDayString = f"{i.clear_name} Matchday {query.first().matchday}"
        retList.append(MatchDayObject(startTime,endTime,matchDayString))

    return retList
