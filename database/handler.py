from api.calls import *

def getAndSaveData(func,**kwargs):
    if len(kwargs) == 0:
        data = func()
    else:
        data = func(**kwargs)
    for i in data:
        i.save()

def updateDB():
    getAndSaveData(getFederations)
    for federation in Federation.objects.all():
        getAndSaveData(getCompetitions,idFederation=federation.id)

    for competition in Competition.objects.all():
        getAndSaveData(getSeasons,idCompetitions=competition.id)

    getAndSaveData(getTeams)

    for competition in Competition.objects.all():
        for season in Season.objects.filter(competition=competition):
            getAndSaveData(getMatches,idCompetitions=competition.id,idSeason=season.id)