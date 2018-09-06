from typing import Dict,Union,List,Tuple
from datetime import datetime,timedelta
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging
from dateutil.parser import parse
from unidecode import unidecode
import json

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
    country = models.ForeignKey(Country,verbose_name="Country that team belongs to",on_delete=models.CASCADE,null=True)
    name = models.CharField(max_length=1024,verbose_name="Name of the team")
    type = models.CharField(max_length=128,verbose_name="Team type",null = True)


    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Season.objects.all()) == 0:
            Season.updateData()

        objList = []
        result = MetaAPI.makeDataCall(MetaAPI.DataSrc.middleWare,MetaAPI.DataKey.teams)

        if len(Country.objects.all()) == 0:
            Country.updateData()

        for i in result['teams']:
            try:
                country = Country.objects.get(id=i['countryCode'])
            except ObjectDoesNotExist:
                country = None

            obj = Team(
                id = i['idTeam'],
                country = country,
                name = i['webName'],
                type = i['type']
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

    def __str__(self):
        return f"Stats {self.season}"

class Player(MetaAPI):
    class PosMatch:
        pos = {
            0: "Goalkeeper",
            1: "Defender",
            2: "Midfielder",
            3: "Forward",
            4: "Unknown"
        }
    id = models.IntegerField(primary_key=True,verbose_name="Id of player, according to API")
    name = models.CharField(max_length=256, verbose_name="Name of player")
    short_name = models.CharField(max_length=32,verbose_name="Short name of player")
    team = models.ForeignKey(Team,verbose_name="Team this player belongs to",on_delete=models.CASCADE,null=True)
    height = models.IntegerField(verbose_name="Height of player in cm")
    weight = models.IntegerField(verbose_name="Weight of player in kg")
    jersey_number = models.IntegerField(verbose_name="Jersey number of player",null=True)
    position = models.CharField(max_length=20,verbose_name="Position of player")
    birth_date = models.DateField(verbose_name="Birth date of the player",null=True)
    join_date = models.DateField(verbose_name="Join date of player",null=True)
    leave_date = models.DateField(verbose_name="Leave date of player",null=True)
    goals = models.IntegerField(verbose_name="Goals scored by player",null = True)
    yellow_cards = models.IntegerField(verbose_name="Yellow cards received by player",null=True)
    red_cards = models.IntegerField(verbose_name="Red cards received by player",null=True)
    imageLink = models.URLField(max_length=255, verbose_name="Link to the image of the player")
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Team.objects.all())) == 0:
            Team.updateData()

        wikiData = MetaAPI.makeDataCall(MetaAPI.DataSrc.soccerWiki,MetaAPI.WikiKey.playerData)
        names = [unidecode(f"{i.attrib['f']} {i.attrib['s']}") for i in wikiData]

        objList = []
        for competition in Competition.objects.all():
            season = competition.current_season()
            param = {
                "count":1000
            }
            if competition.country_id in Federation.objects.values_list('id', flat=True):
                continue

            squad = MetaAPI.makeDataCall(MetaAPI.DataSrc.api, MetaAPI.ApiKey.squad.format(competition.id,season.id),param)
            for i in squad:
                if int(i['IdSeason']) == season.id:
                    squad = i
                    break
            
            if len(squad) == 0:
                continue
            for player in squad['Players']:
                add_res = MetaAPI.makeDataCall(MetaAPI.DataSrc.api,MetaAPI.ApiKey.playerInfo.format(player['IdPlayer']))
                try:
                    try:
                        imageLink = wikiData[names.index(unidecode(add_res['Name'][0]['Description']))].attrib['i']
                        imageLink = "https://cdn.soccerwiki.org/images/player/"+imageLink
                    except ValueError:
                        firstLast = add_res['Name'][0]['Description'].split(" ")
                        firstLast = firstLast[0] +" " + firstLast[-1]
                        try:
                            imageLink = wikiData[names.index(unidecode(firstLast))].attrib['i']
                            imageLink = "https://cdn.soccerwiki.org/images/player/" + imageLink
                        except ValueError:
                            logger.warning(f"No image link for {add_res['Name'][0]['Description']}")
                            imageLink = ""
                except KeyError:
                    logger.warning(f"No image link for {add_res['Name'][0]['Description']}")
                    imageLink = ""

                try:
                    team = Team.objects.get(id=int(player['IdTeam']))
                except ObjectDoesNotExist:
                    team = None


                obj = Player(
                    id = add_res['IdPlayer'],
                    name = add_res['Name'][0]['Description'],
                    short_name = add_res['Alias'][0]['Description'],
                    team = team,
                    height = add_res['Height'],
                    weight = add_res['Weight'],
                    jersey_number = player['JerseyNum'],
                    position = Player.PosMatch.pos[player['RealPositionSide']],
                    birth_date = parse(player['BirthDate']) if player['BirthDate'] != None else None,
                    join_date = parse(player['JoinDate']) if player['JoinDate'] != None else None,
                    leave_date = parse(player['LeaveDate']) if player['LeaveDate'] != None else None,
                    goals = player['Goals'],
                    yellow_cards = player['YellowCards'],
                    red_cards = player['RedCards'],
                    imageLink = imageLink
                )
                objList.append(obj)
                break

        objList = Player.saveData(Player,objList)
        return objList

    def __str__(self):
        return f"{self.name} playing for {self.team}"

class Stage(MetaAPI):
    typeDict = {
        0:"KnockOut",
        1:"Group",
        2:"League",
        3:"Unknown"
    }

    id = models.IntegerField(primary_key=True,verbose_name="ID of stage, according to API")
    name = models.CharField(max_length=255,verbose_name="Name of stage",null=True)
    season = models.ForeignKey(Season,verbose_name="Season belonging to this stage",on_delete=models.CASCADE)
    start_date = models.DateField(verbose_name="Start date of stage")
    end_date = models.DateField(verbose_name="End date of stage")
    stage_type = models.CharField(max_length=10,verbose_name="Type of stage")
    stage_level = models.IntegerField(verbose_name="Stage level",null=True)

    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Season.objects.all())) == 0:
            Season.updateData()

        objList = []

        for competition in Competition.objects.all():
            season = competition.current_season()

            param = {"idCompetition":competition.id,
                     "idSeason":season.id,
                     "count":1000}

            data = MetaAPI.makeDataCall(MetaAPI.DataSrc.api,MetaAPI.ApiKey.stages,param)
            for i in data:
                try:
                    name = i['Name'][0]['Description']
                except IndexError:
                    name = None

                obj = Stage(
                    id = i['IdStage'],
                    name=name,
                    season = season,
                    start_date = parse(i['StartDate']),
                    end_date = parse(i['EndDate']),
                    stage_type = Stage.typeDict[i['Type']],
                    stage_level = i['StageLevel']
                )
                objList.append(obj)

        objList = Stage.saveData(Stage,objList)
        return objList

    def __str__(self):
        return f"Stage {self.name} for {self.season}"


class Group(MetaAPI):
    id = models.IntegerField(primary_key=True,verbose_name="Id according to API")
    stage = models.ForeignKey(Stage,verbose_name="Stage belonging to this group",on_delete=models.CASCADE)
    name = models.CharField(max_length=255,verbose_name="Name of group",null=True)
    description = models.CharField(max_length=1024,verbose_name="Description of group",null=True)
    start_date = models.DateField(verbose_name="Start date of group")
    end_date = models.DateField(verbose_name="End date of group")
    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if(len(Stage.objects.all())) == 0:
            Stage.updateData()

        objList = []

        for stage in Stage.objects.all():
            season = stage.season
            competition = season.competition

            param ={
                "idCompetition":competition.id,
                "idSeason":season.id,
                "idStage":stage.id,
                "counter":1000
            }
            data = MetaAPI.makeDataCall(MetaAPI.DataSrc.api,MetaAPI.ApiKey.groups,param)

            for i in data:

                try:
                    description = i['Description'][0]['Description']
                except IndexError:
                    description = None

                try:
                    name = i['Name'][0]['Description']
                except IndexError:
                    name = None


                obj = Group(
                    id=i['IdGroup'],
                    stage = stage,
                    name=name,
                    description=description,
                    start_date=parse(i['StartDate']),
                    end_date=parse(i['EndDate'])
                )

                objList.append(obj)

        objList = Group.saveData(Group,objList)
        return objList

    def __str__(self):
        return f"Group {self.name} for {self.stage}"

class Calendar(MetaAPI):
    id = models.IntegerField(primary_key=True,verbose_name="Id of the match, according to API")
    season = models.ForeignKey(Season,verbose_name="Season belonging to this match",on_delete=models.CASCADE)
    stage = models.ForeignKey(Stage,verbose_name="Stage this match belongs to",on_delete=models.CASCADE)
    group = models.ForeignKey(Group,verbose_name="Group this match belongs to",on_delete=models.CASCADE,null=True)
    weather = models.CharField(max_length=255,verbose_name="Weather information for the game",null=True)
    attendance = models.IntegerField(verbose_name="Attendance for the game",null=True)
    matchday = models.IntegerField(verbose_name="Matchday of the game",null=True)
    date = models.DateField(verbose_name="Date of the match")
    home_team = models.ForeignKey(Team,verbose_name="Home team",related_name="home_team",on_delete=models.CASCADE,null=True)
    away_team = models.ForeignKey(Team,verbose_name="Away team",related_name="away_team",on_delete=models.CASCADE,null=True)
    home_score = models.IntegerField(verbose_name="Goals for Home team",null=True)
    away_score = models.IntegerField(verbose_name="Goals for away team",null=True)
    leg = models.IntegerField(verbose_name="Leg of the game",null=True)
    stadium = models.CharField(max_length=1024,verbose_name="Stadium the match is played at",null=True)
    officials = models.CharField(max_length=2048,verbose_name="Officials for the game",null=True)
    home_lineup = models.CharField(max_length=8096,verbose_name="Home Lineup",null=True)
    away_lineup = models.CharField(max_length=8096,verbose_name="Away Lineup",null=True)
    events = models.CharField(max_length=16192,verbose_name="Match events",null=True)


    def __init__(self,*args,**kwargs):
        MetaAPI.__init__(self,*args,**kwargs)

    @staticmethod
    def updateData():
        if len(Group.objects.all()) == 0:
            Group.updateData()

        if len(Team.objects.all()) == 0:
            Team.updateData()

        objList = []

        for competition in Competition.objects.all():
            season = competition.current_season()

            param = {
                "idSeason":season.id,
                "idCompetition":competition.id,
                "count":1000

            }
            data = MetaAPI.makeDataCall(MetaAPI.DataSrc.api,MetaAPI.ApiKey.matches,param)
            for i in data:
                stage = Stage.objects.get(id=i['IdStage'])
                try:
                    group = Group.objects.get(id=i['IdGroup'])
                except ObjectDoesNotExist:
                    group = None
                try:
                    home_team = Team.objects.get(id=i['Home']['IdTeam'])
                except:
                    home_team = None
                try:
                    away_team = Team.objects.get(id=i['Away']['IdTeam'])
                except:
                    away_team = None
                try:
                    obj =Calendar(
                        id=i['IdMatch'],
                        season =season,
                        stage =stage,
                        group =group,
                        weather =json.dumps(i['Weather']),
                        attendance =i['Attendance'],
                        matchday =i['MatchDay'],
                        date =parse(i['Date']),
                        home_team =home_team,
                        away_team =away_team,
                        home_score =i['HomeTeamScore'],
                        away_score =i['AwayTeamScore'],
                        leg =i['Leg'],
                        stadium =json.dumps(i['Stadium']),
                        officials =json.dumps(i['Officials']),
                        home_lineup =None,
                        away_lineup =None,
                        events =None,
                        )
                except Exception as e:
                    print(i)

                objList.append(obj)

        objList = Calendar.saveData(Calendar,objList)
        return objList

    def __str__(self):
        return f"{self.home_team}:{self.away_team} for {self.season}"


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