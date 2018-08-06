from database.models import *
from discord import Message,Server

class DiscordCmds:
    addComp = "!addCompetition"

def createChannel(match: Match):
    pass


def deleteChannel(match: Match):
    pass


def watchCompetition(competition,server):
    seasons = Season.objects.filter(competition=competition).order_by('start_date')
    compWatcher = CompetitionWatcher(competition,seasons[0],server.name)
    compWatcher.save()


def cmdHandler(msg: Message):
    if msg.content.startswith(DiscordCmds.addComp):
        data = msg.content.split(" ")
        if len(data) != 2:
            return "Add competition needs the competition as a Parameter!"

        comp = Competition.objects.filter(clear_name=data[1])
        watcher = CompetitionWatcher.objects.filter(competition__in=comp)

        if len(watcher) != 0:
            return f"Allready watching {data[1]}"

        if len(comp) == 0:
            return f"Can't find competition {data[1]}"

        if len(comp) != 1:
            names = set(existing_com.clear_name for existing_com in comp)
            return f"Found competitions {names} with that name. Please be more specific"

        watchCompetition(comp,msg.server)

        return(f"Start watching competition {data[1]}")


