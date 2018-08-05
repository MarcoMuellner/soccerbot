import requests
import json
from enum import Enum
from typing import Dict,List

class ApiCalls:
    api_home = "https://api.fifa.com/api/v1/"

    federations = "confederations"
    competitions = "competitions/all"
    seasons = "seasons"
    matches = "calendar/matches"
    teams = "teams/all"

count = 1000


def makeCall(keyword : str ,payload : Dict = {}) -> List:
    req = requests.get(ApiCalls.api_home+keyword,params=payload)
    return json.loads(req.content.decode())["Results"]

def looping(keyword,payload={}):
    def looping_decorator(func):
        def func_wrapper():
            result = makeCall(ApiCalls.federations)
            returnList = []

            for resDict in result:
                returnList.append(func(resDict))

            return returnList
        return func_wrapper
    return looping_decorator

@looping
def getFederations(resDict):
    identifier = resDict["IdConfederation"]
    clear_name = resDict["Name"][0]["Description"]
    print(f"id: {identifier}, name: {clear_name}")

    return {'identifier':identifier,'clear_name':clear_name}

def getSeasons(resDict):
    pass