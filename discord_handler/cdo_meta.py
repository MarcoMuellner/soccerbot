from inspect import getmembers, isroutine
import logging
from typing import Dict, Callable, List
from collections import OrderedDict
from discord import Channel, Embed, Message, Reaction,User
from django.core.exceptions import ObjectDoesNotExist
import os
import json
from enum import Enum

from discord_handler.client import client
from database.models import DiscordUsers,Settings

logger = logging.getLogger(__name__)

discordCommandos = []
commandoGroups = []

class pageNav(Enum):
    forward = 1
    previous = 2

def emojiList():
    return ["0⃣",
            "1⃣",
            "2⃣",
            "3⃣"]

path = os.path.dirname(os.path.realpath(__file__))
try:
    with open(path+"/../secret.json") as f:
        masterUserID = json.loads(f.read())['masterUser']
except (KeyError,FileNotFoundError):
    logger.error(f"NO MASTER USER AVAILABLE")
    masterUserID = None



############################### Commandos and so on ##########################
class CommandoGroup:
    def __init__(self, group, fun: callable, docstring: str, userlevel: int = 0):
        self.group = group
        self.fun = fun
        self.docstring = docstring
        self.userLevel = userlevel
        self.associatedCommandos = []

    @staticmethod
    def allGroups() -> List:
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
    def allCommandos() -> List:
        return discordCommandos

    @staticmethod
    def addCommando(commando):
        logger.info(f"Add commando {commando}")
        discordCommandos.append(commando)

    def __str__(self):
        return f"Cmd {self.cmd_group}:{self.commando}, userLevel {self.userLevel}"


############################### Response objects ##########################

class CDOInteralResponseData:
    def __init__(self, response: str = "", additionalInfo: OrderedDict = OrderedDict(), reactionFunc=None, paging = None):
        self.response = response
        self.additionalInfo = additionalInfo
        self.reactionFunc = reactionFunc
        self.paging = paging


class CDOFullResponseData:
    def __init__(self, channel: Channel, cdo: str, internalResponse: CDOInteralResponseData):
        self.channel = channel
        self.cdo = cdo
        self.response = internalResponse.response
        self.paging = internalResponse.paging
        self.additionalInfo = internalResponse.additionalInfo

    def __str__(self):
        return f"Posting {self.response} to {self.cdo} with addInfo {self.additionalInfo} to {self.channel}"


############################### Meta functions ##########################

async def editPagingMessage(message : Message,embObj):
    await client.edit_message(message,embed=embObj)
    await resetPaging(message)

async def resetPaging(message : Message):
    await client.clear_reactions(message)
    await client.add_reaction(message=message, emoji='⏪')
    await client.add_reaction(message=message, emoji='⏩')

def getEmbObj(responseData):
    title = f"Commando {responseData.cdo}"
    content = responseData.response

    embObj = Embed(title=title, description=content)

    for key, val in responseData.additionalInfo.items():
        embObj.add_field(name=key, value=val, inline=True)

    return embObj

async def sendResponse(responseData):
    logger.info(responseData)

    embObj = getEmbObj(responseData)

    return await client.send_message(responseData.channel, embed=embObj)


async def cmdHandler(msg: Message) -> str:
    """
    Receives commands and handles it according to allCommandos. Commandos are automatically parsed from the code.
    :param msg: message from the discord channel
    :return:
    """
    try:
        prefix = Settings.objects.get(name="prefix")
        prefix = prefix.value
    except ObjectDoesNotExist:
        prefix = "!"

    for cdos in DiscordCommando.allCommandos():
        if msg.content.startswith(prefix+cdos.commando):
            if msg.author.bot:
                logger.info("Ignoring {msg.content}, because bot")
                return

            if msg.author.id == masterUserID and len(DiscordUsers.objects.filter(id=masterUserID)) == 0:
                DiscordUsers(id=masterUserID,name=msg.author.name,userLevel=6).save()

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


############################### Decorators ##########################

def markGroup(group: str) -> Callable:
    def neededParameters() -> Dict:
        return {'name': str,
                'userLevel': int,
                }

    def internal_func_wrapper(func: callable):
        attributes = getmembers(func, lambda a: not (isroutine(a)))
        memberDescriptors = dict([a for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))])
        for name, valueType in neededParameters().items():
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


def markCommando(cmd: str, group=GrpGeneral, defaultUserLevel=None):
    def internal_func_wrapper(func: callable):
        async def func_wrapper(**kwargs):
            responseDataInternal = await func(**kwargs)
            if not isinstance(responseDataInternal, CDOInteralResponseData):
                raise TypeError("Commandos need to return a CDOInteralResponseData type!")

            responseData = CDOFullResponseData(kwargs['msg'].channel, kwargs['cdo'], responseDataInternal)
            msg = await sendResponse(responseData)

            if responseDataInternal.reactionFunc is not None:
                await client.wait_for_reaction(message=msg, check=responseDataInternal.reactionFunc)
            elif responseDataInternal.paging is not None:
                await resetPaging(msg)
                def pagingCheck(reaction: Reaction, user: User):
                    if reaction.count == 2:
                        if reaction.emoji == '⏩':
                            direction = pageNav.forward
                        else:
                            direction = pageNav.previous

                        data = responseDataInternal.paging(direction)
                        responseData = CDOFullResponseData(reaction.message.channel, kwargs['cdo'], data)
                        embObj = getEmbObj(responseData)

                        client.loop.create_task(editPagingMessage(reaction.message,embObj))
                    return False
                await client.wait_for_reaction(message=msg,check=pagingCheck)
            return

        DiscordCommando.addCommando(DiscordCommando(cmd, func_wrapper, func.__doc__, group, defaultUserLevel))
        return func_wrapper

    return internal_func_wrapper
