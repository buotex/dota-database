import os
import requests
#from xml.dom.minidom import parseString
from pyparsing import *
from bs4 import BeautifulSoup as bs
import itertools
import re
import sys

import time
import json
import simplejson
import jsonschema

import numpy
import scipy
import sklearn
import datetime
from dateutil.relativedelta import relativedelta

from dbdriver import *

STEAM_API_KEY = os.environ["STEAMODD_API_KEY"]
PARAMS = {"key" : STEAM_API_KEY}




class Winrate(object):
    sort = {
        "winrate": { 
            "key": lambda x: (x[0], x[1]),
            "reverse": True
            },
        "hero_name": {
            "key": lambda x: x[4]
        }
    }


def getDates(delta):
    after = int(((datetime.datetime.today() + delta) - datetime.datetime(1970,1,1)).total_seconds())
    before= int((datetime.datetime.today() - datetime.datetime(1970,1,1)).total_seconds())
    return [after, before]


def createValueString(values):
    return (', '.join(len(values) * ['{}'])).format(*values)

#def createArrayString(values):
#    #return "\'\{" + ', '.join(len(values) * ['{}']) \}\'".format()

def createInsert(table, values):
    runstring = 'INSERT INTO {}'.format(table)+' VALUES (' + createValueString(values) + ')'
    return runstring

def wrapString(string):
    return "'{}'".format(string)

def createNamedInsert(table, **kwargs):
    runstring = 'INSERT INTO {} '.format(table) +\
    '(' + createValueString(kwargs.keys()) + ')' +\
    ' VALUES (' + \
     createValueString(kwargs.values()) + ')'
    return runstring

def createWhere(key, val):
    return "{} = {}".format(key, val)

def createWhereStrings(**kwargs):
    wherestring = 'WHERE ' + " AND ".join([createWhere(key, val) for key, val in kwargs.items()])
    return wherestring

def createNamedUpdate(table, where, **kwargs):
    runstring = 'UPDATE {} '.format(table) +\
    'SET (' + createValueString(kwargs.keys()) + ')' +\
    ' = (' + \
     createValueString(kwargs.values()) + ') ' + createWhereStrings(**where)

    return runstring


def filterString(string):
    string = string.decode('unicode-escape').decode('ascii', 'ignore')
    r = re.compile(r'[^A-z\[\]-]')
    return r.sub('', string)

def getJavascript(url, **kwargs):
    request = requests.get(url, **kwargs)
    soup = bs(request.text.encode('utf-8'))
    scriptResults = soup('script', {'type' : 'text/javascript'})
    return scriptResults

def getJson(url, **kwargs):
    request = requests.get(url, **kwargs)
    try:
        json = request.json()
    except simplejson.decoder.JSONDecodeError:
        print "Could not decode \n{}".format(request.text)
        raise
    return json
        
def getText(url, **kwargs):
    request = requests.get(url, **kwargs)
    soup = bs(request.text.encode('utf-8'))
    return soup

class pyparseHelper:

    keyval = quotedString + Suppress(":") + quotedString
    idSpec = Suppress(Literal('g_rgProfileData = '))  +Suppress('{') + delimitedList(keyval) + Suppress('}')
    heroNameSpec = Suppress(Literal('\"url\"')) + quotedString
    heroAliasesSpec = Suppress(Literal('\"NameAliases\"')) + QuotedString('"')
    heroIdSpec = Suppress(Literal('\"HeroID\"')) + quotedString
    quotedString.setParseAction(removeQuotes)





def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(itertools.islice(a,0,None,2), itertools.islice(b,0,None,2))

def stringToSteamId(string):
    v = 0x0110000100000000
    y = int(string[8])
    z = int(string[10:])
    return v + y + 2 * z

def steamIdTo32(steamid):
    rem = steamid - 0x0110000100000000
    return rem

def steamIdToString(steamid):
    rem = steamid - 0x0110000100000000
    y = rem % 2
    z = (rem - y) / 2
    return "STEAM_0:{}:{}".format(y,z)



def getTokens(spec, iterable):
    tokens = []
    for i in iterable:
        found = spec.searchString(i)
        if found:
            for f in found:
                tokens.extend(f)
    return tokens

def getPersonaFrom64(steamid64):

    STEAM_PROFILE_URL='http://steamcommunity.com/profiles/{}'.format(steamid64)
    scriptResults = getJavascript(STEAM_PROFILE_URL)
    tokens = getTokens(pyparseHelper.idSpec, scriptResults)
    jsonData = {}
    for key, value in pairwise(tokens):
        jsonData[key] = value
    persona = jsonData["personaname"]
    persona = filterString(persona)
    return persona


def vanityToSteamId(vanity):

    STEAM_PROFILE_URL='http://steamcommunity.com/id/{}'.format(vanity)
    scriptResults = getJavascript(STEAM_PROFILE_URL)
    tokens = getTokens(pyparseHelper.idSpec, scriptResults)
    jsonData = {}
    for key, value in pairwise(tokens):
        jsonData[key] = value
    return int(jsonData["steamid"])

#bit64 = steamIdTo64("STEAM_0:0:23599837")
def getFriendList(steamid64):
    
    STEAM_FRIEND_URL="http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={}&steamid={}&relationship=friend".format(STEAM_API_KEY,
        steamid64)
    json = getJson(STEAM_FRIEND_URL, params = params)
    friends = json["friendslist"]["friends"]
    return [int(friend["steamid"]) for friend in friends]


def insertPlayers(db, steamidList):
    for id in steamidList:
        try:
            persona = getPersonaFrom64(id)
        except:
            continue
        persona = "\'" + persona +"\'"
        steamid32 = steamIdTo32(id)

        db.execute(createInsert("players", [steamid32, persona]))



#def filterMatches(matchlist):
    


def insertMatch(db, match):
    matchid = match["match_id"]
    starttime = match["start_time"] 
    players = match["players"]
    runstrings = []
    runstring = createInsert("match_detail", [matchid, starttime])
    failed = db.execute(runstring)
    if failed:
        return 1



    
    for player in players:
        try:
            playerdata = [player["account_id"], player["player_slot"], player["hero_id"]]
            runstrings.append( createInsert("matches", [matchid,]  + playerdata) )
        except:
            print playerdata
            
    if len(runstrings) == 10:
        for s in runstrings:
            try:
                failed = db.execute(s)
                if failed:
                    deletestring = "DELETE from match_detail where match_id = {}".format(matchid)
                    db.execute(deletestring)
                    break
                    
            except Exception as e:
                print e

def getOldestGameTime(steamid):
    qstring = 'select min(start_time) from match_detail where match_id \
    in (select match_id from matches where player_id = {})'.format(steamid)
    result = db.one(qstring)
    return result 

def getMatchDetails(matchid):
    STEAM_MATCH_URL = "https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001"
    params = PARAMS.copy()
    params["match_id"] = matchid
    matchdetail = getJson(STEAM_MATCH_URL, params = params)

    return matchdetail["result"]

def _getMatchHistory(steamid, **kwargs):
    STEAM_HISTORY_URL = "https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001"
    params = PARAMS.copy()
    params["account_id"] = steamid
    #params["min_players"] = 10
    params.update(kwargs)
    matchlist = getJson(STEAM_HISTORY_URL, params = params)

    return matchlist["result"]["matches"]


def updateMatches(db, account_id, hero_id= 0 ):
    oldest_match_id = 0
    while 1:
        matches = _getMatchHistory(account_id, hero_id = hero_id, start_at_match_id = oldest_match_id)
        if len(matches) == 0: 
            break
        oldest_match_id = matches[-1]["match_id"]
        #t = getOldestGameTime(account_id)
        for match in matches:
            insertMatch(db, match)
        if len(matches) < 100:
            break

def getAllMatches(db, account_id):

    db.execute("SELECT hero_id from heros")
    hero_ids = [hero[0] for hero in db.fetchall()]
    for hero_id in hero_ids:
        updateMatches(db, account_id, hero_id)


def insertMatchDetails(match):
    #backup = open("matchdetail", 'w')
    #json.dump(match, backup)
    
    detailparams = {}
    where = {"match_id" : match["match_id"]}
    for p in ["start_time", "radiant_win", "duration", "tower_status_radiant", "barracks_status_radiant",
              "barracks_status_dire", "game_mode"]:
        detailparams[p] = match[p]    

    dstring = createNamedUpdate("match_detail", where,  **detailparams)
    db.execute(dstring)

    for p in match["players"]:
        where = {"match_id": match["match_id"], "player_id": p["account_id"], "hero_id" : p["hero_id"]}
        playerparams = {}
        for i in ['gold_spent', 'gold', 'deaths', 'hero_damage',
                  'last_hits', 'denies',
                  'tower_damage', 'xp_per_min', 'kills',
                  'hero_healing', 'assists', 'gold_per_min',
                  'level', 'item_4', 'item_5', 'item_2', 'item_3',
                  'item_0', 'item_1']:
            playerparams[i] = p[i]
        
        playerparams.update(where)
        pstring = createNamedInsert("played", **playerparams)
        db.execute(pstring)

    



def fillMatchDetails():
    db.execute('select match_id from match_detail where radiant_win is NULL')
    records = db.fetchall()
    print "{} new matches found".format(len(records))
    counter = 0
    for record in records:
        details = getMatchDetails(record)
        insertMatchDetails(details)
        print "{}/{} done".format(counter, len(records))
        counter = counter + 1
        

def insertHeroIds(db):
    source = "https://raw.github.com/dotabuff/d2vpk/master/dota_pak01/scripts/npc/npc_heroes.txt"
    herolist = getText(source)
    heronames = getTokens(pyparseHelper.heroNameSpec, herolist)
    heroids = getTokens(pyparseHelper.heroIdSpec, herolist)
    #heroaliases = getTokens(pyparseHelper.heroAliasesSpec, herolist)
    
    def splitAlias(alias):
        pat = re.findall('[A-z]+', alias)
        return pat
        
    heronames.remove("Centaur Warchief") #workaround, file is buggy

    for name, id in zip(heronames, heroids):
        #aliases = splitAlias(alias)
        #aliasstring= "\'{" + createValueString(aliases) + "}\'"
        runstring = createInsert('heros', [int(id), wrapString(name)])
        db.execute(runstring)

def getWinrate(records, **kwargs):
    try:
        if kwargs['intime']:
            queryrecords = [record[0] for record in records]
            recordstring = "'{" + createValueString(queryrecords) + "}'"
            after = kwargs['intime'][0]
            before = kwargs['intime'][1]
            valid = db.all('SELECT * from intime({},{},{})'.format(recordstring, after, before))
            records = [r for r,v in zip(records,valid) if v]
    except:
        pass

    numMatches = len(records)
    numWins = len([record for record in records if record[1] == record[2]])
    numLosses = numMatches - numWins
    try:
        winrate = float(numWins * 100) / numMatches
    except:
        winrate = 0
    
    return [winrate, numWins, numLosses]

def checkWinrateTuples(players, hero_involved = None, hero_same_team = True, **kwargs):
    personastring = "\'{" + createValueString(players) + "}\'"

    if not hero_involved:
        querystring = "Select * from played_as_team({})".format(personastring)
    else:
        querystring = "Select * from played_as_team_with_hero({}, '{}')".format(personastring, hero_involved)
    records = db.all(querystring)

    herostring = ""
    if hero_involved:
        if hero_same_team:
            herostring = " with {}".format(hero_involved)
            records = [record for record in records if record[1] == record[3]]
        else:
            herostring = " against {}".format(hero_involved)
            records = [record for record in records if record[1] == (not record[3])]
    
    descstring = ", ".join(players) + herostring
    winrate, numWins, numLosses = getWinrate(records, **kwargs)
    return [winrate, numWins, numLosses, descstring, hero_involved]

def checkWinrate(players, hero_involved = None, hero_same_team = True, **kwargs):

    result = checkWinrateTuples(players, hero_involved, hero_same_team) 

    retstring = "Overall Winrate for {}: {:.02f}%, ({} - {})".format(result[3], result[0],result[1],result[2])

    return retstring

def checkWinrateOnHeroTuples(player, hero_name, played_with = None, **kwargs):
    played_with_string = "{" + createValueString(played_with) + "}"
    runstring = "select * from played_as_hero_with_team('{}', '{}','{}')".format(player, hero_name, played_with_string)
    records = db.all(runstring)

    winrate, numWins, numLosses = getWinrate(records, **kwargs)
    descstring = "{} on {} with ".format(player, hero_name) + ", ".join(played_with)
    return [winrate, numWins, numLosses, descstring, hero_name]

def checkWinrateOnHero(player, hero_name, played_with = None, **kwargs):
    result = checkWinrateOnHeroTuples(player, hero_name, played_with, **kwargs)

    retstring = "Overall Winrate for {}: {:.02f}%, ({} - {})".format(result[3], result[0], result[1], result[2])
    return retstring 


def checkWinrateOnAllHerosWithPlayers(player, played_with = None, key = Winrate.sort["winrate"], **kwargs):
    hero_ids = db.all('select hero_id from heros')
    hero_names = db.all('select hero_name from heros')
    
    results = []
    for name in hero_names:
        results.append(checkWinrateOnHeroTuples(player, name.lower(), played_with, **kwargs))
    results = sorted(results, **key)
    for result in results:
        retstring = "Overall Winrate for {}: {:.02f}%, ({} - {})".format(result[3], result[0], result[1], result[2])
        if result[1] + result[2] > 0:
            print retstring 
    return results


def checkWinrateAllHeros(players, hero_same_team = True, key = Winrate.sort['winrate'], **kwargs):
    hero_ids = db.all('select hero_id from heros')
    hero_names = db.all('select hero_name from heros')
    
    results = []
    for name in hero_names:
        results.append(checkWinrateTuples(players, name.lower(), hero_same_team, **kwargs))
    results = sorted(results, **key)
    for result in results:
        retstring = "Overall Winrate for {}: {:.02f}%, ({} - {})".format(result[3], result[0], result[1], result[2])
        if result[1] + result[2] > 0:
            print retstring 
    return results
    
def rankHeros():
    gpm = db.all('SELECT hero_name, avg(gold_per_min) from played natural join heros group by hero_id, hero_name')
    gpm = sorted(gpm, key = lambda x: x[1])
    gold = [float(record[1]) for record in gpm] 
    hist = numpy.histogram(gold, bins = 5)
    go.db


    

if  __name__ == "__main__":


    with ConnectionWrapper("dbname=dota user=bxu") as db:
        #initializations
        #insertHeroIds(db)

        #account_id = db.one("select player_id from players where LOWER(persona) = 'rainvargus'")
        bit64 = vanityToSteamId("rainvargus")
        #insertPlayers(db, [bit64])

        #matches = getMatchHistory(bit64)
        #print db.fetchall()
        #matches = getAllMatches(db, bit64)
        #for match in matches:
        #    insertMatch(db, match)
        fillMatchDetails()

    #bit64 = stringToSteamId("STEAM_0:0:23599837")
    #print bit64
    #getNameFrom64(bit64)
    #print getNameFrom64(76561198049183649)
    #getFriendList(bit64)
    #friends = getFriendList(bit64)
    
    #insertPlayers(friends[57:])
     
    #t = getOldestGameTime(account_id)
    #matchid = db.one("select match_id from match_detail where start_time = {}".format(t))
    #print t
    #print matchid
    #matchdetails = getMatchDetails(matchid)
    #print matchdetails
    #matches = getMatchHistory(account_id, date_max = 1349382647)
    #go.db
    #print createNamedInsert("matches", asdf = "bla", blub = 3)
    #print createWhereStrings( asdf = "bla", blub = 3)
    #print createValueString(["rainvargus", "schatten"])
    #print checkWinrate(['rainvargus', 'schatten'], 'drow', False)
    #print checkWinrate(['rainvargus', 'chroniko'], 'outworld_devourer', True)
    #print checkWinrate(['Fire-storm' ], 'Phantom_Assassin')
    #results = checkWinrateAllHeros([ 'rainvargus', 'Fire-storm'], True)
    #print results
    #print checkWinrateOnAllHerosWithPlayers('schatten', ['rainvargus', ], key = Winrate.sort['hero_name'])
    #checkWinrateOnAllHerosWithPlayers('rainvargus', [], key = Winrate.sort['hero_name'])
    #checkFarmRateOnAllHerosWithPlayers('schatten', ['rainvargus'])
    #print checkWinrateOnHero('rainvargus', 'templar_assassin', ['chroniko'])
    #rankHeros()
    
    
    
    #checkWinrateOnAllHerosWithPlayers('rainvargus', [], intime = getDates(relativedelta(months = -6)))
