import os
import requests
import json
#from xml.dom.minidom import parseString
from pyparsing import *
from bs4 import BeautifulSoup as bs
import itertools
import re
import sys

import postgres
import psycopg2
import time
class PostgresWrapper(postgres.Postgres):
    def run(self, sql, parameters = None, *args,**kwargs):
        try:
            postgres.Postgres.run(self, sql, parameters, *args, **kwargs)
            return 0
        except psycopg2.IntegrityError:
            return 1
        except:
            raise
db = PostgresWrapper("postgres://bxu@localhost/dota")

STEAM_API_KEY = os.environ["STEAMODD_API_KEY"]
PARAMS = {"key" : STEAM_API_KEY}

def createInsert(table, values):
    runstring = 'INSERT INTO {}'.format(table)+' VALUES (' + (','.join(len(values) * ['{}'])).format(*values) + ')'
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
    json = request.json()
    return json
        
def getSoup(url, **kwargs):
    request = requests.get(url, **kwargs)
    soup = bs(request.text.encode('utf-8'))
    return soup

class pyparseHelper:

    keyval = quotedString + Suppress(":") + quotedString
    idSpec = Suppress(Literal('g_rgProfileData = '))  +Suppress('{') + delimitedList(keyval) + Suppress('}')
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


def insertPlayers(steamidList):
    for id in steamidList:
        try:
            persona = getPersonaFrom64(id)
        except:
            continue
        persona = "\'" + persona +"\'"
        steamid32 = steamIdTo32(id)

        db.run(createInsert("players", [steamid32, persona]))


def getMatchHistory(steamid, **kwargs):
    STEAM_HISTORY_URL = "https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001"
    params = PARAMS.copy()
    params["account_id"] = steamid
    params.update(kwargs)
    matchlist = getJson(STEAM_HISTORY_URL, params = params)

    return matchlist["result"]["matches"]

def filterMatches(matchlist):
    


def insertMatch(match):
    matchid = match["match_id"]
    starttime = match["start_time"] 
    players = match["players"]
    runstrings = []
    runstrings.append(createInsert("match_detail", [matchid,starttime]))
    
    for player in players:
        try:
            playerdata = [player["account_id"], player["player_slot"], player["hero_id"]]
            runstrings.append( createInsert("matches", [matchid,]  + playerdata) )
        except:
            print playerdata
            go.db
            
    if len(runstrings) == 11:
        for s in runstrings:
            try:
                failed = db.run(s)
                if failed:
                    deletestring = "DELETE from match_detail where match_id = {}".format(matchid)
                    db.run(deletestring)
                    break
                    
            except:
                go.db




if  __name__ == "__main__":
    #bit64 = stringToSteamId("STEAM_0:0:23599837")
    #bit64 = vanityToSteamId("rainvargus")
    account_id = db.one("select player_id from players where persona = 'rainvargus'")
    #print bit64
    #getNameFrom64(bit64)
    #print getNameFrom64(76561198049183649)
    #getFriendList(bit64)
    #friends = getFriendList(bit64)
    #insertPlayers([bit64])
    
    #insertPlayers(friends[57:])
     
    matches = getMatchHistory(account_id)
    for match in matches:
        insertMatch(match)
