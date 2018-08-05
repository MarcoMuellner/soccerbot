import requests
import json
from typing import Dict, List, Callable, Union
from dateutil import parser


class ApiCalls:
    api_home = 'https://api.fifa.com/api/v1/'

    federations = 'confederations'
    competitions = 'competitions/all'
    seasons = 'seasons'
    matches = 'calendar/matches'
    teams = 'teams/all'


def loop(func: Callable, reqList) -> List:
    returnList = []
    for resDict in reqList:
        returnList.append(func(resDict=resDict))

    return returnList


def makeCall(keyword: str, payload: Dict = {}) -> List:
    req = requests.get(ApiCalls.api_home + keyword, params=payload)
    return json.loads(req.content.decode())['Results']


def getFederations(**kwargs) -> Union[List, Dict]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.federations)
        return loop(getFederations, reqDict)

    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return {
            "id": apiResults['IdConfederation'],
            "clear_name": apiResults['Name'][0]['Description']
        }
    else:
        raise AttributeError('Wrong parameters for call getFederations')


def getCompetitions(**kwargs) -> Union[List, Dict]:
    if 'idFederation' in kwargs.keys() and len(kwargs.keys()) == 1:
        payload = {
            'owner': kwargs['idFederation'],
            'count': 1000,
            'footballType': 0
        }
        reqDict = makeCall(ApiCalls.competitions, payload)
        return loop(getCompetitions, reqDict)

    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return {
            "id": int(apiResults['IdCompetition']),
            "federations_id": apiResults["IdOwner"],
            "clear_name": apiResults['Name'][0]["Description"]
        }
    else:
        raise AttributeError('Wrong parameters for call getCompetitions')


def getSeasons(**kwargs) -> Union[List, Dict]:
    if 'idCompetitions' in kwargs.keys() and len(kwargs.keys()) == 1:
        payload = {
            'idCompetition': kwargs['idCompetitions'],
            'count': 1000
        }
        reqDict = makeCall(ApiCalls.seasons, payload)
        return loop(getSeasons, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return {
            "id": int(apiResults['IdSeason']),
            "federations_id": apiResults['IdConfederation'][0],
            "competitions_id": int(apiResults['IdCompetition']),
            "clear_name": apiResults['Name'][0]['Description'],
            "start_date": parser.parse(apiResults['StartDate']),
            "end_date": parser.parse(apiResults['EndDate'])
        }
    else:
        raise AttributeError('Wrong parameters for call getSeasons')


def getTeams(**kwargs) -> Union[List, Dict]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.teams)
        return loop(getTeams, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return {
            "id": int(apiResults['IdTeam']),
            "clear_name": apiResults['Name'][0]['Description'],
            "short_name": apiResults['ShortClubName']
        }
    else:
        raise AttributeError('Wrong parameters for call getTeams')


def getMatches(**kwargs) -> Union[List, Dict]:
    if 'idCompetitions' in kwargs.keys() and 'idSeason' in kwargs.keys() and len(kwargs.keys()) == 2:
        payload = {
            'idCompetition': kwargs['idCompetitions'],
            'idSeason': kwargs['idSeason'],
            'count': 1000
        }
        reqDict = makeCall(ApiCalls.matches, payload)
        return loop(getMatches, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return {
            "id": int(apiResults['IdMatch']),
            "competitions_id": int(apiResults['IdCompetition']),
            "seasons_id": int(apiResults['IdSeason']),
            "home_team_id": int(apiResults['Home']['IdTeam']),
            "away_team_id": int(apiResults['Away']['IdTeam']),
            "matchday": int(apiResults['MatchDay']),
            "date": parser.parse(apiResults['Date']),
            "score_home_team": None if apiResults['HomeTeamScore'] == None else int(
                apiResults['HomeTeamScore']),
            "score_away_team": None if apiResults['AwayTeamScore'] == None else int(
                apiResults['AwayTeamScore'])
        }
    else:
        raise AttributeError('Wrong parameters for call getMatches')
