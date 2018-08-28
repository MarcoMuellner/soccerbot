---
layout: page
title: Documentation
subtitle: How to use soccerbot?
---

In this documentation every single command is explained, including examples on how to use them. We will start off with a general explanation on how the commands work, using prefixes, etc. Secondly, we will explain all commands and their parameter that can be used. 

# General information


## Prefix

The prefix for soccerbot is configurable using the `prefix` command. You can, in principle, set it to everything you like, it is recommended to use something short like `-` or `$`. **By default the prefix used is `!`**.

## What happens when i call a command?

Due to the fact, that soccerbot regularly needs to call other websites and crawls data from them, a command can potentially take a while to complete. Therefore, after setting off a command, it will show a `Working ...` message like this:

![Working command][working]

This message indicates that the bot is busy and will be edited after the bot is finished and show the result.
You can of course send the next command after it, though it won't show up, after the bot is actually finished with what it was doing. Some commands also support paging and reactions with emojis

## Paging & reactions

Paging is the concept of splitting up the result of a command into regular bites, navigable with the :fast_forward: and :rewind: emojis. These emojis will automatically show up, if a result has more than 5 entries. Some commands like the `playerInfo` command use this concept as well, but only for 1 entry (a player).

Other commands support reactions with emojis. These are generally the number emojis like :zero: (the first entry in a list). The commands that support that are listed below. 

## Parameters

Soccerbot generally supports 2 kinds of parameters: __inline parameters__ and __positional paraemters__. Inline parameters are followed directly after the command, split up by the `,` symbol and positional parameter are marked by the `=` symbol. Consider this command:
```
!add Premier League,ENG role=dummyRole
```
This command has both kinds of parameters in them. __Premier League__ and __ENG__ are the inline parameters and __role__ is the positional parameter. Again, down below is marked which commands support which Parameters

## Core feature commands

This section specifically will cover the commands you need to add and remove competitions from the bot. They are written prefix agnostic, so of course you need to add the prefix to every command.

### add

* **User level**: 3
* **Description**: `add` allows to add a competition to soccerbot. This competition is then monitored by soccerbot, and adds channels automatically, as well as posting live updates for all matches within this competition. If `defaultCategory` is set before using this command, all competitions will by default move to this category. The name of the channels follow the `live-COMPETITION` pattern.
* **Inline Parameters**:
	* **$1**: Describes the name of the competition. If you are not sure whats the competition name, use the `list` command
	* **$2**__(optional)__: The country code for a given competition according to [FIFA](https://en.wikipedia.org/wiki/List_of_FIFA_country_codes). If the competition given in **$1** is not unique, you need to pass this parameter as well.
* **Optional Parameters**:
	* **role**: Assigns a certain role to the channels created by soccerbot. This role must exist previous to using this parameter.
	* **channel**: Assigns a channel to this competition. All updates will be posted in this channel. If the channel does not exist, it will create it.
	* **category**: Assigns a category to this competition. The channel created by this command will move to that category. If this is not set, the default category is used (set by `defaultCategory`). 

### list

* **User level**: 0
* **Description**: Lists all competition for a given Country. For competitions not assigned to a country but to a federation, you can use the federation as a parameter instead.
* **Inline Parameters**:
	* **$1**: The country/federation for which leagues you are looking for
* **Reactions**: Reacting with a number emoji (:zero:) will add the league in the list with that number

### monitored

* **User level**: 0
* **Description**: Lists all currently monitored competitions
* **Reactions**: Reacting with a number emoji (:zero:) will remove the league in the list with that number

### remove

* **User level**: 3
* **Description**: Removes a competition with that name from the list
* **Inline Parameters**:
	* **$1**: Describes the name of the competition. If you are not sure whats the competition name, use the `monitored` command
	* **$2**__(optional)__: The country code for a given competition according to [FIFA](https://en.wikipedia.org/wiki/List_of_FIFA_country_codes). If the competition given in **$1** is not unique, you need to pass this parameter as well.

### help

* **User level**: 0
* **Description**: Shows all available commands for a given user. Only the commands that are via user level available, will be shown

### scores

**User level**: 0
* **Description**: Shows the score for all currently running matchs. If this is called within a channel managed by soccerbot, it will show the scores for currently running games within this channel. Otherwise you need to specify the Team/Competition you want to check. If you are not sure whats the competition name, use the `list` command
* **Inline Parameters**:
	* **$1**: The competition/team you are looking for.

### topScorer

**User level**: 0
* **Description**:Shows the topScorer list for a given league. All FIFA leagues are available.
* **Inline Parameters**:
	* **$1**: The competition/team you are looking for. If you are not sure whats the competition name, use the `list` command

### standing

**User level**: 0
* **Description**:Shows the current standing for a given league.
* **Inline Parameters**:
	* **$1**: The competition/team you are looking for. If you are not sure whats the competition name, use the `list` command

### playerInfo

**User level**: 0
* **Description**:Shows some stats for a player in the current season. If multiple are found with that name, the first one it finds is used.
* **Inline Parameters**:
	* **$1**: The player you are looking for.

### current 

**User level**: 0
* **Description**:Current games that are running within soccerbot. Shows its score as well.

### upcoming

**User level**: 0
* **Description**:Shows upcoming games for the soccerbot. You can also specify a league, watched by soccerbot.
* **Inline Parameters**:
	* **$1**__(optional)__: The competition you are looking for. If you are not sure whats the competition name, use the `monitored` command.