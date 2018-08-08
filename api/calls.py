import requests
import json
from typing import Dict, List, Callable, Union
from dateutil import parser

from database.models import *

"""
TODO:
    -This whole thing could probably be rewritten through usage of specific api calls
    This would reduce the number of API calls in the future significantly.
"""


class ApiCalls:
    """
    Simple static class, that provides the keywords for the api calls
    """
    api_home = 'https://api.fifa.com/api/v1/'

    federations = 'confederations'
    competitions = 'competitions/all'
    seasons = 'seasons'
    matches = 'calendar/matches'
    teams = 'teams/all'
    specificTeam = 'teams/'


def loop(func: Callable, reqList : List) -> List:
    """
    Helper function, that iterates over a given result List from an Api call
    and adds the result by parsing it through the given func
    :param func: This function is called within the iteration. It should
    return the proper object that will be appended in the List.
    :param reqList: Result List from the Api call
    :return: A list containting model objects from django models
    """
    returnList = []
    for resDict in reqList:
        returnList.append(func(resDict=resDict))

    return returnList


def makeCall(keyword: str, payload: Dict = None) -> Union[List,Dict]:
    """
    Makes a call to the API using the requests library. Returns the machine
    readable result for further processing
    :param keyword: API keyword from ApiCalls, appended to ApiCalls.api_home
    :param payload: parameters for the API call
    :return: List or dict containing the data
    """
    params = payload if payload != None else {}
    req = requests.get(ApiCalls.api_home + keyword, params=params)
    try:
        return json.loads(req.content.decode())['Results']
    except KeyError:
        return json.loads(req.content.decode())


def getFederations(**kwargs) -> Union[List, Federation]:
    """
    Gets all Federations from the API.

    Structurally the same as all other initialize API functions. The initial call
    with empty kwargs starts the loop, the same function will be called again to
    actually parse the result.
    :param kwargs: Empty or resDict from loop
    :return: Full List of Federation objects or single Federation object.
    """
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
    """
    Gets all competitions for a given federation from the API

    Structurally the same as all other initialize API functions. The initial call
    with empty kwargs starts the loop, the same function will be called again to
    actually parse the result.
    :param kwargs: Either idFederation (Identifier for federation) or resDict from loop
    :return: Full List of Competition objects or single Competition object.
    """
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
            clear_name=apiResults['Name'][0]["Description"],
            association=apiResults['IdMemberAssociation'][0]
        )
        comp.federation_id = apiResults["IdOwner"]
        return comp
    else:
        raise AttributeError('Wrong parameters for call getCompetitions')


def getSeasons(**kwargs) -> Union[List, Season]:
    """
    Gets all seasons for a given competition from the API

    Structurally the same as all other initialize API functions. The initial call
    with empty kwargs starts the loop, the same function will be called again to
    actually parse the result.
    :param kwargs: Either idCompetitions (Identifier for the competition) or resDict from loop
    :return: Full list of Season objects or single Season object
    """
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
    """
    Gets 1000 teams from the API

    Structurally the same as all other initialize API functions. The initial call
    with empty kwargs starts the loop, the same function will be called again to
    actually parse the result.
    :param kwargs: Either empty or resDict from loop
    :return: Full list of Team objects, or single Team object
    :todo: this could probably be removed and simply call getSpecificTeam in updateDB
    """
    if len(kwargs.keys()) == 0:
        payload = {
            'count': 1000
        }
        reqDict = makeCall(ApiCalls.teams,payload=payload)
        return loop(getTeams, reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        apiResults = kwargs['resDict']
        return Team(
            id=int(apiResults['IdTeam']),
            clear_name=apiResults['Name'][0]['Description'],
            short_name=apiResults['ShortClubName']
        )

    else:
        raise AttributeError('Wrong parameters for call getTeams')

def getMatches(**kwargs) -> Union[List, Match]:
    """
    Gets 1000 matches from the API

    Structurally the same as all other initialize API functions. The initial call
    with empty kwargs starts the loop, the same function will be called again to
    actually parse the result.
    :param kwargs: either idCompetitions and id Season or resDict from loop
    :return: Full List of Match objects, or single Match object
    """
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
            matchday=None if apiResults['MatchDay'] == None else int(apiResults['MatchDay']),
            date=parser.parse(apiResults['Date']),
            score_home_team=None if apiResults['HomeTeamScore'] == None else int(
                apiResults['HomeTeamScore']),
            score_away_team=None if apiResults['AwayTeamScore'] == None else int(
                apiResults['AwayTeamScore']),
            match_status=apiResults['MatchStatus'],
            stage = apiResults['IdStage']
        )

        match.competition_id = int(apiResults['IdCompetition'])
        match.season_id = int(apiResults['IdSeason'])
        try:
            match.home_team_id = int(apiResults['Home']['IdTeam'])
        except TypeError:
            match.home_team_id = None

        try:
            match.away_team_id = int(apiResults['Away']['IdTeam'])
        except TypeError:
            match.away_team_id = None

        return match
    else:
        raise AttributeError('Wrong parameters for call getMatches')


def getSpecificTeam(teamID:int)->Team:
    """
    Due to the size restriction of the API, this function is needed if for a given
    match a Team is not yet in the database (Foreign Key error!). Returns a full
    team object for a given identifier
    :param teamID: Identifier of the team
    :return: Team object
    """
    reqDict = makeCall(ApiCalls.specificTeam+str(teamID))
    apiResults = reqDict
    return Team(
        id=int(apiResults['IdTeam']),
        clear_name=apiResults['Name'][0]['Description'],
        short_name=apiResults['ShortClubName']
    )
