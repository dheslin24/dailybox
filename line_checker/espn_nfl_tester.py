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


espnid = 401326600
season_type = 2
week = 18
#espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={espnid}"
#espn_nfl_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type}&week={week}"
espn_nfl_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={espnid}"
    
r = requests.get(espn_nfl_url).json()

for _ in r['header']['competitions']:
    print(_)
# for _ in r['events']:
#     print(_['id'], _['name'])

