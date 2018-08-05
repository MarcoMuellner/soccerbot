import requests
import json
from typing import Dict, List, Callable, Union
from dateutil import parser
from database.models import *


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


def getFederations(**kwargs) -> Union[List, Federation]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.federations)
        return loop(getFederations, reqDict)

    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return Federation(
            id=apiResults['IdConfederation'],
            clear_name=apiResults['Name'][0]['Description']
        )
    else:
        raise AttributeError('Wrong parameters for call getFederations')


def getCompetitions(**kwargs) -> Union[List, Competition]:
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
        comp = Competition(
            id=int(apiResults['IdCompetition']),
            clear_name=apiResults['Name'][0]["Description"]
        )
        comp.federation_id = apiResults["IdOwner"]
        return comp
    else:
        raise AttributeError('Wrong parameters for call getCompetitions')


def getSeasons(**kwargs) -> Union[List, Season]:
    if 'idCompetitions' in kwargs.keys() and len(kwargs.keys()) == 1:
        payload = {
            'idCompetition': kwargs['idCompetitions'],
            'count': 1000
        }
        reqDict = makeCall(ApiCalls.seasons, payload)
        return loop(getSeasons, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return Season(
            id=int(apiResults['IdSeason']),
            federation_id=apiResults['IdConfederation'][0],
            competition_id=int(apiResults['IdCompetition']),
            clear_name=apiResults['Name'][0]['Description'],
            start_date=parser.parse(apiResults['StartDate']),
            end_date=parser.parse(apiResults['EndDate'])
        )
    else:
        raise AttributeError('Wrong parameters for call getSeasons')


def getTeams(**kwargs) -> Union[List, Team]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.teams)
        return loop(getTeams, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        Team(
            id=int(apiResults['IdTeam']),
            clear_name=apiResults['Name'][0]['Description'],
            short_name=apiResults['ShortClubName']
        )
    else:
        raise AttributeError('Wrong parameters for call getTeams')


def getMatches(**kwargs) -> Union[List, Match]:
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
        match = Match(
            id=int(apiResults['IdMatch']),
            matchday=int(apiResults['MatchDay']),
            date=parser.parse(apiResults['Date']),
            score_home_team=None if apiResults['HomeTeamScore'] == None else int(
                apiResults['HomeTeamScore']),
            score_away_team=None if apiResults['AwayTeamScore'] == None else int(
                apiResults['AwayTeamScore'])
        )

        match.competition_id = int(apiResults['IdCompetition'])
        match.season_id = int(apiResults['IdSeason'])
        match.home_team_id = int(apiResults['Home']['IdTeam'])
        match.away_team_id = int(apiResults['Away']['IdTeam'])

        return match
    else:
        raise AttributeError('Wrong parameters for call getMatches')
