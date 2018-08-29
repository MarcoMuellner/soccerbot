from typing import Dict, Union
import logging
from collections import OrderedDict
from django.core.exceptions import ObjectDoesNotExist
from json.decoder import JSONDecodeError
import subprocess
import sys
import os
import re
from discord import Reaction,User,Message

from database.models import CompetitionWatcher, Competition, MatchEvents, MatchEventIcon,Settings,DiscordUsers
from discord_handler.handler import client, watchCompetition,Scheduler
from discord_handler.cdo_meta import markCommando, CDOInteralResponseData, cmdHandler, emojiList\
    , DiscordCommando,resetPaging,pageNav
from discord_handler.liveMatch import LiveMatch
from api.calls import getLiveMatches,makeMiddlewareCall,DataCalls,getTeamsSearchedByName
from api.stats import getTopScorers, getLeagueTable,getPlayerInfo
from support.helper import shutdown,checkoutVersion,getVersions,currentVersion

from support.helper import Task

logger = logging.getLogger(__name__)

path = os.path.dirname(os.path.realpath(__file__))
"""
Concering commandos: Commandos are automatically added by marking it with the markCommando decorator. This 
decorator also has as a parameter the given Commando that is wished to be used for this Commando. Commandos in 
general get a kwargs object, containing the message and commando, which can be used. It has to return a 
CDOInternalResponseData object, which is used for its response to the channel.

All commandos belong to a certain group and has a certain userlevel associated to it. If no group is explicitly 
associated, it will use the GrpGeneral object as its group. Also, if no userlevel is associated to a commando,
the userlevel of the group is used.
"""

################################### Commandos ########################################

@markCommando("add", defaultUserLevel=3)
async def cdoAddCompetition(msg : Message,**kwargs):
    """
    Adds a competition to be watched by soccerbot. It will be regularly checked for new games.
    Optional arguments:
    **channel**: Defines a default channel for all live output for a given competition
    **role**: Assigns a role for a competition. This applies to the channel. So only people with this
    role can see this channel.
    :return: Answer message
    """
    responseData = CDOInteralResponseData()
    if "parameter0" in kwargs.keys():
        parameter = kwargs['parameter0']
    else:
        return CDOInteralResponseData("You need to give me a competition, mate")

    comp = Competition.objects.filter(clear_name=parameter)

    logger.debug(f"Available competitions: {comp}")
    if len(comp) == 0:
        return CDOInteralResponseData(f"Can't find competition {parameter}")

    if len(comp) != 1:
        if "parameter1" not in kwargs.keys():
            name_code = [f"{existing_com.clear_name},{existing_com.association_id}" for existing_com in comp]
            responseData.response = f"Found competitions {name_code} with that name. Please add a second parameter " \
                                    f"with the country code. For example: " \
                                    f"**Premier League,ENG**"
            return responseData
        else:
            comp = comp.filter(association=kwargs['parameter1'])
            if len(comp) > 1:
                return CDOInteralResponseData(f"Sorry, we still couldn't find a unique competition. Found competitions "
                                              f"are {[(i.clear_name,i.association) for i in comp]}")
            elif len(comp) <1:
                return CDOInteralResponseData(f"Sorry no competition was found with {parameter},{kwargs['parameter1']}")

    watcher = CompetitionWatcher.objects.filter(competition=comp.first())

    logger.debug(f"Watcher objects: {watcher}")

    if len(watcher) != 0:
        return CDOInteralResponseData(f"Allready watching {parameter}")

    responseData.response = f"Start watching competition {parameter}"

    channel = None if 'channel' not in kwargs.keys() else kwargs['channel']
    category = None if 'category' not in kwargs.keys() else kwargs['category']

    roleNames = [i.name for i in msg.guild.roles]

    role = None

    if 'role' in kwargs.keys():
        fullRole = kwargs['role'].replace("+"," ")
        if fullRole not in roleNames:
            return CDOInteralResponseData(f"The role __{fullRole}__ is not available on this server!")
        else:
            for i in msg.guild.roles:
                if i.name == fullRole:
                    role = i.id

    client.loop.create_task(watchCompetition(comp.first(), msg.guild, channel,role,category))

    return responseData

@markCommando("defaultCategory",defaultUserLevel=5)
async def cdoDefaultCategory(msg : Message,**kwargs):
    """
    Sets a default category for the channels created
    :param kwargs: 
    :return: 
    """
    try:
        defaultCategory = Settings.objects.get(name="defaultCategory")
    except ObjectDoesNotExist:
        defaultCategory = None

    if "parameter0" not in kwargs.keys():
        if defaultCategory is not None:
            return CDOInteralResponseData(f"Default category is **{defaultCategory.value}**")
        else:
            return CDOInteralResponseData(f"No default category set yet")

    if defaultCategory is not None:
        defaultCategory.value = kwargs['parameter0']
    else:
        defaultCategory = Settings(name="defaultCategory",value=kwargs['parameter0'])

    defaultCategory.save()

    return CDOInteralResponseData(f"Default category set to **{defaultCategory.value}**")



@markCommando("remove", defaultUserLevel=3)
async def cdoRemoveCompetition(msg : Message,**kwargs):
    """
    Removes a competition from the watchlist.
    :return: Answer message
    """
    responseData = CDOInteralResponseData()
    if "parameter0" in kwargs.keys():
        parameter = kwargs['parameter0']
    else:
        return CDOInteralResponseData("You need to give me a competition, mate")

    watcher = CompetitionWatcher.objects.filter(competition__clear_name=parameter)

    if len(watcher) == 0:
        responseData.response = f"Competition {parameter} was not monitored"
        return responseData

    if len(watcher) > 1:
        if "parameter1" in kwargs.keys():
            watcher = watcher.filter(competition__association=kwargs['parameter1'])
        else:
            nameCode = [f"{i.competition.clear_name},{i.competition.association}" for i in watcher]
            return CDOInteralResponseData(f"We have multiple competitions that match {parameter}, "
                                          f"naming "
                                          f"{nameCode}"
                                          f", please provide an association with a second parameter. For example: "
                                          f"**{kwargs['prefix']}removeCompetition Premier League,ENG**")

    logger.info(f"Deleting {watcher}")
    await Scheduler.removeCompetition(watcher.first())
    watcher.delete()
    responseData.response = f"Removed {parameter} from monitoring"
    return responseData


@markCommando("monitored")
async def cdoShowMonitoredCompetitions(msg : Message,**kwargs):
    """
    Lists all watched competitions by soccerbot.
    :return: Answer message
    """
    retString = f"React with number emojis to remove.Only the first {len(emojiList())} can " \
                f"be added this way):\n\n"
    addInfo = OrderedDict()
    compList = []
    for watchers in CompetitionWatcher.objects.all():
        compList.append(watchers.competition)
        try:
            addInfo[watchers.competition.association.clear_name] +=(f"\n{watchers.competition.clear_name}")
        except KeyError:
            addInfo[watchers.competition.association.clear_name] = watchers.competition.clear_name

    def check(reaction : Reaction, user):
        if reaction.emoji in emojiList():
            index = emojiList().index(reaction.emoji)
            if index < len(compList):
                msg.content = f"{kwargs['prefix']}removeCompetition {compList[index].clear_name},{compList[index].association_id}"
                client.loop.create_task(cmdHandler(msg))
                return True

    return CDOInteralResponseData(retString, addInfo, check)


@markCommando("list")
async def cdoListCompetitionByCountry(msg : Message,**kwargs):
    """
    Lists all competitions for a given country. Needs the name of the country of country code as
    a parameter.
    :return:
    """
    responseData = CDOInteralResponseData()
    if "parameter0" not in kwargs.keys():
        return CDOInteralResponseData(f"Needs the country or countrycode as parameter")

    association = kwargs['parameter0']

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
        compList.append(f"{comp.clear_name},{comp.association.id}")

    retString += f"\n\nReact with according number emoji to add competitions. Only the first {len(emojiList())} can " \
                 f"be added this way"
    responseData.response = retString

    def check(reaction: Reaction, user):
        if reaction.emoji in emojiList():
            try:
                index = emojiList().index(reaction.emoji)
            except ValueError:
                logger.error(f"{reaction.emoji} not in list!")
                return False
            if index < len(compList):
                msg.content = f"{kwargs['prefix']}addCompetition {compList[index]}"
                client.loop.create_task(cmdHandler(msg))
                return True

    responseData.reactionFunc = check
    return responseData


@markCommando("help")
async def cdoGetHelp(msg : Message,**kwargs):
    """
    Returns all available Commandos and their documentation.
    :return:
    """
    retString = "Available Commandos:"
    addInfo = OrderedDict()

    try:
        userQuery = DiscordUsers.objects.get(id=msg.author.id)
        authorUserLevel = userQuery.userLevel
    except ObjectDoesNotExist:
        authorUserLevel = 0

    for i in DiscordCommando.allCommandos():
        if i.userLevel <= authorUserLevel:
            doc = i.docstring
            doc = re.sub(':.+\n', "", doc)
            doc = re.sub('\n+', "", doc)
            if authorUserLevel >= 5:
                level = f" lvl:{i.userLevel}"
            else:
                level = ""
            addInfo[kwargs['prefix'] + i.commando + level] = doc

    responseData = CDOInteralResponseData(retString, addInfo)

    return responseData

@markCommando("showRunningTasks", defaultUserLevel=6)
async def cdoShowRunningTasks(msg : Message,**kwargs):
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

@markCommando("scores")
async def cdoScores(msg : Message,**kwargs):
    """
    Returns the scores for a given competition/matchday/team
    :param kwargs:
    :return:
    """
    channel = msg.channel

    if "parameter0" not in kwargs.keys():
        if not "live-" in channel.name:
            return CDOInteralResponseData(f"This command with no argument can only be called within matchday channels")

        comp,md = Scheduler.findCompetitionMatchdayByChannel(channel.name)

        matchList = Scheduler.getScores(comp,md)

        resp = CDOInteralResponseData("Current scores:")
        addInfo = OrderedDict()
        for matchString,goalList in matchList.items():
            addInfo[matchString] = ""
            for goals in goalList[0]:
                if goals != '':
                    addInfo[matchString] += goals+"\n"

            if addInfo[matchString] == "":
                del addInfo[matchString]

            if addInfo == OrderedDict():
                addInfo[matchString] = f"{goalList[1]}: 0-0"

        if addInfo == OrderedDict():
            resp.response = "Currently no running matches"
        else:
            resp.response = "Current scores:"
        resp.additionalInfo = addInfo
        return resp
    else:
        searchString = kwargs['parameter0']
        query = Competition.objects.filter(clear_name = searchString)

        if len(query) == 0:
            teamList = getTeamsSearchedByName(searchString)
            if len(teamList) == 0:
                return CDOInteralResponseData(f"Can't find team {searchString}")
            matchObj = teamList[0]['Name'][0]['Description']
            matchList = getLiveMatches(teamID=int(teamList[0]["IdTeam"]))

        else:
            comp = query.first()
            matchObj = comp.clear_name
            matchList = getLiveMatches(competitionID=comp.id)

        if len(matchList) == 0:
            return CDOInteralResponseData(f"No current matches for {matchObj}")

        addInfo = OrderedDict()
        for matchID in matchList:
            try:
                data = makeMiddlewareCall(DataCalls.liveData + f"/{matchID}")
            except JSONDecodeError:
                logger.error(f"Failed to do a middleware call for {matchID}")
                continue

            newEvents, _ = LiveMatch.parseEvents(data["match"]["events"], [])

            class Match:
                id = matchID

            for event in newEvents:
                title,_,goalListing = await LiveMatch.beautifyEvent(event,Match)

                if goalListing != "":
                    try:
                        addInfo[title]+=goalListing + "\n"
                    except KeyError:
                        addInfo[title] = goalListing + "\n"

        if addInfo == OrderedDict():
            return CDOInteralResponseData(f"No goals currently for {matchObj}")

        resp = CDOInteralResponseData(f"Current scores for {matchObj}")
        resp.additionalInfo = addInfo
        return resp

async def basicStatsFun(msg,fun,onlyText,**kwargs):
    """
    Shows the topscorer for a given competition
    :param kwargs:
    :return:
    """
    if 'parameter0' not in kwargs.keys():
        return CDOInteralResponseData("You need to tell me the competition, mate!")

    searchString = kwargs['parameter0']

    competition = Competition.objects.filter(clear_name=searchString)
    if len(competition) == 0:
        return CDOInteralResponseData(f"Sorry, can't find {searchString}")

    if len(competition) > 1:
        if 'parameter1' not in kwargs.keys():
            compStr = ""
            for i in competition:
                compStr +=f"**{i.clear_name} , {i.association.clear_name}**\n"

            retString = f"Multiple competitions found with name {searchString}.\n\n{compStr}\n" \
                        f"React with emojis to choose"

            def check(reaction : Reaction, user):
                if reaction.emoji in emojiList():
                    index = emojiList().index(reaction.emoji)
                    if index < len(competition):
                        msg.content = f"{kwargs['prefix']}{kwargs['cdo']} " \
                                                f"{competition[index].clear_name},{competition[index].association_id}"
                        client.loop.create_task(cmdHandler(msg))
                        return True
                return False

            return CDOInteralResponseData(retString,reactionFunc=check)
        else:
            competition = competition.filter(association_id=kwargs['parameter1'])

    addInfo = await fun(competition.first())
    if addInfo == OrderedDict():
        return CDOInteralResponseData(f"Sorry no data available for {searchString}")
    else:
        if onlyText:
            return CDOInteralResponseData(addInfo, onlyText=True)
        else:
            return CDOInteralResponseData(f"Result for {searchString}",addInfo,paging=1)

@markCommando("topScorer")
async def cdoTopScorer(msg : Message,**kwargs):
    """
    Shows the topscorer for a given competition
    :param kwargs:
    :return:
    """
    return await basicStatsFun(msg,getTopScorers,False,**kwargs)

@markCommando("standing")
async def cdoStanding(msg : Message,**kwargs):
    """
    Shows the standing for a given competition
    :param kwargs:
    :return:
    """
    return await basicStatsFun(msg,getLeagueTable,True,**kwargs)

@markCommando("playerInfo")
async def cdoPlayerInfo(msg : Message,**kwargs):
    """
    Shows information on a given player
    :param kwargs:
    :return:
    """
    if 'parameter0' not in kwargs.keys():
        return CDOInteralResponseData("You need to tell me the name of the player!")

    searchString = kwargs['parameter0']
    res = getPlayerInfo(searchString)
    if res != None:
        playerName = res[0]
        addInfo = res[1]
    else:
        return CDOInteralResponseData(f"Sorry, nothing was found for {kwargs['parameter0']}")
    return CDOInteralResponseData(playerName,addInfo,paging=1)

@markCommando("current")
async def cdoCurrentGames(msg : Message,**kwargs):
    """
    Lists all current games within a matchday channel
    :param kwargs:
    :return:
    """

    if "parameter0" in kwargs.keys():
        competition = Competition.objects.filter(clear_name=kwargs['parameter0'])
    else:
        competition = None

    matchList = Scheduler.startedMatches()
    addInfo = OrderedDict()
    for match in matchList:
        if competition == None:
            addInfo[match.title] = f"{match.minute}"
        else:
            if match.match.competition == competition.first():
                addInfo[match.title] = f"{match.minute}"

    if addInfo == OrderedDict():
        respStr = "No running matches"
    else:
        respStr = "Running matches:"

    resp = CDOInteralResponseData(respStr,addInfo)

    return resp

@markCommando("upcoming")
async def cdoUpcomingGames(msg : Message,**kwargs):
    """
    Lists all upcoming games
    :param kwargs:
    :return:
    """
    if "parameter0" in kwargs.keys():
        competition = Competition.objects.filter(clear_name=kwargs['parameter0'])
    else:
        competition = None

    matchList = Scheduler.upcomingMatches()
    addInfo = OrderedDict()
    for match in matchList:
        if competition == None:
            addInfo[match.title] = f"{match.match.date.strftime('%d %b %Y, %H:%M')} (UTC)"
        else:
            if match.match.competition == competition.first():
                addInfo[match.title] = f"{match.match.date.strftime('%d %b %Y, %H:%M')} (UTC)"

    if addInfo == OrderedDict():
        respStr = "No upcoming matches"
    else:
        respStr = "Upcoming matches:"

    resp = CDOInteralResponseData(respStr,addInfo)
    return resp

@markCommando("setStartCdo", defaultUserLevel=5)
async def cdoSetStartCDO(msg : Message,**kwargs):
    """
    Sets a commandline argument to start the bot.
    :param kwargs:
    :return:
    """
    if kwargs['parameter0'] in kwargs.keys():
        return CDOInteralResponseData("You need to set a command to be executed to start the bot")
    commandString = kwargs['parameter0']

    obj = Settings(name="startCommando",value=commandString)
    obj.save()
    return CDOInteralResponseData(f"Setting startup command to {commandString}")

@markCommando("update", defaultUserLevel=5)
async def cdoUpdateBot(msg : Message,**kwargs):
    """
    Updates bot
    :param kwargs:
    :return:
    """
    def spawnAndWait(listObj):
        p = subprocess.Popen(listObj)
        p.wait()

    if "parameter0" not in kwargs.keys():
        return CDOInteralResponseData("Please provide the version you want to update to (master (_**experimental**_)"
                                      ", or version)")

    version = kwargs['parameter0']

    if version != "master" and version not in getVersions():
        return CDOInteralResponseData(f"Version {data[1]} not available")

    if not checkoutVersion(version):
        return CDOInteralResponseData(f"Sorry, {version} is not available")
    spawnAndWait([sys.executable, path + "/../manage.py", "migrate"])
    spawnAndWait([sys.executable, "-m", "pip", "install", "-r", f"{path}/../requirements.txt"])

    return CDOInteralResponseData(f"Updated Bot to **{version}**. Please restart to apply changes")

@markCommando("stop", defaultUserLevel=5)
async def cdoStopBot(msg : Message,**kwargs):
    """
    Stops the execution of the bot
    :param kwargs:
    :return:
    """
    responseData = CDOInteralResponseData()
    retString = f"To confirm the shutdown, please react with {emojiList()[0]} to this message."
    responseData.response = retString

    def check(reaction : Reaction, user):
        if reaction.emoji == emojiList()[0]:
            client.loop.create_task(client.send_message(msg.channel, "Bot is shutting down in 10 seconds"))
            client.loop.create_task(shutdown())
            return True

    responseData.reactionFunc = check
    return responseData

@markCommando("restart", defaultUserLevel=5)
async def cdoRestartBot(msg : Message,**kwargs):
    """
    Restart Kommando
    :param kwargs:
    :return:
    """
    try:
        Settings.objects.get(name="startCommando")
        logger.info(f"Command: {sys.executable} {path+'/../restart.py'}")
        cmdList = [sys.executable,path+"/../restart.py"]
        logger.info(cmdList)
        p = subprocess.Popen(cmdList)
        logger.info(f"ID of subprocess : {p.pid}")
        return CDOInteralResponseData("Shutting down in 10 seconds. Restart will take around 30 seconds")
    except ObjectDoesNotExist:
        return CDOInteralResponseData("You need to set the startup Command with !setStartCommando before this"
                                      "commando is available")

@markCommando("prefix", defaultUserLevel=5)
async def cdoSetPrefix(msg : Message,**kwargs):
    """
    Sets the prefix for the commands
    :param kwargs:
    :return:
    """
    if kwargs['parameter0'] in kwargs.keys():
        return CDOInteralResponseData("You need to set a command to be executed to start the bot")

    commandString = kwargs['parameter0']
    try:
        prefix = Settings.objects.get(name="prefix")
        prefix.value = commandString
    except ObjectDoesNotExist:
        prefix = Settings(name="prefix",value=commandString)

    prefix.save()
    return CDOInteralResponseData(f"New prefix is {prefix.value}")

@markCommando("setPermissions", defaultUserLevel=5)
async def cdoSetUserPermissions(msg : Message,**kwargs):
    """
    Sets the userlevel for the mentioned users.
    :param kwargs:
    :return:
    """
    if len(msg.mentions) == 0:
        return CDOInteralResponseData("You need to mention a user to set its permission levels")

    level = None

    for key,val in kwargs.items():
        if key.startswith("parameter"):
            if val.startswith("<@"):
                continue
            else:
                try:
                    level = int(val)
                except ValueError:
                    continue

    if level == None:
        return CDOInteralResponseData(f"Wrong parameters! Needs a mention and user level."
                                      f"User Level needs to be a number between 0 and 5")

    if level > 5 or level < 0:
        return CDOInteralResponseData("Only user levels from 0 to 5 are available")

    retString = ""
    for user in msg.mentions:
        DiscordUsers(id=user.id,name=user.name,userLevel=level).save()
        retString += f"Setting {user.name} with id {user.id} to user level {level}\n"

    return CDOInteralResponseData(retString)

@markCommando("getPermissions",defaultUserLevel=5)
async def cdoGetUserPermissions(msg : Message,**kwargs):
    """
    Gets the userlevel of a mentioned user
    :param kwargs:
    :return:
    """
    addInfo = OrderedDict()
    for user in msg.mentions:
        try:
            user = DiscordUsers.objects.get(id=user.id)
            addInfo[user.name] = f"User level: {user.userLevel}"
        except ObjectDoesNotExist:
            addInfo[user.name] = f"User level: 0"

    if addInfo == OrderedDict():
        return CDOInteralResponseData("You need to mention a user to get its permission status!")

    retObj = CDOInteralResponseData("UserLevels:")
    retObj.additionalInfo = addInfo
    return retObj

@markCommando("versions",defaultUserLevel=5)
async def cdoVersions(msg : Message,**kwargs):
    """
    Shows all available versions for the bot
    :param kwargs:
    :return:
    """
    retString = ""
    for i in getVersions():
        retString += f"Version: **{i}**\n"

    return CDOInteralResponseData(retString)

@markCommando("about",defaultUserLevel=0)
async def cdoAbout(msg : Message,**kwargs):
    """
    About the bot
    :param kwargs:
    :return:
    """
    retstring = "**Soccerbot - a live threading experience**\n\n"
    retstring += f"Current version: {currentVersion()}\n"
    retstring += f"Website: https://soccerbot.eu\n"
    retstring += f"More info: https://github.com/muma7490/soccerbot\n"
    retstring += f"Click https://paypal.me/soccerbot if you want to buy my creator a beer"

    return CDOInteralResponseData(retstring)

@markCommando("test", defaultUserLevel=6)
async def cdoTest(msg : Message,**kwargs):
    """
    Test Kommando
    :param kwargs:
    :return:
    """
    msg = await client.send_message(msg.channel, 'React <:yellow_card:478130458090012672> with thumbs up or thumbs down.')
    await client.add_reaction(message=msg, emoji='⏪')
    await client.add_reaction(message=msg,emoji='⏩')

    def check(reaction : Reaction, user : User):
        print(reaction.count)
        if reaction.count == 2:
            client.loop.create_task(resetPaging(reaction.message))
        e = str(reaction.emoji)
        print(e)
        print(e == emojiList()[0])
        return False

    res = await client.wait_for_reaction(message=msg, check=check)
    #await client.send_message(msg.channel, '{0.user} reacted with {0.reaction.emoji}!'.format(res))
