from inspect import getmembers, isroutine
import logging
from typing import Dict, Callable, List
from collections import OrderedDict
from discord import TextChannel, Embed, Message, Reaction,User
from django.core.exceptions import ObjectDoesNotExist
import os
import json
from enum import Enum
import re

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
        masterUserID = int(json.loads(f.read())['masterUser'])
except (KeyError,FileNotFoundError):
    logger.error(f"NO MASTER USER AVAILABLE")
    masterUserID = None

############################### Response objects ##########################

class CDOInteralResponseData:
    def __init__(self, response: str = "", additionalInfo: OrderedDict = OrderedDict()
                 , reactionFunc=None, paging = None,onlyText = False):
        self.response = response
        self.additionalInfo = additionalInfo
        self.reactionFunc = reactionFunc
        self.paging = paging
        self.onlyText = onlyText


class CDOFullResponseData:
    def __init__(self, channel: TextChannel, cdo: str, internalResponse: CDOInteralResponseData):
        self.channel = channel
        self.cdo = cdo
        self.response = internalResponse.response
        self.paging = internalResponse.paging
        self.additionalInfo = internalResponse.additionalInfo

    def __str__(self):
        return f"Posting {self.response} to {self.cdo} with addInfo {self.additionalInfo} to {self.channel}"

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
        self.msg = None

    @staticmethod
    def allCommandos() -> List:
        return discordCommandos

    @staticmethod
    def addCommando(commando):
        logger.info(f"Add commando {commando}")
        discordCommandos.append(commando)

    def __str__(self):
        return f"Cmd {self.cmd_group}:{self.commando}, userLevel {self.userLevel}"

class Page:
    def __init__(self,cdoResp : CDOInteralResponseData,cdo : str,paging = None):
        self.addInfoList = []
        self.cdoResp = cdoResp
        if paging != None:
            maxCount = paging
        else:
            maxCount = 5

        count = 0
        tmpDict = OrderedDict()
        for key,val in cdoResp.additionalInfo.items():
            tmpDict[key] = val
            count += 1
            if count >=maxCount:
                self.addInfoList.append(CDOInteralResponseData(response=cdoResp.response,additionalInfo=tmpDict))
                tmpDict = OrderedDict()
                count = 0

        if tmpDict != OrderedDict():
            self.addInfoList.append(CDOInteralResponseData(response=cdoResp.response,additionalInfo=tmpDict))
        self.index = 0
        self.length = len(self.addInfoList)
        self.cdo = cdo
        pass

    def getInitialData(self) -> CDOInteralResponseData:
        return self.addInfoList[0]

    def reactFunc(self,reaction : Reaction, user : User):

        if self.msg.id == reaction.message.id:
            if self.cdoResp.reactionFunc is not None:
               client.loop.create_task(self.cdoResp.reactionFunc(reaction,user))
            if reaction.count == 2:
                if reaction.emoji == '⏩' and self.index + 1 < self.length:
                    self.index +=1
                elif reaction.emoji == '⏪' and self.index - 1 >= 0:
                    self.index -=1
                else:
                    pass

                responseData = CDOFullResponseData(reaction.message.channel,self.cdo,self.addInfoList[self.index])
                embObj = getEmbObj(responseData)
                embObj.set_footer(text=f"Page {self.index+1}/{self.length}")

                client.loop.create_task(editPagingMessage(reaction.message, embObj))

    def setMsg(self,msg : Message):
        self.msg = msg





############################### Meta functions ##########################

async def editPagingMessage(message : Message,embObj):
    await message.edit(embed=embObj)
    await resetPaging(message)

async def resetPaging(message : Message):
    await message.clear_reactions()
    await message.add_reaction(emoji='⏪')
    await message.add_reaction(emoji='⏩')


def getEmbObj(responseData):
    title = f"Commando {responseData.cdo}"
    content = responseData.response

    embObj = Embed(title=title, description=content)

    for key, val in responseData.additionalInfo.items():
        embObj.add_field(name=key, value=val, inline=True)

    return embObj

def getParameters(msgContent : str) -> Dict[str,str]:
    """
    Get parameters parses through a command call and returns all parameters. Inline parameters are simply added
    after the command, positional parameters can be added via x=y.
    :param msgContent: msgContent for the parameters
    :return: A dictionary full of parameters that can be added to kwargs
    """
    retDict = {}
    #optional parameters
    optPar = re.findall(r"\w+=[/\w\+]+",msgContent)
    for i in optPar:
        key,val = i.split("=")
        retDict[key] = val
        msgContent = msgContent.replace(i,"")
    #inline parameters
    msgContent = re.sub(r"\s*<@\w+>","",msgContent)
    data = msgContent.split(",")
    data[0] = data[0].replace(data[0].split(" ")[0], "") #remove Command
    if data[0] == "":
        data.remove(data[0])
    for index in range(0,len(data)):
        if isinstance(data[index],list):
            retDict[f"parameter{index}"] = data[index][0].strip()
        else:
            retDict[f"parameter{index}"] = data[index].strip()
    return retDict

async def sendResponse(responseData : CDOFullResponseData,onlyText = False,edit_msg : Message= None):
    logger.info(responseData)
    if edit_msg == None:
        if not onlyText:
            embObj = getEmbObj(responseData)
            msg =  await responseData.channel.send(embed=embObj)
        else:
            msg =  await responseData.channel.send(content=responseData.response)
    else:
        if not onlyText:
            embObj = getEmbObj(responseData)
            await edit_msg.edit(embed=embObj)
        else:
            await edit_msg.edit(content=responseData.response,embed=Embed())
        msg = edit_msg

    return msg


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
                parseParameters = getParameters(msg.content)
                logger.info(f"Handling {cdos.commando}")

                tmpMsg = await sendResponse(
                    CDOFullResponseData(msg.channel, cdos.commando, CDOInteralResponseData("Working ...")))
                kwargs = {'cdo': cdos.commando,
                          'msg': msg,
                          'userLevel': authorUserLevel,
                          'prefix':prefix,
                          'tmpMsg':tmpMsg}
                kwargs.update(parseParameters)

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

            maxLen = responseDataInternal.paging if responseDataInternal.paging is not None else 5

            if len(responseDataInternal.additionalInfo) < maxLen:
                responseData = CDOFullResponseData(kwargs['msg'].channel, kwargs['cdo'], responseDataInternal)
                msg = await sendResponse(responseData,responseDataInternal.onlyText,edit_msg=kwargs['tmpMsg'])

                if responseDataInternal.reactionFunc is not None:

                    def internalCheck(reaction: Reaction, user: User):
                        if reaction.message.id == msg.id:
                            return responseDataInternal.reactionFunc(reaction, user)
                        else:
                            return False

                    await client.wait_for('reaction_add', check=internalCheck)
            else:
                pageObj = Page(responseDataInternal,cmd,paging=responseDataInternal.paging)
                responseData = CDOFullResponseData(kwargs['msg'].channel,cmd,pageObj.getInitialData())
                msg = await sendResponse(responseData,edit_msg=kwargs['tmpMsg'])
                await resetPaging(msg)
                pageObj.setMsg(msg)

                def internalCheck(reaction : Reaction, user: User):
                    if reaction.message.id == msg.id:
                        return pageObj.reactFunc(reaction,user)
                    else:
                        return False

                await client.wait_for('reaction_add',check =internalCheck)
            return

        DiscordCommando.addCommando(DiscordCommando(cmd, func_wrapper, func.__doc__, group, defaultUserLevel))
        return func_wrapper

    return internal_func_wrapper
