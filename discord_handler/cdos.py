import re
from typing import Dict,Union
import logging
from support.helper import log_return,DiscordCommando
from discord import Message
from database.models import CompetitionWatcher,Competition
from discord_handler.handler import watchCompetition

logger = logging.getLogger(__name__)

def checkCompetitionParameter(cmdString : str) ->Union[Dict,str]:
    parameterSplit = cmdString.split("#")
    data = parameterSplit[0].split(" ")
    competition_string = ""

    for i in data[1:]:
        if competition_string == "":
            competition_string += i
        else:
            competition_string += " " + i

    logger.debug(f"Competition: {competition_string}, full: {parameterSplit}")

    if len(data) < 2:
        return "Add competition needs the competition as a Parameter!"

    try:
        return {"competition":competition_string,"association":parameterSplit[1]}
    except IndexError:
        return {"competition": competition_string, "association": None}

@log_return
async def cdoAddCompetition(msg: Message):
    """
    Adds a competition to be watched by soccerbot. It will be regularly checked for new games

    :DiscordCommando: !addCompetition
    :param msg: message from Discord Server
    :return: Answer message
    """
    logger.info(f"Handling {DiscordCmds.addComp}")

    parameter = checkCompetitionParameter(msg.content)

    if isinstance(parameter,str):
        return parameter
    else:
        competition_string = parameter["competition"]
        association = parameter["association"]


    comp = Competition.objects.filter(clear_name=competition_string)

    logger.debug(f"Available competitions: {comp}")

    if len(comp) == 0:
        return f"Can't find competition {competition_string}"

    if len(comp) != 1:
        if association == None:
            names = [existing_com.clear_name for existing_com in comp]
            countryCodes = [existing_com.association for existing_com in comp]
            name_code = list(zip(names, countryCodes))
            return f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."
        else:
            comp = Competition.objects.filter(clear_name=competition_string, association=association)
            if len(comp) != 1:
                names = [existing_com.clear_name for existing_com in comp]
                countryCodes = [existing_com.association for existing_com in comp]
                name_code = list(zip(names, countryCodes))
                return f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."

    watcher = CompetitionWatcher.objects.filter(competition=comp.first())

    logger.debug(f"Watcher objects: {watcher}")

    if len(watcher) != 0:
        return f"Allready watching {competition_string}"

    await watchCompetition(comp.first(), msg.server)

    return (f"Start watching competition {competition_string}")

@log_return
async def cdoRemoveCompetition(msg : Message):
    """
    Removes a competition from the watchlist.

    :DiscordCommando: !removeCompetition
    :param msg: message from Discord Server
    :return: Answer message
    """
    parameter = checkCompetitionParameter(msg.content)
    if isinstance(parameter,str):
        return parameter
    else:
        competition_string = parameter["competition"]
        association = parameter["association"]

    watcher = CompetitionWatcher.objects.filter(competition__clear_name=competition_string)

    if len(watcher) == 0:
        return f"Competition {competition_string} was not monitored"

    if len(watcher) > 1:
        watcher = watcher.filter(competition__association=association)

    logger.info(f"Deleting {watcher}")
    watcher.delete()
    return f"Removed {competition_string} from monitoring"

@log_return
async def cdoShowMonitoredCompetitions():
    """
    Lists all watched competitions by soccerbot.

    :DiscordCommando: !monitoredCompetitions
    :return: Answer message
    """
    retString = "Monitored competitions:\n\n"
    for watchers in CompetitionWatcher.objects.all():
        retString += f"Competition: {watchers.competition.clear_name}\n"
    return retString

@log_return
async def cdoGetHelp():
    """
    Returns all available Commandos and their documentation.

    :DiscordCommando: !help
    :return:
    """
    retString = "Available Commandos:\n"
    for i in DiscordCommando.allCommandos():
        retString += i.commando +":\n"
        doc = i.docstring
        doc = re.sub(':.+\n',"",doc)
        doc = re.sub('\n+',"",doc)
        retString += doc + "\n\n"
    return retString