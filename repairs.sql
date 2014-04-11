-- -h localhost -U bxu -d dota
select * from (select match_id, hero_id, player_id, count(match_id)  as c from played group by hero_id, match_id, player_id) as sub where sub.c = 2;

select * from played where (match_id, hero_id, player_id) = (352600166 ,       1 ,   82305385);

--update match_detail set radiant_win=NULL ;

select count(*) from match_detail  where tower_status_radiant is NULL;

--all matches that pudge won in games where schatten and me participated in
select match_id, radiant_win, hero_id, slot from matches natural join match_detail where match_id in 
(
  select match_id from matches where player_id in (select player_id from players where persona = 'rainvargus') intersect
  select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'schatten')
) 
  and hero_id = 14 and ((slot > 100 and not radiant_win) or (slot < 100 and radiant_win));

  
select match_id, radiant_win, slot from matches natural join match_detail where match_id in 
(
  select match_id from matches where player_id in (select player_id from players where persona = 'rainvargus') intersect
  select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'schatten')
) 
  and hero_id = 14 and ((slot < 100 and not radiant_win) or (slot  > 100 and radiant_win));

  
  select match_id, radiant_win, slot from matches natural join match_detail natural join
  (select slot  from matches natural join players where persona = 'rainvargus') on ;
  
  
  where match_id in 
(
  select match_id from matches where player_id in (select player_id from players where persona = 'rainvargus') intersect
  select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'schatten')
) 
  and hero_id = 14 and ((slot < 100 and not radiant_win) or (slot  > 100 and radiant_win));


select match_id, radiant_win, slot from matches natural join match_detail where match_id in 
(
  select match_id from matches where player_id in (select player_id from players where persona = 'rainvargus') intersect
  select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'schatten')
) 
  and hero_id = 14;
 
  and ((slot < 100 and not radiant_win) or (slot  > 100 and radiant_win));



select m.match_id, radiant_win, m.slot, p.slot from 
(
--find all matches where schatten or me participated
select match_id, radiant_win, slot from matches natural join match_detail where match_id in 
(
  select match_id from matches where player_id in (select player_id from players where persona = 'rainvargus') 
  --intersect
  --select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'sputnik')
) 
--and have pudge
  and hero_id = 14
) as m
--put me back in to get slot numbers
join (  select match_id, slot from matches where player_id in (select player_id from players where persona = 'rainvargus') ) as p
on m.match_id = p.match_id
--pudge in other team
where abs(m.slot - p.slot) > 100
--get pudge wins
and ((m.slot < 100 and radiant_win) or (m.slot  > 100 and not radiant_win));

CREATE OR REPLACE FUNCTION findmatches(personas text[] ) RETURNS table (match_id bigint, persona text, slot smallint, hero_id smallint)
    AS $$ SELECT match_id, persona, slot, hero_id from matches NATURAL JOIN players where LOWER(persona) = ANY(personas) $$
        LANGUAGE SQL;

select * from findmatches('{schatten}')


select m.match_id, radiant_win, m.slot, p.slot from 
(
--find all matches where schatten or me participated

--intersect
  --select match_id from matches where player_id in (select player_id from players where LOWER(persona) = 'sputnik')
--and have pudge
  and hero_id = 14
) as m
--put me back in to get slot numbers
join (  select match_id, slot from matches where player_id in (select player_id from players where persona = 'rainvargus') ) as p
on m.match_id = p.match_id
--pudge in other team
where abs(m.slot - p.slot) > 100
--get pudge wins
and ((m.slot < 100 and radiant_win) or (m.slot  > 100 and not radiant_win));


select match_id, our_slot, pudge_slot, radiant_win from (
select found.match_id, count(persona), min(found.slot) as our_slot, min(m.slot) as pudge_slot from findmatches('{rainvargus, schatten}') as found right join matches as m on found.match_id = m.match_id
where m.hero_id = 14 group by found.match_id
 )as res natural join match_detail where count = 2;

DROP FUNCTION played_as_team(text[]);
CREATE OR REPLACE FUNCTION played_as_team(personas text[] ) RETURNS table (match_id bigint, on_radiant boolean, radiant_win boolean )
AS $$ SELECT match_id, min(slot) < 100 AS on_radiant, radiant_win FROM findmatches(personas) natural join match_detail GROUP BY match_id, radiant_win
HAVING count(slot) = array_length(personas, 1)$$
LANGUAGE SQL;

select * from played_as_team('{rainvargus, chroniko}');




DROP FUNCTION played_as_team_with_hero(text[],text);

CREATE OR REPLACE FUNCTION played_as_team_with_hero(personas text[], hero text) RETURNS table (match_id bigint, on_radiant boolean, radiant_win boolean, hero_on_radiant boolean)
AS $$SELECT match_id, on_radiant, slot < 100, radiant_win as hero_on_radiant from played_as_team(personas) 
natural join 
matches 
natural join match_detail
where hero_id in (select hero_id from heros where LOWER(hero_name) = hero)$$
LANGUAGE SQL;


SELECT match_id, on_radiant, slot < 100 as hero_on_radiant from played_as_team('{rainvargus, schatten}') natural join matches where 
hero_id in (select hero_id from heros where hero_name = LOWER())

select * from played_as_team_with_hero('{rainvargus, schatten}', 'bounty') order by match_id;


select * from heros;

DROP FUNCTION played_as_hero_with_team(text,text,text[]);

CREATE OR REPLACE FUNCTION played_as_hero_with_team(param_persona text, param_hero text, param_personas text[]) RETURNS table (match_id bigint, on_radiant boolean, radiant_win boolean)
AS $$SELECT match_id, slot < 100 as on_radiant, radiant_win FROM 
matches 
natural join players as p natural join heros natural join match_detail
where lower(param_persona) = lower(p.persona) AND lower(param_hero) = lower(hero_name) 
AND match_id in (select match_id from played_as_team(param_personas || param_persona))
$$
LANGUAGE SQL;

SELECT match_id, slot < 100 as on_radiant, radiant_win FROM 
matches natural join players as p natural join heros natural join match_detail
where lower('schatten') = lower(p.persona) AND 'pudge' = lower(hero_name) 

select * from played_as_hero_with_team('schatten', 'bounty_hunter', '{zeromind}');

select * from played_as_hero_with_team('Fire-storm', 'phantom_assassin', '{}');

CREATE FUNCTION intime(match_ids bigint[], minstarttime bigint default 0, maxstarttime bigint default 9223372036854775807) RETURNS table (isintime boolean)
AS $$
SELECT (start_time >= minstarttime and start_time <= maxstarttime) as isintime from match_detail where match_id = ANY(match_ids)
$$
LANGUAGE SQL;
select * from played_as_hero_with_team('rainvargus', 'abaddon', '{}');

select * from players;

select (slot < 100) = radiant_win as WON, match_id from matches natural join (
select * from match_detail natural join (
select distinct match_id from matches where match_id >= 562908933 and match_id not in (
select match_id from matches where player_id in (
select m2.player_id from matches m join matches m2 on m.match_id = m2.match_id where m.player_id <> m2.player_id and m2.player_id <>4294967295 
and
m.player_id in  (select player_id from players where lower(persona)='rainvargus' and m.match_id >= 562908933) group by m2.player_id having count(*) >=2)
)
) m2 )m3
where player_id in (select player_id from players where lower(persona) = 'rainvargus') order by match_id desc

