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


espnid = 401326625
# cpf playoff link
espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={espnid}"
espn_nfl_url_single = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={espnid}"
season_type = 3 # post season
week = 4
espn_nfl_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type}&week={week}"
espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?seasontype={season_type}&week={week}&limit=900"



#r = requests.get(espn_nfl_url).json()
r = requests.get(espn_nfl_url).json()

# single espnid testing
#print(r.keys())
print("\n\n")
print(r)

# print(f"{r['boxscore']['teams']}")

# print(r['scoringPlays'])
# for score in r['scoringPlays']:
#     print(f"\n\n{score}")

# --- live game output ---
# {'id': '401326625574', 'type': {'id': '67', 'text': 'Passing Touchdown', 'abbreviation': 'TD'}, 
# 'text': 'Odell Beckham Jr. Pass From Matthew Stafford for 4 Yrds M.Gay extra point is GOOD, Center-M.Orzech, Holder-J.Hekker.', 'awayScore': 0, 'homeScore': 7, 
# 'period': {'number': 1}, 'clock': {'value': 230.0, 'displayValue': '3:50'}, 'team': {'id': '14', 'uid': 's:20~l:28~t:14', 'displayName': 'Los Angeles Rams', 
# 'abbreviation': 'LAR', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/lar/los-angeles-rams', 'text': 'Clubhouse'},
#  {'href': 'https://www.espn.com/nfl/team/schedule/_/name/lar', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}

# {'id': '4013266251002', 'type': {'id': '68', 'text': 'Rushing Touchdown', 'abbreviation': 'TD'}, 
# 'text': 'Matthew Stafford 1 Yard Rush, M.Gay extra point is GOOD, Center-M.Orzech, Holder-J.Hekker.', 'awayScore': 0, 'homeScore': 14, 'period': {'number': 2}, 
# 'clock': {'value': 718.0, 'displayValue': '11:58'}, 'team': {'id': '14', 'uid': 's:20~l:28~t:14', 'displayName': 'Los Angeles Rams', 
# 'abbreviation': 'LAR', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/lar/los-angeles-rams', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/lar', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}

# {'id': '4013266251385', 'type': {'id': '36', 'text': 'Interception Return Touchdown', 'abbreviation': 'TD'}, 
# 'text': 'David Long Jr. 3 Yrd Interception Return M.Gay extra point is GOOD, Center-M.Orzech, Holder-J.Hekker', 'awayScore': 0, 'homeScore': 21, 
# 'period': {'number': 2}, 'clock': {'value': 479.0, 'displayValue': '7:59'}, 'team': {'id': '14', 'uid': 's:20~l:28~t:14', 'displayName': 'Los Angeles Rams', 
# 'abbreviation': 'LAR', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/lar/los-angeles-rams', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/lar', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}

# {'id': '4013266252222', 'type': {'id': '67', 'text': 'Passing Touchdown', 'abbreviation': 'TD'}, 
# 'text': 'Cooper Kupp Pass From Matthew Stafford for 7 Yrds M.Gay extra point is GOOD, Center-M.Orzech, Holder-J.Hekker', 'awayScore': 0, 'homeScore': 28, 
# 'period': {'number': 3}, 'clock': {'value': 636.0, 'displayValue': '10:36'}, 'team': {'id': '14', 'uid': 's:20~l:28~t:14', 'displayName': 'Los Angeles Rams', 
# 'abbreviation': 'LAR', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/lar/los-angeles-rams', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/lar', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}

# ------- 2 pt converstion below -------
# {'id': '4013266252535', 'type': {'id': '68', 'text': 'Rushing Touchdown', 'abbreviation': 'TD'}, 
# 'text': 'James Conner 2 Yard Rush, (Pass formation) TWO-POINT CONVERSION ATTEMPT. K.Murray pass to A.Wesley is complete. ATTEMPT SUCCEEDS.', 
# 'awayScore': 8, 'homeScore': 28, 'period': {'number': 3}, 'clock': {'value': 251.0, 'displayValue': '4:11'}, 'team': {'id': '22', 'uid': 's:20~l:28~t:22', 
# 'displayName': 'Arizona Cardinals', 'abbreviation': 'ARI', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/ari/arizona-cardinals', 
# 'text': 'Clubhouse'}, {'href': 'https://www.espn.com/nfl/team/schedule/_/name/ari', 'text': 'Schedule'}], 
# 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/ari.png'}, 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}


# --- past game ---
# scoring plays output:
# [{'id': '4013266281181', 'type': {'id': '9', 'text': 'Fumble Recovery (Own)'}, 'text': 'T.J. Watt 26 Yd Fumble Return (Chris Boswell Kick)', 'awayScore': 7, 
# 'homeScore': 0, 'period': {'number': 2}, 'clock': {'value': 641.0, 'displayValue': '10:41'}, 'team': {'id': '23', 'uid': 's:20~l:28~t:23', 'displayName': 
# 'Pittsburgh Steelers', 'abbreviation': 'PIT', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/pit/pittsburgh-steelers', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/pit', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266281536', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Jerick McKinnon 4 Yd pass from Patrick Mahomes (Harrison Butker Kick)', 'awayScore': 7, 
# 'homeScore': 7, 'period': {'number': 2}, 'clock': {'value': 345.0, 'displayValue': '5:45'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 'displayName': 
# 'Kansas City Chiefs', 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266281846', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Byron Pringle 12 Yd pass from Patrick Mahomes (Harrison Butker Kick)', 'awayScore': 7, 
# 'homeScore': 14, 'period': {'number': 2}, 'clock': {'value': 115.0, 'displayValue': '1:55'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 
# 'displayName': 'Kansas City Chiefs', 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 
# 'Clubhouse'}, {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266282167', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Travis Kelce 48 Yd pass from Patrick Mahomes (Harrison Butker Kick)', 'awayScore': 7, 'homeScore': 21, 
# 'period': {'number': 2}, 'clock': {'value': 13.0, 'displayValue': '0:13'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 'displayName': 'Kansas City Chiefs', 
# 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266282480', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Nick Allegretti 1 Yd pass from Patrick Mahomes (Harrison Butker Kick)', 'awayScore': 7, 
# 'homeScore': 28, 'period': {'number': 3}, 'clock': {'value': 613.0, 'displayValue': '10:13'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 
# 'displayName': 'Kansas City Chiefs', 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266282655', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Tyreek Hill 31 Yd pass from Patrick Mahomes (Harrison Butker Kick)', 'awayScore': 7, 'homeScore': 35, 
# 'period': {'number': 3}, 'clock': {'value': 554.0, 'displayValue': '9:14'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 'displayName': 'Kansas City Chiefs', 
# 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 'scoringType': 
# {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266282949', 'type': {'id': '67', 'text': 'Passing Touchdown', 
# 'abbreviation': 'TD'}, 'text': 'Diontae Johnson 13 Yd pass from Ben Roethlisberger (Chris Boswell Kick)', 'awayScore': 14, 'homeScore': 35, 'period': 
# {'number': 3}, 'clock': {'value': 250.0, 'displayValue': '4:10'}, 'team': {'id': '23', 'uid': 's:20~l:28~t:23', 'displayName': 'Pittsburgh Steelers', 
# 'abbreviation': 'PIT', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/pit/pittsburgh-steelers', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/pit', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266283215', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'Byron Pringle 2 Yd pass from Travis Kelce (Harrison Butker Kick)', 'awayScore': 14, 'homeScore': 42, 
# 'period': {'number': 4}, 'clock': {'value': 853.0, 'displayValue': '14:13'}, 'team': {'id': '12', 'uid': 's:20~l:28~t:12', 'displayName': 
# 'Kansas City Chiefs', 'abbreviation': 'KC', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/kc/kansas-city-chiefs', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/kc', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}, {'id': '4013266283664', 'type': {'id': '67', 'text': 
# 'Passing Touchdown', 'abbreviation': 'TD'}, 'text': 'James Washington 15 Yd pass from Ben Roethlisberger (Chris Boswell Kick)', 'awayScore': 21, 
# 'homeScore': 42, 'period': {'number': 4}, 'clock': {'value': 456.0, 'displayValue': '7:36'}, 'team': {'id': '23', 'uid': 's:20~l:28~t:23', 'displayName': 
# 'Pittsburgh Steelers', 'abbreviation': 'PIT', 'links': [{'href': 'https://www.espn.com/nfl/team/_/name/pit/pittsburgh-steelers', 'text': 'Clubhouse'}, 
# {'href': 'https://www.espn.com/nfl/team/schedule/_/name/pit', 'text': 'Schedule'}], 'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png'}, 
# 'scoringType': {'name': 'touchdown', 'displayName': 'Touchdown', 'abbreviation': 'TD'}}]







# dict_keys(['leagues', 'season', 'week', 'events'])

print(r['events'][0].keys())
# dict_keys(['id', 'uid', 'date', 'name', 'shortName', 'season', 'competitions', 'links', 'weather', 'status'])
print(r['events'][0]['id'])
print(r['events'][0]['date'])
print(r['events'][0]['name'])
print(r['events'][0]['shortName'])
print(r['events'][0]['status'])
# 401326627
# 2022-01-15T21:30Z
# Las Vegas Raiders at Cincinnati Bengals
# LV @ CIN
# {'clock': 0.0, 'displayClock': '0:00', 'period': 0, 'type': {'id': '1', 'name': 'STATUS_SCHEDULED', 
# 'state': 'pre', 'completed': False, 'description': 'Scheduled', 'detail': 'Sat, January 15th at 4:30 PM EST', 
# 'shortDetail': '1/15 - 4:30 PM EST'}}
# print(r['leagues'][0]['abbreviation'])
# print(r['season'])


# for event in r['events']:
#     print(f"espnid: {event['id']}")
#     print(f"date: {event['date']}")
#     print(f"date: {event['season']['year']}")
#     print(f"date: {event['name']}")
#     print(f"date: {event['shortName']}")
#     print(f"date: {event['status']['type']['detail']}")
#     print(f"date: {event['status']['type']['shortDetail']}")

#print(r['events'][0]['competitions'][0].keys())
# dict_keys(['id', 'uid', 'date', 'attendance', 'type', 'timeValid', 'neutralSite', 'conferenceCompetition', 
#            'recent', 'venue', 'competitors', 'notes', 'status', 'broadcasts', 'leaders', 'tickets', 
#            'startDate', 'geoBroadcasts', 'odds'])

# print(r['events'][0]['competitions'][0]['id'])
# print(r['events'][0]['competitions'][0]['type'])
# #print(r['events'][0]['competitions'][0]['competitors'])
# print(r['events'][0]['competitions'][0]['notes'])
# print(r['events'][0]['competitions'][0]['status'])
# print(r['events'][0]['competitions'][0]['startDate'])
# print(r['events'][0]['competitions'][0]['odds'])
# # 401326627
# # {'id': '1', 'abbreviation': 'STD'}
# # [{'type': 'event', 'headline': 'AFC Wild Card Playoffs'}]
# # {'clock': 0.0, 'displayClock': '0:00', 'period': 0, 'type': {'id': '1', 'name': 'STATUS_SCHEDULED', 
# # 'state': 'pre', 'completed': False, 'description': 'Scheduled', 'detail': 'Sat, January 15th at 4:30 PM EST', 
# # 'shortDetail': '1/15 - 4:30 PM EST'}}
# # 2022-01-15T21:30Z
# # [{'provider': {'id': '45', 'name': 'Caesars Sportsbook (New Jersey)', 'priority': 1}, 'details': 'CIN -6.0', 
# # 'overUnder': 49.0}]


# print(r['events'][0]['competitions'][0]['competitors'][0].keys())
# # dict_keys(['id', 'uid', 'type', 'order', 'homeAway', 'team', 'score', 'statistics', 'records', 'leaders'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['id'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['type'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['order'])
# print(r['events'][0]['competitions'][0]['competitors'][1]['order'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['homeAway'])
# print(r['events'][0]['competitions'][0]['competitors'][1]['homeAway'])
# #print(r['events'][0]['competitions'][0]['competitors'][0]['team'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['score'])
# # 4
# # team
# # 0
# # 1
# # home
# # away
# # 0

#print(r['events'][0]['competitions'][0]['competitors'][0]['team'].keys())
# dict_keys(['id', 'uid', 'location', 'name', 'abbreviation', 'displayName', 'shortDisplayName', 'color', 
#            'alternateColor', 'isActive', 'venue', 'links', 'logo'])

# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['name'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['abbreviation'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['displayName'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['shortDisplayName'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['color'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['alternateColor'])
# print(r['events'][0]['competitions'][0]['competitors'][0]['team']['logo'])
# # Bengals
# # CIN
# # Cincinnati Bengals
# # Bengals
# # FF2700
# # 000000
# # https://a.espncdn.com/i/teamlogos/nfl/500/scoreboard/cin.png


















# ---- CFP box testing below ----

# print(f"header:  {r['header'].keys()}")
# print(f"com {len(r['header']['competitions'])}")
# print(f"com {r['header']['competitions'][0].keys()}")
# # dict_keys(['id', 'uid', 'date', 'neutralSite', 'conferenceCompetition', 'boxscoreAvailable', 
# #             'commentaryAvailable', 'liveAvailable', 'onWatchESPN', 'recent', 'boxscoreSource', 
# #             'playByPlaySource', 'competitors', 'status', 'broadcasts', 'groups'])

# print(f"status {r['header']['competitions'][0]['status']}")
# # status {'type': {'id': '1', 'name': 'STATUS_SCHEDULED', 'state': 'pre', 'completed': False, 
# #         'description': 'Scheduled', 'detail': 'Mon, January 10th at 8:00 PM EST', 
# #         'shortDetail': '1/10 - 8:00 PM EST'}}

# kickoff = r['header']['competitions'][0]['status']['type']['detail']
# print(kickoff)

# now = datetime.utcnow()
# print(now)
# # curr_year = datetime.strftime(now).year
# # print(curr_year)

# dt = datetime.strptime(kickoff + ' ' + str(datetime.utcnow().year), '%a, %B %dth at %I:%M %p %Z %Y')
# delta = dt - now
# print(delta.days)
# sec = delta.seconds
# print(delta.seconds)

# print(sec/60)

# --------------------------------------------
# starttime = time.mktime((2021, 12, 17, 18, 59, 0, 0, 0, 0))
# season_type = 3
# week = 1
# event = 401331242   # 401331242 is CFP final     401331215
# league = 'ncaaf'
# espn_url_nfl = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event}"  # change to eventid eventually
# espn_url_ncaaf = f"http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={event}"

# if league == 'ncaaf':
#     response = requests.get(espn_url_ncaaf)
# else:
#     response = requests.get(espn_url_nfl)
# r = response.json()
# espn_dict = dict(r)
# print(espn_dict.keys())

# d = {}

# print("----------BOXSCORE------------")
# #print(f"boxscore keys:  {espn_dict['boxscore'].keys()}")
# print(f"boxscore teams: {espn_dict['boxscore']['teams']}")
# for teams in espn_dict['boxscore']['teams']:
#     for k, v in teams.items():
#         #print(f"{k}\n{v}")
#         #print(teams[k])
#         if k == 'team':
#             print(v['abbreviation'] + ' - ' + v['displayName'] + ' ' + v['name'])
#             print(v['logo'])
#             d[v['abbreviation']] = {'schoolName': v['displayName'], 'nickname': v['name'], 'logo': v['logo']}

# result of above:
# dheslin@DESKTOP-IF8M32H:~/bygtech/line_checker$ ./espn_tester.py
# UGA - Georgia Bulldogs
# ALA - Alabama Crimson Tide

# print("\n-----------GAMEINFO--------------")
# print(espn_dict['gameInfo'])

#print("\n------------HEADER----------")
# for competition in espn_dict['header']['competitions']:
#     #print(type(competition))
#     for competitor in competition['competitors']:
#         team = competitor['team']['abbreviation']
#         if 'score' in competitor:
#             #print(competitor['team']['abbreviation'], competitor['score'])
            
#             curr_score = competitor['score']
#             qtrs = {}
#             q = 1
#             for qtr in competitor['linescores']:
#                 #print(qtr['displayValue'])
#                 qtrs[q] = qtr['displayValue']
#                 q += 1
#             d[team]['current_score'] = curr_score
#             d[team]['qtr_scores'] = qtrs
#         else:
#             d[team]['current_score'] = 'n/a'
#             d[team]['qtr_scores'] = 'n/a'

# print(d)





#### ESPN API NOTES BELOW: ####
# dict_keys(['leagues', 'groups', 'season', 'week', 'events'])
# league 23 == NCAAF

# season
#   type:  1 preseason   2 regular   3 post
#   year:  year

# week
#   number:  1 (week number)

# events
#   dict_keys(['id', 'uid', 'date', 'name', 'shortName', 'season', 'competitions', 'links', 'status'])










#game_dict = get_games(r, False)['game']
#print(game_dict)
#print(r['events'][0]['competitions'][0]['notes'][0]['headline'])

# now = datetime.utcnow() - timedelta(hours=5)
# print(now)
# print('now again')
# for game in game_dict:
#     fav = ''
#     spread = 0
#     game_dict[game]['current_winner'] = ''
#     game_in_future = game_dict[game]['datetime'] > now  # if in future, will be true.
#     time_to_kickoff = game_dict[game]['datetime'] - now
#     # if (game_dict[game]['line'] != 'TBD' and now.day - last_db_update.day > 1) or insert_mode == True:
#     if game_dict[game]['line'] != 'TBD' and game_in_future and time_to_kickoff.total_seconds() > 3600:  # >1 hour to kickoff - record latest line
#         espnid = game_dict[game]['espn_id']
#         fav = game_dict[game]['line'][0]
#         if len(game_dict[game]['line']) > 1 and len(game_dict[game]['line'][1]) > 1:  # to handle 'EVEN' lines, will only be ['EVEN'] with len 1
#             if game_dict[game]['line'][1][-2:] == '.0':  # get rid of the -10.0 float to int.  only show float when it's a .5 spread
#                 game_dict[game]['line'][1] = game_dict[game]['line'][1][:-2]
#                 spread = game_dict[game]['line'][1]
#             else:
#                 spread = game_dict[game]['line'][1]
#         else:
#             spread = ''
#         line_query = "INSERT INTO latest_lines (espnid, fav, spread, datetime) VALUES (%s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE espnid = %s, fav = %s, spread = %s, datetime = NOW();"
#         #db2(line_query, (espnid, fav, spread, espnid, fav, spread))
#         logging.info(f"inserted new line: {espnid}: {fav}: {spread}: {now}")

 