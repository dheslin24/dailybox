#!/usr/bin/python3

from passlib.apps import custom_app_context as pwd_context
import sys
import time
from datetime import datetime, timedelta, date
import json
import requests
from db_accessor import db2 
from game_module import get_games
import logging

logging.basicConfig(filename="line.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")


starttime = time.mktime((2021, 12, 17, 18, 59, 0, 0, 0, 0))
season_type = 3
week = 1
espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?seasontype={season_type}&week={week}&limit=900"
while True:
    response = requests.get(espn_ncaa_url)
    r = response.json()

    game_dict = get_games(r, False)['game']
    #print(game_dict)
    #print(r['events'][0]['competitions'][0]['notes'][0]['headline'])

    now = datetime.utcnow() - timedelta(hours=5)
    print(now)
    print('now again')
    for game in game_dict:
        fav = ''
        spread = 0
        game_dict[game]['current_winner'] = ''
        game_in_future = game_dict[game]['datetime'] > now  # if in future, will be true.
        time_to_kickoff = game_dict[game]['datetime'] - now
        # if (game_dict[game]['line'] != 'TBD' and now.day - last_db_update.day > 1) or insert_mode == True:
        if game_dict[game]['line'] != 'TBD' and game_in_future and time_to_kickoff.total_seconds() > 3600:  # >1 hour to kickoff - record latest line
            espnid = game_dict[game]['espn_id']
            fav = game_dict[game]['line'][0]
            if len(game_dict[game]['line']) > 1 and len(game_dict[game]['line'][1]) > 1:  # to handle 'EVEN' lines, will only be ['EVEN'] with len 1
                if game_dict[game]['line'][1][-2:] == '.0':  # get rid of the -10.0 float to int.  only show float when it's a .5 spread
                    game_dict[game]['line'][1] = game_dict[game]['line'][1][:-2]
                    spread = game_dict[game]['line'][1]
                else:
                    spread = game_dict[game]['line'][1]
            else:
                spread = ''
            line_query = "INSERT INTO latest_lines (espnid, fav, spread, datetime) VALUES (%s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE espnid = %s, fav = %s, spread = %s, datetime = NOW();"
            db2(line_query, (espnid, fav, spread, espnid, fav, spread))
            logging.info(f"inserted new line: {espnid}: {fav}: {spread}: {now}")

    time.sleep(900.0 - ((time.time() - starttime) % 900.0))