-- -h localhost -U bxu -d dota
DROP table matches;


DROP table match_detail CASCADE;
CREATE table match_detail
(match_id bigint, start_time int,
radiant_win boolean, duration smallint, tower_status_radiant smallint, tower_status_dire smallint,
barracks_status_radiant smallint, barracks_status_dire smallint, game_mode smallint,
PRIMARY KEY (match_id));

CREATE table matches 
(match_id bigint, player_id bigint, slot smallint, hero_id smallint,
	FOREIGN KEY (match_id) REFERENCES match_detail(match_id) ON DELETE CASCADE,
	CONSTRAINT player_entry PRIMARY KEY (match_id, player_id, hero_id));

DROP table played;

CREATE table played
(match_id bigint, player_id bigint, hero_id smallint, player_slot smallint, item_0 smallint, item_1 smallint, item_2
smallint, item_3 smallint, item_4 smallint, item_5 smallint, kills smallint, deaths smallint, assists smallint, gold
smallint, last_hits smallint, denies smallint, gold_per_min smallint, xp_per_min smallint, gold_spent smallint,
hero_damage int, tower_damage int, hero_healing int, level smallint, ability_upgrades char[25],
FOREIGN KEY (match_id, player_id, hero_id) references matches(match_id, player_id, hero_id) ON DELETE CASCADE
);

DROP table players;
CREATE table players
(player_id bigint, persona text,
	PRIMARY KEY(player_id));


CREATE FUNCTION enter_played() RETURNS trigger AS $enter_played$
    BEGIN
        -- Check that empname and salary are given
        
	INSERT INTO played VALUES (NEW.match_id, NEW.player_id, NEW.hero_id);
	RETURN NEW;
    END;
$enter_played$ LANGUAGE plpgsql;


CREATE trigger games_played
after insert ON matches
FOR EACH ROW
EXECUTE PROCEDURE enter_played();


delete from matches;
delete from match_detail;
delete from played;
