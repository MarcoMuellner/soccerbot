from typing import Dict,Union,List,Tuple
from datetime import datetime,timedelta
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging
import asyncio

from .Meta import MetaAPI
logger = logging.getLogger(__name__)

#####################################FEDERATION#################################

class Federation(MetaAPI):
    """
    Federation represents all information belonging to a single federation. This represents the root of all information.
    You should be able to get all infromation from this class.
    """
    id = models.CharField(primary_key=True, max_length=255, verbose_name="ID of federation")
    name = models.CharField(max_length=255, verbose_name="Short name of the federation")
    full_name = models.CharField(max_length=1024, verbose_name="Long name of the federation")
    address = models.CharField(max_length=1024, verbose_name="Address of the federation")

    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def initData(full : bool = False) -> List:
        result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.federations)
        objs = []
        for i in result:
            obj = Federation(
                id=i['IdConfederation'],
                name=i['Description'][0]['Description'],
                full_name= i['Name'][0]['Description'],
                address = i['Address']
            )
            objs.append(obj)
            if full:
                Competition.initData(obj,full)

        obj = Federation(
            id="FIFA",
            name="FIFA",
            full_name="Fédération Internationale de Football Association",
            address="")

        if full:
            compList = Competition.initData(obj, full)

        objs.append(obj)

        Federation.objects.bulk_create(objs)
        return objs

    @staticmethod
    async def updateRegularly(time: timedelta):
        MetaAPI.updateInternally(time,Federation.initData)

    @property
    def competitions(self):
        return Competition.objects.filter(federation=self)

    def __str__(self):
        return f"Federation {self.id}"


#####################################COUNTRY #################################
class Country(MetaAPI):
    id = models.CharField(primary_key=True, max_length=3, verbose_name="FIFA country code")
    name = models.CharField(max_length=255, verbose_name="Full Country Name")

    def __init__(self, *args, **kwargs):
        MetaAPI.__init__(self, *args, **kwargs)

    @staticmethod
    def initData():
        params = {
            'count': 1000
        }
        result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.countries, params)

        objs = []

        for i in result:
            obj = Country(
                id=i['IdCountry'],
                name=i['Name']
            )

            objs.append(obj)

        for fed in Federation.objects.all():
            objs.append(Country(id=fed.id, name=fed.name))

        Country.objects.bulk_create(objs)
        return objs

    def __str__(self):
        return f"Country: {self.name.encode('utf-8')}"

#####################################COMPETITION #################################
class Competition(MetaAPI):
    id = models.IntegerField(primary_key=True, verbose_name="Id of the competitions, according to API")
    federation = models.ForeignKey(Federation, on_delete=models.CASCADE, verbose_name="Federation ID")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name="Country of competition",null=True)
    name = models.CharField(max_length=255, verbose_name="Full name of the competition")
    type = models.CharField(max_length=255,verbose_name="Type of competition")
    gender = models.CharField(max_length=255, verbose_name="Gender of competition")

    competitionType = {
        1:"International competition",
        2:"National competition",
        3:"FIFA competition",
        4:"Unknown competition"
    }

    genderType = {
        1:"Male",
        2:"Female"
    }

    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def initData(federation : Federation, full : bool = False) -> List:
        params = {
            'owner': federation.id,
            'count': 1000,
            'footballType': 0
        }
        result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.competitions,params)
        objs = []

        for i in result:
            try:
                country_id = i['IdMemberAssociation'][0] if i['IdMemberAssociation'][0] != '' != 0 else i['IdOwner']
            except IndexError:
                country_id = i['IdOwner']
            try:
                country = Country.objects.get(id=country_id)
            except ObjectDoesNotExist:
                if len(Country.objects.all()) == 0:
                    Country.initData()
                try:
                    country = Country.objects.get(id=country_id)
                except ObjectDoesNotExist:
                    country = None

            obj = Competition(
                id=i['IdCompetition'],
                federation = federation,
                country = country,
                name=i['Name'][0]['Description'],
                type=Competition.competitionType[i['CompetitionType']],
                gender=Competition.genderType[i['Gender']],
            )

            objs.append(obj)

        Competition.objects.bulk_create(objs)

        return objs

    def __str__(self):
        return f"{self.name} -> {self.federation}"
