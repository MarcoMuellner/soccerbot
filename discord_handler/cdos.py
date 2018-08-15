import re
from typing import Dict, Union
import logging
from discord import Message, Channel, Embed
from collections import OrderedDict
from django.core.exceptions import ObjectDoesNotExist
import asyncio

from database.models import CompetitionWatcher, Competition, DiscordUsers, MatchEvents, MatchEventIcon
from discord_handler.handler import client, watchCompetition
from inspect import getmembers, isroutine
from support.helper import Task

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
emojiList = ["0⃣", "1⃣", "2⃣", "3⃣"]


class CommandoGroup:
    def __init__(self, group, fun: callable, docstring: str, userlevel: int = 0):
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
    def associateCommando(commando, group):
        for i in commandoGroups:
            if i.fun == group:
                i.associatedCommandos.append(commando)
                return i

    def __str__(self):
        return f"Group {self.group}, userLevel {self.userLevel}"


class DiscordCommando:
    def __init__(self, commando: str, fun: callable, docstring: str, group, userLevel: int):
        self.commando = commando
        self.cmd_group = CommandoGroup.associateCommando(self, group)
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

neededParameters = {'name': str,
                    'userLevel': int,
                    }


def markGroup(group: str):
    def internal_func_wrapper(func: callable):
        attributes = getmembers(func, lambda a: not (isroutine(a)))
        memberDescriptors = dict([a for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))])
        for name, valueType in neededParameters.items():
            if name not in memberDescriptors.keys():
                raise AttributeError(f"A group for a command has to implement {name}")

            try:
                valueType(memberDescriptors[name])
            except ValueError:
                raise AttributeError(f"The parameter {name} has to be of type {valueType}")
        CommandoGroup.addGroup(CommandoGroup(group, func, func.__doc__))
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
    def __init__(self, response: str = "", additionalInfo: OrderedDict = OrderedDict(), reactionFunc=None):
        self.response = response
        self.additionalInfo = additionalInfo
        self.reactionFunc = reactionFunc


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
        embObj.add_field(name=key, value=val, inline=True)

    await client.send_message(responseData.channel, embed=embObj)


def markCommando(cmd: str, group=GrpGeneral, userlevel=None):
    def internal_func_wrapper(func: callable):
        async def func_wrapper(**kwargs):
            responseDataInternal = await func(**kwargs)
            if not isinstance(responseDataInternal, CDOInteralResponseData):
                raise TypeError("Commandos need to return a CDOInteralResponseData type!")

            responseData = CDOFullResponseData(kwargs['msg'].channel, kwargs['cdo'], responseDataInternal)
            msg = await sendResponse(responseData)
            if responseDataInternal.reactionFunc is not None:
                await client.wait_for_reaction(message=msg, check=responseDataInternal.reactionFunc)
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
                          'userLevel': authorUserLevel}

                return await cdos.fun(**kwargs)
            else:
                responseStr = "I am sorry, you are not allowed to do that"
                responseData = CDOFullResponseData(msg.channel, cdos.commando, CDOInteralResponseData(responseStr))
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

@markGroup("Admin")
class GrpAdmin:
    """
    Admin group. Changing of behaviour should fall into this group.
    """
    userLevel = 0
    name = "Admin"


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
        responseData.response = "Error within Commando!"
        logger.error("Parameter is not string instance, please check logic!")
        return responseData
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
        return CDOInteralResponseData(f"Allready watching {competition_string}")

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
    retString = f"Monitored competitions (react with number emojis to remove.Only the first {len(emojiList)} can " \
                f"be added this way):\n\n"
    addInfo = OrderedDict()
    compList = []
    for watchers in CompetitionWatcher.objects.all():
        compList.append(watchers.competition.clear_name)
        try:
            addInfo[watchers.competition.association.clear_name].append(f"\nwatchers.competition.clear_name")
        except KeyError:
            addInfo[watchers.competition.association.clear_name] = watchers.competition.clear_name

    def check(reaction, user):
        if reaction.emoji in emojiList:
            index = emojiList.index(reaction.emoji)
            if index < len(compList):
                kwargs['msg'].content = f"!removeCompetition {compList[index]}"
                client.loop.create_task(cmdHandler(kwargs['msg']))
                return True
        return False

    return CDOInteralResponseData(retString, addInfo, check)


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
    compList = []

    for comp in competition:
        retString += comp.clear_name + "\n"
        compList.append(f"{comp.clear_name}#{comp.association.id}")

    retString += f"\n\nReact with according number emoji to add competitions. Only the first {len(emojiList)} can " \
                 f"be added this way"
    responseData.response = retString

    def check(reaction, user):
        if reaction.emoji in emojiList:
            try:
                index = emojiList.index(reaction.emoji)
            except ValueError:
                logger.error(f"{reaction.emoji} not in list!")
                return False
            if index < len(compList):
                kwargs['msg'].content = f"!addCompetition {compList[index]}"
                client.loop.create_task(cmdHandler(kwargs['msg']))
                return True
        return False

    responseData.reactionFunc = check
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


@markCommando("!changeEventIcons", GrpAdmin)
async def cdoChangeIcons(**kwargs):
    """
    Allows for changing of icons for match Events. The command with no parameters will return all events,
    with the event alone the currently set icon and with event and icon it will set the icon to the event.
    :return:
    """
    data = kwargs['msg'].content.split(" ")

    if len(data) == 1:
        responseString = "Available events:"
        addInfo = OrderedDict()
        for tag in MatchEvents:
            try:
                query = MatchEventIcon.objects.get(event=tag.value)
                val = query.eventIcon
            except ObjectDoesNotExist:
                val = "No icon set"

            addInfo[str(tag).replace("MatchEvents.", "")] = val
        return CDOInteralResponseData(responseString, addInfo)

    if len(data) == 2:
        for tag in MatchEvents:
            if data[1] in str(tag):
                try:
                    query = MatchEventIcon.objects.get(event=tag.value)
                    val = query.eventIcon
                except ObjectDoesNotExist:
                    val = "No icon set"
                return CDOInteralResponseData(f"**{data[1]}** : {val}")

        return CDOInteralResponseData(f"Event **{data[1]}** is not available")

    if len(data) == 3:
        for tag in MatchEvents:
            if data[1] in str(tag):
                MatchEventIcon(tag.value, data[2]).save()
                return CDOInteralResponseData(f"Set **{data[1]}** to {data[2]}")
        return CDOInteralResponseData(f"Event **{data[1]}** is not available")

    return CDOInteralResponseData()


@markCommando("!showRunningTasks", GrpAdmin)
async def cdoShowRunningTasks(**kwargs):
    """
    Shows all currently running tasks on the server
    :return:
    """
    tasks = Task.getAllTaks()
    responseString = "Running tasks:"
    addInfo = OrderedDict()

    for i in tasks:
        args = str(i.args).replace("<", "").replace(">", "").replace(",)", ")")
        addInfo[f"{i.name}{args}"] = f"Started at {i.time}"

    return CDOInteralResponseData(responseString, addInfo)


@markCommando("!test")
async def cdoTest(**kwargs):
    """
    Test Kommando
    :param kwargs:
    :return:
    """
    msg = await client.send_message(kwargs['msg'].channel, 'React with thumbs up or thumbs down.')

    def check(reaction, user):
        e = str(reaction.emoji)
        print(e)
        print(e == emojiList[0])
        return False

    res = await client.wait_for_reaction(message=msg, check=check)
    await client.send_message(kwargs['msg'].channel, '{0.user} reacted with {0.reaction.emoji}!'.format(res))
