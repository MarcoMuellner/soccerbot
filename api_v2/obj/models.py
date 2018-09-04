from typing import Dict,Union,List,Tuple
from datetime import datetime,timedelta
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging
import asyncio
from dateutil.parser import parse

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
    def updateData() -> List:
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

        obj = Federation(
            id="FIFA",
            name="FIFA",
            full_name="Fédération Internationale de Football Association",
            address="")

        objs.append(obj)

        objs = Federation.saveData(Federation,objs)
        return objs

    @staticmethod
    async def updateRegularly(time: timedelta):
        MetaAPI.updateInternally(time, Federation.updateData)

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
    def updateData():
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

        objs = Country.saveData(Country,objs)
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
    def updateData() -> List:
        params = {
            'count': 1000,
            'footballType': 0
        }
        result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.competitions,params)
        objs = []

        for i in result:

            #Use confederations if competition has no associated country
            if len(i['IdMemberAssociation']) != 0 and i['IdMemberAssociation'] != '':
                country_id = i['IdMemberAssociation'][0]
            else:
                country_id = i['IdOwner']

            #Update data if it is not in Country objects
            if country_id not in [i.id for i in Country.objects.all()]:
                Country.updateData()

            #If it is still not available, set it to None
            try:
                country = Country.objects.get(id=country_id)
            except ObjectDoesNotExist:
                country = None

            if i['IdOwner'] not in [i.id for i in Federation.objects.all()]:
                Federation.updateData()

            federation = Federation.objects.get(id=i['IdOwner'])

            obj = Competition(
                id=i['IdCompetition'],
                federation = federation,
                country = country,
                name=i['Name'][0]['Description'],
                type=Competition.competitionType[i['CompetitionType']],
                gender=Competition.genderType[i['Gender']],
            )

            objs.append(obj)

        objs = Competition.saveData(Competition, objs)

        return objs

    def current_season(self):
        seasons = Season.objects.filter(competition=self).order_by('start_date')
        return seasons.last()


    def __str__(self):
        return f"{self.name} -> {self.federation}"

class Season(MetaAPI):
    id = models.IntegerField(primary_key=True, verbose_name="Id of the Seasons, according to API")
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, verbose_name="Competitions ID")
    name = models.CharField(max_length=255, verbose_name="Full name of the given season")
    start_date = models.DateTimeField(verbose_name="S tarting date of the season")
    end_date = models.DateTimeField(verbose_name="End date of the season")

    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Competition.objects.all()) == 0:
            Competition.updateData()

        objList = []
        for comp in Competition.objects.all():
            params = {
                'idCompetition': comp.id,
                'count': 1000
            }
            result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.seasons, params)

            for i in result:
                obj = Season(
                    id=i['IdSeason'],
                    competition=comp,
                    name=i['Name'][0]['Description'],
                    start_date=parse(i['StartDate']),
                    end_date=parse(i['EndDate'])
                    )
                objList.append(obj)

        objList = Season.saveData(Season,objList)
        return objList

    def __str__(self):
        return f"{self.name}: {self.federation}:{self.competition}"

class Team(MetaAPI):
    id = models.IntegerField(primary_key=True,verbose_name="ID of the team,according to API")
    country = models.ForeignKey(Country,verbose_name="Country that team belongs to",on_delete=models.CASCADE)
    name = models.CharField(max_length=1024,verbose_name="Name of the team")
    short_name = models.CharField(max_length=10,verbose_name="Short name of the team",null=True)


    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Country.objects.all()) == 0:
            Country.updateData()

        objList = []

        for country in Country.objects.all():
            params = {
                'count': 1000
            }
            result = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.teams.format(country.id), params)

            #passing confederation stuff, for which no standing is available
            if result == None and country.id in [i.id for i in Federation.objects.all()]:
                continue

            for i in result:
                obj = Team(
                    id = i['IdTeam'],
                    country = country,
                    name = i['Name'][0]['Description'],
                    short_name= i['ShortClubName']
                )
                objList.append(obj)

        Team.saveData(Team,objList)
    def __str__(self):
        return f"{self.name} in {self.country}"

class SeasonStats(MetaAPI):
    season = models.ForeignKey(Season,verbose_name="Season belonging to this stat",on_delete=models.CASCADE)
    rank = models.IntegerField(verbose_name="Rank of the team")
    team = models.ForeignKey(Team,verbose_name="Team of that rank",on_delete=models.CASCADE)
    games = models.IntegerField(verbose_name="Games played for that season")
    wins = models.IntegerField(verbose_name="Wins for that team")
    draws = models.IntegerField(verbose_name="Draws for that team")
    losses = models.IntegerField(verbose_name="Losses for that team")
    goals_scored = models.IntegerField(verbose_name="Goals scored by that team")
    goals_received = models.IntegerField(verbose_name="Goals received by that team")
    points = models.IntegerField(verbose_name="Points for that team")

    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Season.objects.all()) == 0:
            Season.updateData()

        if len(Team.objects.all()) == 0:
            Team.updateData()


        objList = []

        for competition in Competition.objects.all():
            result = MetaAPI.makeDataCall(MetaAPI.DataSrc.middleWare,MetaAPI.DataKey.standings.format(competition.id))
            season = competition.current_season()

            for i in result['standing']:
                team = Team.objects.filter(name=i['teamName'])

                if len(team) > 1:
                    logger.warning(f"Multiple teams found with {i['teamName']} namly {list(team)}")
                team = team.first()

                if team == None:
                    team = Team(id = i['idTeam']
                                ,country=competition.country
                                ,name=i['teamName']
                                ,short_name=i['teamShortName'])
                    team.save()

                obj = SeasonStats(
                    season = season,
                    rank = i['rank'],
                    team = team,
                    games= i['matches'],
                    wins = i['matchesWon'],
                    losses = i['matchesLost'],
                    draws = i['matchesDrawn'],
                    goals_scored= i['goalsFor'],
                    goals_received = i['goalsAgainst'],
                    points = i['points']

                )
                objList.append(obj)

        objList = SeasonStats.saveData(SeasonStats,objList)
        return objList

class Player(MetaAPI):
    id = models.IntegerField(primary_key=True,verbose_name="Id of player, according to API")
    name = models.CharField(max_length=256, verbose_name="Name of player")
    short_name = models.CharField(max_length=32,verbose_name="Short name of player")
    team = models.ForeignKey(Team,verbose_name="Team this player belongs to",on_delete=models.CASCADE)
    height = models.IntegerField(verbose_name="Height of player in cm")
    weight = models.IntegerField(verbose_name="Weight of player in kg")
    jersey_number = models.IntegerField(verbose_name="Jersey number of player")
    position = models.CharField(max_length=20,verbose_name="Position of player")
    birth_date = models.DateField(verbose_name="Birth date of the player")
    join_date = models.DateField(verbose_name="Join date of player")
    leave_date = models.DateField(verbose_name="Leave date of player")
    goals = models.IntegerField(verbose_name="Goals scored by player")
    yellow_cards = models.IntegerField(verbose_name="Yellow cards received by player")
    red_cards = models.IntegerField(verbose_name="Red cards received by player")
    imageLink = models.URLField(max_length=255, verbose_name="Link to the image of the player")
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Team.objects.all())) == 0:
            Team.updateData()

        wikiData = MetaAPI.makeDataCall(MetaAPI.DataSrc.soccerWiki,MetaAPI.WikiKey.playerData)

        objList = []
        for team in Team.objects.all():
            squad = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.squad.format(team.id))
            for player in squad:
                add_res = MetaAPI.makeDataCall(MetaAPI.DataSrc.api,MetaAPI.ApiKey.playerInfo.format(player['IdPlayer']))



class Calendar(MetaAPI):
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Season.objects.all()) == 0:
            Season.updateData()

class LiveMatch(MetaAPI):
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        pass


class TeamStats(MetaAPI):
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Team.objects.all())) == 0:
            Team.updateData()

class PlayerStats(MetaAPI):
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Player.objects.all())) == 0:
            Player.updateData()