---
layout: page
title: Quickstart
subtitle: So how do i actually install it?
---
While not many, certain things need to be done in advance and certain
knowledge is required to actually run this bot. **Be sure that
all these requirements are met, before running the bot! No help
will be provided with these issues!**

### Knowledge stuff
* A basic knowledge of python and how to runs scripts, as well
as setting up virtual environments and installing packages.
* How to run scripts on a server and add bots to discord
* Basic knowledge on Reddit OAuth (basically on how to add
an application to reddit)
* Basic knowledge of shell commands.

### Software & Hardware requirements

* Currently, only Python3.6 is officially supported. Versions
lower than that will have problems with newer features used within
this bot, and Python3.7 is currently not supported by Discord.py
* Additionally to python, you need pip as well as some virtualenv
* You need to install git if you don't have it installed.
* A decent enough internet connection and hardware connection to run
the bot is also required.
* The bot is only tested on Mac/Linux. So try and get one of those.
* A set up application for [discord](https://discordapp.com/developers/docs/topics/oauth2#bots) and [reddit](https://ssl.reddit.com/prefs/apps/).

If you have these requirements set up, go ahead to the next point.

Before we beginn, we assume that you are connected to the server/device
where you want to run the bot. The bot assumes that this device is
available 24/7 (it does need to some regular maintanance work, set to
midnight UTC). Try and get some kind of cheap hosting solution, where
you have a VPS or something similar at your disposal.

## How to install the bot

So now that you are connected to your server. Lets start setting up
things. Switch to the path you want to install the server to
```console
marco@mamu-pc:~cd /path/to/install/
```
Next up, lets clone the software to this path
```console
marco@mamu-pc:~/path/to/install$ git clone https://github.com/muma7490/soccerbot
Cloning into 'soccerbot'...
...
```
```
A short note on this: You can also simply download the code from the
github, though updating via discord will not work this way. Cloning the
repo is the preffered way to do it.
```
Now that we have the software on the machine, lets switch into the folder.
```console
marco@mamu-pc:~/path/to/install$ cd soccerbot/
```
We assume that python3.6 is in your path as well as pip and venv is
installed for this python version. Please refer to
[this link](https://gist.github.com/Geoyi/d9fab4f609e9f75941946be45000632b)
to install the virtualenv as well as pip. From this point on we
assume that you created the virtual environment as well a
applied it to this folder and called it __venv__.

Now lets install all the packages we need.
```console
(venv) marco@mamu-pc:~/path/to/install/soccerbot (master)$ pip install -r requirements.txt
```
Next, lets set up the database.
```console
(venv) marco@mamu-pc:~/path/to/install/soccerbot (master)$ python manage.py migrate
```
Now the software is pretty much ready to go. The only thing left is
to setup the secret.json file. Here is an example of how that looks like:
```json
{
	"discord_secret":"secret_key",
	"reddit_secret":"secret_key",
	"reddit_client_id":"client_id",
	"masterUser":"user_id"
}
```
Replace the key in "discord_secret" with your discord secret you set up
when setting up the bot with discord and the reddit stuff with the
id and secret you got when setting up the reddit application. The
masterUser value should be the id of the master user, which is easily
obtainable with clicking _copy id_ on discord. This user will be able to assign userlevels for all other users.

And there you go. Everything should be set up now, and with
```console
(venv) marco@mamu-pc:~/path/to/install/soccerbot (master)$ python __main__.py
```
you can run the bot. Obviously you should create some kind of daemon for
the bot, so it can run without you connected to the server. See
[this link](https://www.raspberrypi-spy.co.uk/2015/10/how-to-autorun-a-python-script-on-boot-using-systemd/)
 for further info on that.

 Please refer to [the bot documentation](documentation.md) and [technical_details](technical_details.md) for more information.

