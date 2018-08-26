from collections import OrderedDict
from texttable import Texttable
from json.decoder import JSONDecodeError
import logging
from typing import Tuple
from datetime import datetime
from dateutil import parser
from pytz import UTC

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
    except (KeyError,TypeError) as  e:
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

class PositionMatcher:
    pos = {
        0:"Goalkeeper",
        1:"Defender",
        2:"Midfielder",
        3:"Forward",
        4:"Unknown"
    }

def getPlayerInfo(playerName : str) -> Tuple[str,OrderedDict]:
    apiPlayer = playerName.replace(" ","+")
    try:
        params = {"name":apiPlayer}
        data = makeAPICall(ApiCalls.playerSearch,payload=params)
    except JSONDecodeError:
        return None

    if not isinstance(data,list):
        return None

    data = data[0]
    if len(data) == 0:
        return (playerName,OrderedDict())

    id = data['IdPlayer']
    name = data['Name'][0]['Description']

    try:
        data = makeAPICall(ApiCalls.playerInfo + f"/{id}/teams")
    except JSONDecodeError:
        return None

    addData = OrderedDict()

    for i in reversed(data):
        retString = f"Position: {PositionMatcher.pos[i['Position']]}\n"

        if "JerseyNum" in i.keys():
            retString += f"Jersey Number: {i['JerseyNum']}\n"

        if len(i['PositionLocalized']) != 0:
            retString += f"Position: {i['PositionLocalized'][0]['Description']}\n"

        statList ={
            "Goals":"Goals",
            "RedCards": "Red cards",
            "YellowCards": "Yellow cards",
            "MatchesPlayed": "Matches played",
        }

        for key,val in statList.items():
            if i[key] != None:
                retString +=f"{val}: {i[key]}\n"
            else:
                retString += f"{val}: 0\n"
        retString += f"Joined at {parser.parse(i['JoinDate']).strftime('%d %b %Y')}\n"
        if parser.parse(i['LeaveDate']) > datetime.utcnow().replace(tzinfo=UTC):
            retString += f"Contract running until {parser.parse(i['LeaveDate']).strftime('%d %b %Y')}\n"
        else:
            retString += f"Contract ran out at {parser.parse(i['LeaveDate']).strftime('%d %b %Y')}\n"

        try:
            teamData = makeAPICall(ApiCalls.specificTeam + f"/{i['IdTeam']}")
        except JSONDecodeError:
            return None

        addData[teamData['Name'][0]['Description']] = retString
    return name,addData
