from trueskill import Rating, rate, TrueSkill

from dbdriver import *



class HeroSkill(object):

    def __init__(self):
        self.env = TrueSkill(mu = 3000, sigma=1000)
    
    def init_players(self, player_ids):
        self.players = dict()
        for player_id in player_ids:
            self.players[player_id] = self.env.Rating()

    def loadMatches(self, matches):
        for match in matches:
            rating_group = [dict(zip(match.radiant, [self.players[p] for p in match.radiant])),
                           dict(zip(match.dire, [self.players[p] for p in match.dire])),
                           ]
            result = rate(rating_group, ranks = match.result)
            for side in result:
                for p in side.keys():
                    self.players[p] = side[p]


class Match(object):
    def __init__(self, radiant, dire, result):
        self.radiant = radiant
        self.dire = dire
        self.result = result




with ConnectionWrapper("dbname=dota user=bxu") as db:
    db.execute("select hero_id from heros")
    hero_ids = db.fetchall()

    S = HeroSkill()
    S.init_players(hero_ids)
    print S.players









S = HeroSkill()
player_ids = ["rainvargus", "schatten", "sputnik"]
S.init_players(player_ids)




match1 = Match(["rainvargus", "sputnik"], ["schatten"], [0,1])
S.loadMatches([match1])

print S.players





