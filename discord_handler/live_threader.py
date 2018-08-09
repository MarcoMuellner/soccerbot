import json
import logging
from api.calls import makeMiddlewareCall, DataCalls,makeAPICall,ApiCalls
from database.models import Match
from database.handler import MatchStatus

import time

logger = logging.getLogger(__name__)


class LiveMatch:
    def __init__(self, matchid):
        self.events = []
        self.match = matchid

    def loop(self):
        while True:
            # api/v1/live/football/{idCompetition}/{idSeason}/{idStage}/{idMatch}
            data = makeMiddlewareCall(DataCalls.liveData+f"/{self.match}")

            eventList = self.parseEvents(data["match"]["events"])

            for i in eventList:
                print(i)

            if data["match"]["isFinished"]:
                print("Match finished!")
                break
            time.sleep(20)


    def parseEvents(self,data:list):
        retEvents = []
        if data != self.events:
            diff = [i for i in data if i not in self.events]
            for event in reversed(diff):
                if event['eventCode'] == 3: #Goal!
                    retEvents.append(f"{event['minute']}: Goal! {event['playerName']} scores for {event['teamName']}")
                elif event['eventCode'] == 4: #Substitution!
                    retEvents.append(f"{event['minute']}: Substition! {event['playerName']} changes for {event['playerToName']}")
                elif event['eventCode'] == 1:
                    retEvents.append(f"{event['minute']}: Yellow card for {event['playerName']}")
                elif event['eventCode'] == 14:
                    retEvents.append(f"{event['minute']}: End of the first half")
                elif event['eventCode'] == 13:
                    ret = f"{event['minute']}: Kickoff"
                    ret += " in the first half" if event['phaseDescriptionShort'] == "1H" else " in the second half"
                    retEvents.append(ret)
                else:
                    print(f"EventId {event['eventCode']} with descr {event['eventDescription']} not handled!")

            self.events = data
        return retEvents

    def getMatchSettings(self):
        pass
