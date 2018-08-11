import re
from typing import Dict, Union
import logging
from discord import Message, Channel, Embed
from collections import OrderedDict
from django.core.exceptions import ObjectDoesNotExist

from database.models import CompetitionWatcher, Competition, DiscordUsers
from discord_handler.handler import client, watchCompetition
from inspect import getmembers,isroutine

logger = logging.getLogger(__name__)

"""
Concering commandos: Commandos are automatically added by marking it with the markCommando decorator. This 
decorator also has as a parameter the given Commando that is wished to be used for this Commando. Commandos in 
general get a kwargs object, containing the message and commando, which can be used. It has to return a 
CDOInternalResponseData object, which is used for its response to the channel.

All commandos belong to a certain group and has a certain userlevel associated to it. If no group is explicitly 
associated, it will use the GrpGeneral object as its group. Also, if no userlevel is associated to a commando,
the userlevel of the group is used.
"""

discordCommandos = []
commandoGroups = []

class CommandoGroup:
    def __init__(self, group , fun : callable, docstring : str, userlevel : int = 0 ):
        self.group = group
        self.fun = fun
        self.docstring = docstring
        self.userLevel = userlevel
        self.associatedCommandos = []

    @staticmethod
    def allGroups():
        return commandoGroups

    @staticmethod
    def addGroup(group):
        logger.info(f"Adding group {group}")
        commandoGroups.append(group)

    @staticmethod
    def associateCommando(commando,group):
        for i in commandoGroups:
            if i.fun == group:
                i.associatedCommandos.append(commando)
                return i

    def __str__(self):
        return f"Group {self.group}, userLevel {self.userLevel}"


class DiscordCommando:
    def __init__(self, commando: str, fun : callable, docstring : str, group, userLevel : int):
        self.commando = commando
        self.cmd_group = CommandoGroup.associateCommando(self,group)
        self.userLevel = userLevel if userLevel is not None else self.cmd_group.userLevel
        self.fun = fun
        self.docstring = docstring

    @staticmethod
    def allCommandos():
        return discordCommandos

    @staticmethod
    def addCommando(commando):
        logger.info(f"Add commando {commando}")
        discordCommandos.append(commando)

    def __str__(self):
        return f"Cmd {self.cmd_group}:{self.commando}, userLevel {self.userLevel}"



################################### Group Helpers #####################################

neededParameters = {'name':str,
                    'userLevel':int,
                    }

def markGroup(group : str):
    def internal_func_wrapper(func:callable):
        attributes = getmembers(func, lambda a:not(isroutine(a)))
        memberDescriptors = dict([a for a in attributes if not(a[0].startswith('__') and a[0].endswith('__'))])
        for name,valueType in neededParameters.items():
            if name not in memberDescriptors.keys():
                raise AttributeError(f"A group for a command has to implement {name}")

            try:
                valueType(memberDescriptors[name])
            except ValueError:
                raise AttributeError(f"The parameter {name} has to be of type {valueType}")
        CommandoGroup.addGroup(CommandoGroup(group,func,func.__doc__))
        return func
    return internal_func_wrapper

@markGroup("General")
class GrpGeneral:
    """
    This is the default group. Contains all commandos that are available to everyone on the server.
    """
    userLevel = 0
    name = "General"
################################### Commandos Helpers ########################################

class CDOInteralResponseData:
    def __init__(self, response: str = "", additionalInfo: OrderedDict = OrderedDict()):
        self.response = response
        self.additionalInfo = additionalInfo


class CDOFullResponseData:
    def __init__(self, channel: Channel, cdo: str, internalResponse: CDOInteralResponseData):
        self.channel = channel
        self.cdo = cdo
        self.response = internalResponse.response
        self.additionalInfo = internalResponse.additionalInfo

    def __str__(self):
        return f"Posting {self.response} to {self.cdo} with addInfo {self.additionalInfo} to {self.channel}"

async def sendResponse(responseData):
    logger.info(responseData)
    title = f"Commando {responseData.cdo}"
    content = responseData.response

    embObj = Embed(title=title, description=content)

    for key, val in responseData.additionalInfo.items():
        embObj.add_field(name=key, value=val)

    await client.send_message(responseData.channel, embed=embObj)

def markCommando(cmd : str, group = GrpGeneral, userlevel = None):
    def internal_func_wrapper(func: callable):
        async def func_wrapper(**kwargs):
            responseData = await func(**kwargs)
            if not isinstance(responseData, CDOInteralResponseData):
                raise TypeError("Commandos need to return a CDOInteralResponseData type!")

            responseData = CDOFullResponseData(kwargs['msg'].channel, kwargs['cdo'], responseData)
            await sendResponse(responseData)
            return

        DiscordCommando.addCommando(DiscordCommando(cmd, func_wrapper, func.__doc__, group, userlevel))
        return func_wrapper

    return internal_func_wrapper


async def cmdHandler(msg: Message) -> str:
    """
    Receives commands and handles it according to allCommandos. Commandos are automatically parsed from the code.
    :param msg: message from the discord channel
    :return:
    """
    for cdos in DiscordCommando.allCommandos():
        if msg.content.startswith(cdos.commando):
            if msg.author.bot:
                logger.info("Ignoring {msg.content}, because bot")
                return

            try:
                userQuery = DiscordUsers.objects.get(id=msg.author.id)
                authorUserLevel = userQuery.userLevel
            except ObjectDoesNotExist:
                authorUserLevel = 0


            if cdos.userLevel <= authorUserLevel:
                logger.info(f"Handling {cdos.commando}")
                kwargs = {'cdo': cdos.commando,
                          'msg': msg,
                          'userLevel':authorUserLevel}

                return await cdos.fun(**kwargs)
            else:
                responseStr = "I am sorry, you are not allowed to do that"
                responseData = CDOFullResponseData(msg.channel,cdos.commando,CDOInteralResponseData(responseStr))
                await sendResponse(responseData)


def checkCompetitionParameter(cmdString: str) -> Union[Dict, str]:
    """
    Reads competition parameters, i.e. competition and country code
    :param cmdString: string from message
    :return: Either error message or dict with competition string and country code
    """
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
        return {"competition": competition_string, "association": parameterSplit[1]}
    except IndexError:
        return {"competition": competition_string, "association": None}

################################### Commandos ########################################

@markCommando("!addCompetition")
async def cdoAddCompetition(**kwargs):
    """
    Adds a competition to be watched by soccerbot. It will be regularly checked for new games
    :return: Answer message
    """
    responseData = CDOInteralResponseData()
    parameter = checkCompetitionParameter(kwargs['msg'].content)

    if isinstance(parameter, str):
        return parameter
    else:
        competition_string = parameter["competition"]
        association = parameter["association"]

    comp = Competition.objects.filter(clear_name=competition_string)

    logger.debug(f"Available competitions: {comp}")

    if len(comp) == 0:
        responseData.response = f"Can't find competition {competition_string}"
        return responseData

    if len(comp) != 1:
        if association == None:
            names = [existing_com.clear_name for existing_com in comp]
            countryCodes = [existing_com.association for existing_com in comp]
            name_code = list(zip(names, countryCodes))
            responseData.response = f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."
            return responseData
        else:
            comp = Competition.objects.filter(clear_name=competition_string, association=association)
            if len(comp) != 1:
                names = [existing_com.clear_name for existing_com in comp]
                countryCodes = [existing_com.association for existing_com in comp]
                name_code = list(zip(names, countryCodes))
                responseData.response = f"Found competitions {name_code} with that name. Please be more specific (add #ENG for example)."
                return responseData

    watcher = CompetitionWatcher.objects.filter(competition=comp.first())

    logger.debug(f"Watcher objects: {watcher}")

    if len(watcher) != 0:
        return f"Allready watching {competition_string}"

    client.loop.create_task(watchCompetition(comp.first(), kwargs['msg'].server))
    responseData.response = f"Start watching competition {competition_string}"
    return responseData


@markCommando("!removeCompetition")
async def cdoRemoveCompetition(**kwargs):
    """
    Removes a competition from the watchlist.
    :return: Answer message
    """
    responseData = CDOInteralResponseData()
    parameter = checkCompetitionParameter(kwargs['msg'].content)
    if isinstance(parameter, str):
        return parameter
    else:
        competition_string = parameter["competition"]
        association = parameter["association"]

    watcher = CompetitionWatcher.objects.filter(competition__clear_name=competition_string)

    if len(watcher) == 0:
        responseData.response = f"Competition {competition_string} was not monitored"
        return responseData

    if len(watcher) > 1:
        watcher = watcher.filter(competition__association=association)

    logger.info(f"Deleting {watcher}")
    watcher.delete()
    responseData.response = f"Removed {competition_string} from monitoring"
    return responseData


@markCommando("!monitoredCompetitions")
async def cdoShowMonitoredCompetitions(**kwargs):
    """
    Lists all watched competitions by soccerbot.
    :return: Answer message
    """
    retString = "Monitored competitions:\n\n"
    addInfo = OrderedDict()
    for watchers in CompetitionWatcher.objects.all():
        try:
            addInfo[watchers.competition.association.clear_name].append(f"\nwatchers.competition.clear_name")
        except KeyError:
            addInfo[watchers.competition.association.clear_name] = watchers.competition.clear_name

    return CDOInteralResponseData(retString, addInfo)


@markCommando("!listCompetitions")
async def cdoListCompetitionByCountry(**kwargs):
    """
    Lists all competitions for a given country. Needs the name of the country of country code as
    a parameter.
    :return:
    """
    responseData = CDOInteralResponseData()
    data = kwargs['msg'].content.split(" ")

    if len(data) == 0:
        responseData.response = "List competition needs the country or countrycode as parameter"
        return responseData

    association = ""

    for i in data[1:]:
        if association == "":
            association += i
        else:
            association += " " + i

    competition = Competition.objects.filter(association__clear_name=association)

    if len(competition) == 0:
        competition = Competition.objects.filter(association_id=association)

    if len(competition) == 0:
        responseData.response = f"No competitions were found for {association}"
        return responseData

    retString = "Competitions:\n\n"

    for comp in competition:
        retString += comp.clear_name + "\n"

    responseData.response = retString
    return responseData


@markCommando("!help")
async def cdoGetHelp(**kwargs):
    """
    Returns all available Commandos and their documentation.
    :return:
    """
    retString = "Available Commandos:\n"
    addInfo = OrderedDict()
    for i in DiscordCommando.allCommandos():
        doc = i.docstring
        doc = re.sub(':.+\n', "", doc)
        doc = re.sub('\n+', "", doc)
        addInfo[i.commando] = doc

    return CDOInteralResponseData(retString, addInfo)
