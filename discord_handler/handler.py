from database.models import *
from discord import Message, Server


class DiscordCmds:
    addComp = "!addCompetition"


def createChannel(match: Match):
    pass


def deleteChannel(match: Match):
    pass


def watchCompetition(competition, serverName):
    seasons = Season.objects.filter(competition=competition).order_by('start_date').first()
    server = DiscordServer(name=serverName)
    server.save()
    compWatcher = CompetitionWatcher(competition=competition,
                                     current_season=seasons, applicable_server=server, current_matchday=1)
    compWatcher.save()


def cmdHandler(msg: Message):
    if msg.content.startswith(DiscordCmds.addComp):
        parameterSplit = msg.content.split("-")
        data = parameterSplit[0].split(" ")
        competition_string = ""
        for i in data[1:]:
            if competition_string == "":
                competition_string += i
            else:
                competition_string += " " + i

        if len(data) < 2:
            return "Add competition needs the competition as a Parameter!"

        comp = Competition.objects.filter(clear_name=competition_string)

        if len(comp) == 0:
            return f"Can't find competition {competition_string}"

        if len(comp) != 1:
            if len(parameterSplit) == 1:
                names = [existing_com.clear_name for existing_com in comp]
                countryCodes = [existing_com.association for existing_com in comp]
                name_code = list(zip(names, countryCodes))
                return f"Found competitions {name_code} with that name. Please be more specific (add -ENG for example)."
            else:
                comp = Competition.objects.filter(clear_name=competition_string,association=parameterSplit[1])
                if len(comp) != 1:
                    names = [existing_com.clear_name for existing_com in comp]
                    countryCodes = [existing_com.association for existing_com in comp]
                    name_code = list(zip(names,countryCodes))
                    return f"Found competitions {name_code} with that name. Please be more specific (add -ENG for example)."

        watcher = CompetitionWatcher.objects.filter(competition=comp.first())

        if len(watcher) != 0:
            return f"Allready watching {competition_string}"

        watchCompetition(comp.first(), msg.server)

        return (f"Start watching competition {competition_string}")
