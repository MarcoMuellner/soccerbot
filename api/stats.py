from collections import OrderedDict
from texttable import Texttable
from json.decoder import JSONDecodeError
import logging

from database.models import Competition,Season
from database.handler import getAndSaveData
from api.calls import makeAPICall,getAllSeasons,ApiCalls,makeMiddlewareCall,DataCalls

logger = logging.getLogger(__name__)

async def getTopScorers(competition : Competition) -> OrderedDict:
    """
    Returns the topScorers for a given league by its competition.
    :param competition: competition Object. Needs to be valid, no further check is done
    :return: OrderedDict that can be directly fed into a CDOInternalResponse
    """
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
            goalStr = f"**Goals scored: __{i['GoalsScored']}__**\n"
            goalStr +=f"_Headers: __{i['GoalsScoredByHead']}__ _\n"
            goalStr +=f"_Penalties: __{i['GoalsScoredOnPenalty']}__ _\n"
            addInfo[f"{i['Rank']}.: "+ i['PlayerInfo']['PlayerName'][0]['Description']] = goalStr

        return addInfo
    except KeyError:
        return OrderedDict()

async def getLeagueTable(competition : Competition) -> str:
    """
    Creates a nicely structured league table for a given competition. Competition needs to be
    valid, no further check on that object is done
    :param competition: Competition for which you are looking for
    :return: string containing the league in a nicely formatted way
    """
    try:
        data = makeMiddlewareCall(DataCalls.standings+f"/{competition.id}")
    except JSONDecodeError:
        return ""
    table = Texttable()
    tableData = [["Rk","Team","M","W","L","D","Pts"]]

    for i in data['competitionsStanding'][0]['listStandings']:
        tableData.append([i['rank'],i['teamName'],i['matches'],i['matchesWon'],i['matchesLost'],
                          i['matchesDrawn'],i['points']])

    table.set_deco(Texttable.VLINES | Texttable.HEADER | Texttable.BORDER)
    table.set_cols_width([2, 20, 2, 2, 2, 2, 3])
    table.add_rows(tableData,True)
    logger.info(table.draw())

    return "```" + table.draw() + "```"