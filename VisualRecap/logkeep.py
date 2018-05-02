import json
import datetime


def updateGenInfo(profits, now, day):
    with open("../logs/generalInfo.json") as json_file:
        genInfo = json.load(json_file)

    if now.weekday() == 0 and day != genInfo["monday"]:
        genInfo["Average"] = (genInfo["Average"]*genInfo["NbWeeks"]+genInfo["thisWeek"])/(genInfo["NbWeeks"]+1)
        genInfo["NbWeeks"] += 1
        genInfo["thisWeek"] = 0.0
        genInfo["monday"] = day

    genInfo["thisWeek"] += profits

    with open('../logs/generalInfo.json', 'w') as f:
        json.dump(genInfo, f)


def newSale(profits, objType):
    now = datetime.datetime.now()

    hour = str(now.hour)
    day = str(now.month) + "/" + str(now.day)
    profits = float(profits)
    objType = str(objType)

    with open("../logs/log.json") as json_file:
        logs = json.load(json_file)

    try:
        logs[day]["Hour"] += [hour]
        logs[day]["Profits"] += [profits]
        logs[day]["ObjType"] += [objType]
    except KeyError:
        logs[day] = {"Hour": [hour],
                     "Profits": [profits],
                     "ObjType": [objType]}

    with open('../logs/log.json', 'w') as f:
        json.dump(logs, f)

    updateGenInfo(profits, now, day)
