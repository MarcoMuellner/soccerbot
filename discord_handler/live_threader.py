import json
import logging

logger = logging.getLogger(__name__)

class LiveMatch:
    def __init__(self):
        self.events = {"HomeTeam":
                      {"Goals":[],
                       "Bookings":[],
                       "Substitutions":[]
                       },
                  "AwayTeam":
                      {"Goals":[],
                       "Bookings":[],
                       "Substitutions":[]
                       }
                  }

    def loop(self):
        while True:
            data = None #getData from somewhere
            eventList = []
            eventList + self.parseTeam(data, 'HomeTeam')
            eventList + self.parseTeam(data, 'AwayTeam')

            for i in eventList:
                logger.info(i)


    def getMatchSettings(self):
        pass

    def parseTeam(self,contentDict,teamKeyWord):
        eventList = []

        parseList = [
            ("Goals",self.parseGoals),
            ("Bookings", self.parseGoals),
            ("Substitutions", self.parseGoals),
        ]

        for eventKeyword,func in parseList:
            eventList + self.parseEvent(contentDict,teamKeyWord,eventKeyword,func)

    def parseGoals(self,eventSet):
        pass

    def parseCards(self,eventSet):
        pass

    def parseSubstitions(self,eventSet):
        pass

    def getPlayerName(self,id):
        pass

    def parseEvent(self,contentDict,teamKeyWord,EventKeyword,func):
        if contentDict[teamKeyWord][EventKeyword] != self.events[teamKeyWord][EventKeyword]:
            #get the difference between the two lists!
            differential = [i for i in contentDict[teamKeyWord][EventKeyword] if i not in self.events[teamKeyWord][EventKeyword]]
            returnList = []
            for i in differential:
                returnList.append(func(i))
            return returnList
        else:
            return []
