from typing import Dict,List,Union
from datetime import datetime, timedelta
import inspect
import requests
import json
import re
from django.db import models
import asyncio
import xml.etree.ElementTree as ET

class MetaAPI(models.Model):
    """
    Meta API represents the basic class that every API object is derived off. It shows
    a general interface, that should be implemented by all classes of this type, as well
    as providing some general data, like the urls for the APIs.

    All API objects have to integrate static methods, that return objects of that type.
    This needs to be filterable as well, by all members available.
    """
    class Meta: #abstract class for django
        abstract = True

    class DataSrc:
        api = "https://backend.fifa.com/backend/v1/"
        middleWare = "https://data.fifa.com/"
        soccerWiki = 'http://c3420952.r52.cf0.rackcdn.com/'

    class ApiKey:
        federations = 'confederations'
        competitions = 'competitions/all'
        seasons = 'seasons'
        matches = 'calendar/matches'
        teams = 'teams/association/{}'
        specificTeam = 'teams'
        playerInfo = 'players/{}'
        countries = 'countries'
        live = "live/football"
        teamSearch = "teams/search"
        topScorer = "topseasonplayerstatistics/season"
        playerSearch = 'players/search'
        squad = 'teams/squads/all/{}/{}'
        stages = 'stages'
        groups = 'competitiongroups'

    class DataKey:
        liveData = "matches/en/live/info"
        standings = "livescores/de/standing/byphase/{}"
        teams = "livescores/en/teams"

    class WikiKey:
        playerData = "playerdata.xml"

    def __init__(self,*args,**kwargs):
        #Write model
        models.Model.__init__(self, *args, **kwargs)

    @staticmethod
    def makeDataCall(src : str, keyword: str ,params : Dict[str,Union[str,int]] = None) -> Union[List,Dict]:
        """
        This method should make the actual data call to the backend.
        :param url: The full URL of the API
        :param params: The parameter for the get call.
        :return: The data from the API
        """

        params = params if params != None else {}
        req = requests.get(src + keyword, params=params)

        if req.status_code == 404:
            raise requests.exceptions.HTTPError(f"404 error returned by {req.url}")

        if src == MetaAPI.DataSrc.soccerWiki:
            dataList = ET.ElementTree(ET.fromstring(req.text))
            return dataList.getroot()[0].getchildren()
        else:
            try:
                data = req.content.decode()
                data = re.sub(r"_\w+\(", "", data)
                data = data.replace(")", "")
                try:
                    return json.loads(data)['Results']
                except (KeyError, TypeError) as e:
                    return json.loads(data)
            except json.decoder.JSONDecodeError:
                raise ValueError(f"Failed to parse data for url {req.url}")

    @staticmethod
    async def updateRegularly(time : timedelta):
        """
        If an event loop is available, this method should be spawned, according to the
        delta time it should be updated at.
        :param time: The delta time this should be updated at
        :return:
        """
        raise NotImplementedError("Update regularly is not implemented!")

    @staticmethod
    def updateInternally(delta : timedelta, fun : callable):
        start_time = datetime.utcnow()
        while True:
            time = datetime.utcnow()
            if time - start_time > delta:
                fun()
                start_time = datetime.utcnow()
            else:
                asyncio.sleep(300)

    def mem(self) -> Dict[str,property]:
        """
        Creates a dictionary containing all properties of a given API Object. These
        objects can be used to filter stuff.
        :return:
        """
        obj = inspect.getmembers(type(self),inspect.isdatadescriptor)
        del obj['__weakref__']
        return dict(obj)

    def checkDataAccess(self,**kwargs) -> bool:
        """
        Checks if the passed kwargs object contains only properties that are available
        through the Accessor
        :return: true/false, depending on if the things are correct
        """
        inKeys = kwargs.keys()
        avKeys = self.mem().keys()
        return set(inKeys).issubset(avKeys)

    @staticmethod
    def saveData(classObj:models.Model , objectList : List) -> List:
        itList = [i for i in objectList if i not in classObj.objects.values_list('id', flat=True)]

        s = set(itList)
        bulkList = [i for i in objectList if i not in s]

        for i in itList:
            i.save()

        classObj.objects.bulk_create(bulkList)

        return objectList

    def __str__(self):
        raise NotImplementedError(f"{type(self)} need to implement the __str__ method")


