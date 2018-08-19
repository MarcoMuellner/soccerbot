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

These are the features available now for v0.1.0, which of course is only
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
And your done. With
```
python __main__.py
```
you can start your server. You obviously have to add it to your discord
server.

If you want to run it in production mode, it is strongly recommended
to add it as a systemctl job.

