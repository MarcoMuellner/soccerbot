from collections import OrderedDict

from database.models import Competition,Season
from database.handler import getAndSaveData
from api.calls import makeAPICall,getAllSeasons,ApiCalls

async def getTopScorers(competition : Competition) -> OrderedDict:
    season = Season.objects.filter(competition=competition)
    if season == None or len(season) == 0:
        getAndSaveData(getAllSeasons,idCompetitions=competition.id)
        season = Season.objects.filter(competition=competition)
        if season == None or len(season) == 0:
            raise ValueError(f"No season for {competition}")

    season = season.order_by('start_date').last()
    data = makeAPICall(ApiCalls.topScorer + f"/{season.id}/topscorers")

    addInfo = OrderedDict()
    try:
        for i in data['PlayerStatsList']:
            addInfo[i['PlayerInfo']['PlayerName'][0]['Description']] = i['GoalsScored']

        return addInfo
    except KeyError:
        return OrderedDict()