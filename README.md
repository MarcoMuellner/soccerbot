# The soccerbot [![Build Status](https://travis-ci.org/muma7490/soccerbot.svg?branch=master)]

_Introducing soccerbot: A discord bot that automatically creates Match
channels, posts live updates and many more things to come._

## Functionality
- All official FIFA football leagues in the world are available,
including live updates to them.
- Customization: You can choose the competitions that
are watched for your discord server
- Automated creation of matchday channels for each league you want
monitored. They are also automatically deleted.
- Live updates for all matches. This includes goals, substitutions and
cards.
- Look and feel for match events are configurable via json files
- Allows the posting of statistics for a competition. Currently includes
the table as well as the topscorer for a given league.
- Automated version management. You can update the bot from within
discord
- Userlevel management for the bot. It allows for certain users
to have access to different commandos.

These are the features available now for v0.3.0, which of course is only
a pre version of things to come. The final goal for this bot is to
make all other soccerbots obsolete.

## Requirements
To use this bot, you currently have to install it on your own server.

**Important**: Python 3.6 is mandatory. Also it is recommended
to use a virtual environment for the code.

The installation process is very simple. First off install the
requirements
```
pip install -r requirements.txt
```
Next, initialize the database
```
python manage.py migrate
```
Create your secret.json file containing your secret. Its content
should look something like this:
```
{
    "secret":"key"
}
```
And your done. You can also set a master user if you like
to so. With
```
{
    "masterUser":"idOfUser"
}
```
You can give him absolute rights on the bot, and have access to
the debugging commandos.

With
```
python __main__.py
```
you can start your server. You obviously have to add it to your discord
server.

If you want to run it in production mode, it is strongly recommended
to add it as a systemctl job.

## Acknowledgments

Special thanks to @Nascimento#3578 and the [football](https://discord.gg/wKhSQEt)
discord server, who gave a huge amount of input, helped with development
and provided me with most of the ideas implemented in this bot.

