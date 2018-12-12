from colorama import Fore
from time import sleep
import datetime
import json
import os

clear = lambda: os.system('cls')

def openDoc():
    with open("../logs/log.json") as json_file:
        logs = json.load(json_file)
    return logs


def getRecap(logs):
    days = []
    perDay = []
    for day in logs:
        days += [day]
    for day in days[::-1]:
        daily = sum(logs[day]["Profits"])
        perDay += [round(daily, 2)]

    return [days[::-1], perDay]


def getLastSales(logs):
    now = datetime.datetime.now()
    day = str(now.month) + "/" + str(now.day)
    
    empty = Fore.GREEN + Fore.WHITE
    sales = [empty, empty, empty, empty, empty]
    if day in logs:
        for lastish in range(5):
            try:
                hour = str(logs[day]["Hour"][::-1][lastish])
                sales[lastish] = "->" + (2-len(hour))*" " + hour + "h \u2551 "
                sales[lastish] += Fore.GREEN + str(logs[day]["Profits"][::-1][lastish]) + "$ " + Fore.WHITE
                sales[lastish] += str(logs[day]["ObjType"][::-1][lastish])
            except IndexError:
                break
    return sales


def getVisualRecap(logs):
    perDay = []
    recap = getRecap(logs)
    days = recap[0]
    profit = recap[1]
    for i in range(len(profit)):
        perDay += [(5-len(days[i]))*" " + days[i] + "\u2551" +
                   Fore.GREEN + int(profit[i])*"\u25A0" + Fore.WHITE + str(profit[i])]
    return perDay


def getWeekTotal():
    with open("../logs/generalInfo.json") as json_file:
        genInfo = json.load(json_file)

    progress = ((genInfo["thisWeek"]/genInfo["Average"])*75) if ((genInfo["thisWeek"]/genInfo["Average"])*75) < 100 \
        else 100

    weekRecap = ["\u2554" + 39*"\u2550" + "\u2557",
                 "\u2551" + 14 * " " + "Week Total" + 15 * " " + "\u2551",
                 "\u2560" + 39 * "\u2550" + "\u2569" + 34*"\u2550" + "\u2566" + 25*"\u2550" + "\u2557",
                 "\u2551" + 100*" " + "\u2551",
                 "\u255A" + 74 * "\u2550" + "\u2569" + 25 * "\u2550" + "\u255D"]
    if progress < 75:
        weekRecap[3] = "\u2551" + Fore.RED + int(progress)*"\u25A0" + Fore.WHITE + (74-int(progress))*" " +\
                       "\u2551" + 25*" " + "\u2551"
    elif 75 < progress < 101:
        weekRecap[3] = "\u2551" + Fore.GREEN + 74*"\u25A0" + Fore.WHITE +\
                       "\u2551" + Fore.GREEN + (int(progress)-75)*"\u25A0" + Fore.WHITE +\
                       (25-(int(progress)-75))*" " + "\u2551"

    return weekRecap


def afficher():
    logs = openDoc()
    lastSale = getLastSales(logs)
    visualRecap = getVisualRecap(logs)

    print("\u2554" + 39*"\u2550" + "\u2557" + 10*" " + "\u2554" + 39*"\u2550" + "\u2557")
    print("\u2551" + 13*" " + "Last 5 Sales" + 14*" " + "\u2551" + 10*" " +
          "\u2551" + 10*" " + "Last 10 Days' Chart" + 10*" " + "\u2551")
    print("\u2560" + 6*"\u2550" + "\u2566" + 32 * "\u2550" + "\u2563" + 5*" " +
          "\u2554" + 4*"\u2550" + "\u2569" + 39 * "\u2550" + "\u2569" + 10*"\u2550")
    for i in range(5):
        try:
            print("\u2551" + lastSale[i] + (49-len(lastSale[i]))*" " + "\u2551" + visualRecap[i])
        except IndexError:
            print("\u2551" + lastSale[i] + (49 - len(lastSale[i])) * " " + "\u2551" + "     \u2551")
    try:
        print("\u255A" + 6*"\u2550" + "\u2569" + 32 * "\u2550" + "\u255D" + visualRecap[5])
    except IndexError:
        print("\u255A" + 6*"\u2550" + "\u2569" + 32 * "\u2550" + "\u255D" + 5 * " " + "\u2551")
        for i in range(6, 10):
            try:
                print(41*" " + visualRecap[i])
            except IndexError:
                print(46 * " " + "\u2551")
    print(46 * " " + "\u255A" + 55*"\u2550")
    print()

    for line in getWeekTotal():
        print(line)

while True:
    clear()
    print(Fore.WHITE)
    print(afficher())
    sleep(5)

