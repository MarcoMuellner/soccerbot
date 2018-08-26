import re

with open("debug.log") as f:
    lines = f.readlines()

pattern = re.compile(r".+parseReddit.+")
innerPattern = re.compile(r"\d+-\d+-\d+\s\d+:\d+\d+:\d+,\d+ . api\.reddit - parseReddit - \d+ - \n")
replacePattern = re.compile(r"\d+-\d+-\d+\s\d+:\d+\d+:\d+,\d+ . api\.reddit - parseReddit - \d+ - ")

resultList = []

for i in lines:
    match = pattern.findall(i)
    if len(match) != 0:
        if "Possible non catched event for" not in i:
            match = innerPattern.findall(i)
            if len(match) == 0:
                resultList.append(replacePattern.sub("",i))

uniqueList = []

for i in resultList:
    if i not in uniqueList:
        uniqueList.append(i)


with open("parseRedditRes.txt",'w') as f:
    for i in uniqueList:
        f.write(i)

print(uniqueList)