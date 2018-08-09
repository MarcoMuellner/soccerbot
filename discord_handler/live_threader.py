import json
import logging
from api.calls import makeCall, ApiCalls
from database.models import Match
from database.handler import MatchStatus

import time

logger = logging.getLogger(__name__)


class LiveMatch:
    def __init__(self, match: Match):
        self.events = {"HomeTeam":
                           {"Goals": [],
                            "Bookings": [],
                            "Substitutions": []
                            },
                       "AwayTeam":
                           {"Goals": [],
                            "Bookings": [],
                            "Substitutions": []
                            }
                       }
        self.match = match

    def loop(self):
        while True:
            # api/v1/live/football/{idCompetition}/{idSeason}/{idStage}/{idMatch}
            data = makeCall(
                ApiCalls.liveMatch + f"/{self.match.competition.id}/{self.match.season.id}/{self.match.stage}/{self.match.id}")
            eventList = []
            eventList += self.parseTeam(data, 'HomeTeam')
            eventList += self.parseTeam(data, 'AwayTeam')

            for i in eventList:
                print(i)

            if data["MatchStatus"] != MatchStatus.Live.value:
                break
            time.sleep(20)

        print("Match ended")

    def getMatchSettings(self):
        pass

    def parseTeam(self, contentDict, teamKeyWord):
        eventList = []

        parseList = [
            ("Goals", self.parseGoals),
            ("Bookings", self.parseCards),
            ("Substitutions", self.parseSubstitions),
        ]

        for eventKeyword, func in parseList:
            eventList += self.parseEvent(contentDict, teamKeyWord, eventKeyword, func)

        return eventList

    def getPlayerName(self, id):
        result = makeCall(ApiCalls.playerInfo + f"/{id}")
        return result['Name'][0]['Description']

    def parseEvent(self, contentDict, teamKeyWord, EventKeyword, func):
        if contentDict[teamKeyWord][EventKeyword] != self.events[teamKeyWord][EventKeyword]:
            # get the difference between the two lists!
            differential = [i for i in contentDict[teamKeyWord][EventKeyword] if
                            i not in self.events[teamKeyWord][EventKeyword]]
            returnList = []
            for i in differential:
                returnList.append(func(i))

            self.events[teamKeyWord][EventKeyword] += differential

            return returnList
        else:
            return []

    def parseGoals(self, eventSet):
        #todo Team?
        try:
            return f"{eventSet['Minute']}:{self.getPlayerName(eventSet['IdPlayer'])} scored a goal!"
        except TypeError:
            return f"{eventSet['Minute']}: Goal "

    def parseCards(self, eventSet):
        #todo Team?
        try:
            return f"{eventSet['Minute']}:{eventSet['Card']} card for {self.getPlayerName(eventSet['IdPlayer'])}"
        except:
            return f"{eventSet['Minute']}:Card"

    def parseSubstitions(self, eventSet):
        #todo Team?
        try:
            return f"{eventSet['Minute']}: Substitution. {self.getPlayerName(eventSet['IdPlayerOff'])} is going off for {self.getPlayerName(eventSet['IdPlayerOn'])}"
        except:
            return f"{eventSet['Minute']}:Substitution"
