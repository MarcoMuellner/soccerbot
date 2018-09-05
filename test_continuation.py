import requests

param = {
    "count":1000,
}
datar = requests.get("https://api.fifa.com/api/v1/teams/all",param)
headers = datar.headers
data = datar.json()
print(data['ContinuationToken'])
print(len(data['Results']))
print(datar.headers)
print(data['Results'][-1])
param = {
    "count":1000,
    'x-ms-continuation':data['ContinuationToken'],
    'ContinuationHash': data['ContinuationHash']
}

headers['x-ms-continuation']="{"+f"'token':'{data['ContinuationToken']}',"+"'range':{'min':'','max':'F'}}"
print(headers['x-ms-continuation'])

datar = requests.get("https://api.fifa.com/api/v1/teams/all",param,headers=headers)
data = datar.json()
print(data['ContinuationToken'])
print(len(data['Results']))
print(datar.headers)
print(data['Results'][-1])

