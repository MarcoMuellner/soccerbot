import requests
import json
from typing import Dict,List,Callable,Union
from datetime import datetime
from dateutil import parser

count = 1000

'''
def makeCall(keyword : str ,payload : Dict = {}) -> List:
    

def looping(keyword):
    def looping_decorator(func):
        def func_wrapper():
            result = makeCall(keyword[0],keyword[1])
            returnList = []

            for resDict in result:
                returnList.append(func(resDict))

            return returnList
        return func_wrapper
    return looping_decorator

@looping(ApiCalls.federations)
def getFederations(resDict):
    identifier = resDict['IdConfederation']
    clear_name = resDict['Name'][0]['Description']
    print(f'id: {identifier}, name: {clear_name}')

    return {'identifier':identifier,'clear_name':clear_name}
'''

class ApiCalls:
    api_home = 'https://api.fifa.com/api/v1/'

    federations = 'confederations'
    competitions ='competitions/all'
    seasons = 'seasons'
    matches = 'calendar/matches'
    teams = 'teams/all'

def loop(func:Callable,reqList)->List:
    returnList = []
    for resDict in reqList:
        returnList.append(func(resDict = resDict))

    return returnList

def makeCall(keyword : str,payload : Dict= {}) ->List:
    req = requests.get(ApiCalls.api_home + keyword, params=payload)
    return json.loads(req.content.decode())['Results']

def getFederations(**kwargs) -> Union[List,Dict]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.federations)
        return loop(getFederations,reqDict)

    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        identifier = kwargs['resDict']['IdConfederation']
        clear_name = kwargs['resDict']['Name'][0]['Description']
        return {'id': identifier, 'name': clear_name}
    else:
        raise AttributeError('Wrong parameters for call getFederations')

def getCompetitions(**kwargs) -> Union[List,Dict]:
    if 'idFederation' in kwargs.keys() and len(kwargs.keys()) == 1:
        payload = {
            'owner':kwargs['idFederation'],
            'count':1000,
            'footballType':0
        }
        reqDict = makeCall(ApiCalls.competitions,payload)
        return loop(getCompetitions,reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        identifier = int(kwargs['resDict']['IdCompetition'])
        clear_name = kwargs['resDict']['Name'][0]["Description"]
        idFederation = kwargs['resDict']["IdOwner"]
        return {'id': identifier, 'name': clear_name,"idFederation":idFederation}
    else:
        raise AttributeError('Wrong parameters for call getCompetitions')

def getSeasons(**kwargs) -> Union[List,Dict]:
    if 'idCompetitions' in kwargs.keys() and len(kwargs.keys()) == 1:
        payload = {
            'idCompetition':kwargs['idCompetitions'],
            'count':1000
        }
        reqDict = makeCall(ApiCalls.seasons,payload)
        return loop(getSeasons,reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        identifier = int(kwargs['resDict']['IdSeason'])
        idFederation = kwargs['resDict']['IdConfederation'][0]
        idCompetition = int(kwargs['resDict']['IdCompetition'])
        clear_name = kwargs['resDict']['Name'][0]['Description']
        start_date = parser.parse(kwargs['resDict']['StartDate'])
        end_date = parser.parse(kwargs['resDict']['EndDate'])

        return {'id': identifier,
                'name': clear_name,
                'idFederation': idFederation,
                'idCompetition':idCompetition,
                'start_date':start_date,
                'end_date':end_date}
    else:
        raise AttributeError('Wrong parameters for call getSeasons')

def getTeams(**kwargs) -> Union[List,Dict]:
    if len(kwargs.keys()) == 0:
        reqDict = makeCall(ApiCalls.teams)
        return loop(getTeams,reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        identifier = int(kwargs['resDict']['IdTeam'])
        clear_name = kwargs['resDict']['Name'][0]['Description']
        short_name = kwargs['resDict']['ShortClubName']
        return {'id':identifier,'name':clear_name,'short_name':short_name}
    else:
        raise AttributeError('Wrong parameters for call getTeams')

def getMatches(**kwargs) -> Union[List,Dict]:
    if 'idCompetitions' in kwargs.keys() and 'idSeason' in kwargs.keys() and len(kwargs.keys()) == 2:
        payload = {
            'idCompetition': kwargs['idCompetitions'],
            'idSeason':kwargs['idSeason'],
            'count': 1000
        }
        reqDict = makeCall(ApiCalls.matches, payload)
        return loop(getMatches,reqDict)
    elif 'resDict' in kwargs.keys() and len(kwargs.keys()) == 1:
        identifier = int(kwargs['resDict']['IdMatch'])
        idCompetition = int(kwargs['resDict']['IdCompetition'])
        idSeason = int(kwargs['resDict']['IdSeason'])
        home_team_id = int(kwargs['resDict']['Home']['IdTeam'])
        away_team_id = int(kwargs['resDict']['Away']['IdTeam'])
        matchday = int(kwargs['resDict']['MatchDay'])
        date = parser.parse(kwargs['resDict']['Date'])
        score_home_team =  None if kwargs['resDict']['HomeTeamScore'] == None else int(
            kwargs['resDict']['HomeTeamScore'])
        score_away_team = None if kwargs['resDict']['AwayTeamScore'] == None else int(
            kwargs['resDict']['AwayTeamScore'])

        return {'id':identifier,
                'idCompetition':idCompetition,
                'idSeason':idSeason,
                'idHomeTeam':home_team_id,
                'idAwayTeam':away_team_id,
                'matchday':matchday,
                'date':date,
                'score_home_team':score_home_team,
                'score_away_team':score_away_team}
    else:
        raise AttributeError('Wrong parameters for call getMatches')