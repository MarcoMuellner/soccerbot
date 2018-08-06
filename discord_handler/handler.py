from database.models import *


def createChannel(match: Match):
    pass


def deleteChannel(match: Match):
    pass


def watchCompetition(competition):
    pass


def cmdHandler(msg: str):
    if msg.startswith("!addCompetition"):
        data = msg.split(" ")
        if len(data) != 2:
            return "Add competition needs the competition as a Parameter!"

