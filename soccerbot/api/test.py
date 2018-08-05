import requests
import json

fifa_api = "https://api.fifa.com/api/v1/"

headers = {'Content-Type': 'application/json'}

def printResults(results):
    print(results)
    for items in results:
        for key, value in items.items():
            print(f'{key},{value}')


#get all confederations
x = requests.get(fifa_api+"confederations")
print(x.url)
results = json.loads(x.content.decode())["Results"]
#printResults(results)


owner = "UEFA"

#get all competitions
payload = {
    'owner':owner,
    'count':500,
    'footballType':0
}
x = requests.get(fifa_api+"competitions/all",params=payload)
print(x.url)
results = json.loads(x.content.decode())["Results"]
#printResults(results)

#printResults(results)
idComp = 2000000019


#get all seasons
payload = {
    'idCompetition':idComp,
    'count':500
}
x = requests.get(fifa_api+"seasons",params=payload)
print(x.url)
results = json.loads(x.content.decode())["Results"]
#printResults(results)

idSeason = 2000011119

#get all matches
payload = {
    'idCompetition':idComp,
    'idSeason':idSeason,
    'count':1000
}
x = requests.get(fifa_api+"calendar/matches",params=payload)
print(x.url)
results = json.loads(x.content.decode())["Results"]
#printResults(results)

#get all teams
x = requests.get(fifa_api+"teams/all",params=payload)
print(x.url)
results = json.loads(x.content.decode())["Results"]
#printResults(results)

