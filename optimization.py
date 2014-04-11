import dota
import numpy as np
from numpy import random

import anneal


#Build the adjacency matrix

db = dota.PostgresWrapper("postgres://bxu@localhost/dota")

match_ids = db.all('select match_id from match_detail')
hero_ids = db.all('select hero_id from heros')
hero_names = db.all('select hero_name from heros')
hero_dict = {}
for id, name in zip(hero_ids, hero_names):
    hero_dict[id] = name

for i in range(np.max(hero_ids) + 1):
    if i not in hero_ids:
        hero_dict[i] = ""

adjacency_matrix = np.array((np.max(hero_ids)+1, np.max(hero_ids)+1))
#db.all('select * from matches 


records = db.all('select array_agg(hero_id) as hero, array_agg(gold_per_min) as gpm,\
                 array_agg(xp_per_min) as xpm, array_agg(slot) as slot, bool_and(radiant_win),\
                 array_agg(kills) as kills, array_agg(assists) as assists, array_agg(deaths) as deaths,\
                 array_agg(hero_damage) as hero_damage, array_agg(tower_damage) as tower_damage\
                 from played natural join matches natural join match_detail group by match_id')

winrates = db.all('select avg(radiant_win::int) as winrate, hero_id from played natural\
 join heros natural join match_detail group by hero_id, hero_name order by hero_id')

winratematrix = np.zeros((np.max(hero_ids)+1, 2), dtype = object)
for record in winrates:
    winratematrix[record[1]] = [record[0], hero_dict[record[1]]]

def rankHerosGpm(records):

    for record in records:
        indices = np.argsort(record[3])
        offset = record[4] * 5
        record = np.array(record[0:4])
        hero_ids = record[0][indices]
        gpm = record[1][indices]
        xpm = record[2][indices]
        
        gpm_indices = np.argsort(gpm[offset:offset+5])
        hero_id_ranking = hero_ids[offset:offset+5][gpm_indices]
        for i,j in zip(hero_id_ranking[:-1], hero_id_ranking[1:]):
            adjacency_matrix[i,j] += 1
            adjacency_matrix[j,i] -= 1

    def evalfunc(ordering):
        obj = 0
        for i, hero_id in enumerate(ordering):
            row = adjacency_matrix[hero_id, ordering]
            obj += np.sum(row[i:])
        return obj

    def move(ordering):
        a,b = random.randint(0,len(ordering), size = 2)
        ordering[a], ordering[b] = ordering[b], ordering[a]
        return ordering


    #minimum = optimize.anneal(evalfunc, range(adjacency_matrix.shape[0]), maxiter = 50)

    ordering = range(adjacency_matrix.shape[0])

    annealer = anneal.Annealer(evalfunc, move)
    schedule = annealer.auto(ordering, minutes = 1, steps = 200)
    ordering, e = annealer.anneal(ordering, schedule['tmax'], schedule['tmin'], schedule['steps'], updates = 6)

    for o in ordering:
        print hero_dict[o]


def rankHerosPartnerKDA(records, hero_ids, winrates):
    values = np.zeros((np.max(hero_ids)+1, 3))
    counts = np.zeros((np.max(hero_ids)+1))
    for record in records:
        indices = np.argsort(record[3])
        hero_ids = np.array(record[0])[indices]
        record = np.array(record[5:])
        record = record[:,indices]
        kills = [np.sum(record[0][:4]), np.sum(record[0][4:])]
        assists= [np.sum(record[1][:4]), np.sum(record[1][4:])]
        deaths = [np.sum(record[2][:4]), np.sum(record[2][4:])]
        for i, hero_id in enumerate(hero_ids):
            offset = (i > 4)
            counts[hero_id] +=1
            values[hero_id] += np.array([kills[offset], assists[offset], deaths[offset]])
    counts = 1./counts.astype(np.float)
    values = counts.reshape(values.shape[0],1) * values.astype(np.float)

    go.db
    kda = np.nan_to_num((values[:,0]) / (values[:,2]))
    
    result = np.concatenate((kda[:,None], winratematrix),axis = 1 )
    return result[result[:,0].argsort()]

if __name__ == "__main__":
    #rankHerosGpm(records)
    print rankHerosPartnerKDA(records, hero_ids, winrates)
