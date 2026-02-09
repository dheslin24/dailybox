import requests
from datetime import datetime, timedelta
# from db_accessor.db_accessor import db2
import json
from pprint import pprint

'''
example espn api scoringPlays response below:

{'awayScore': 0,
 'clock': {'displayValue': '8:25', 'value': 505.0},
 'homeScore': 3,
 'id': '401547757463',
 'period': {'number': 1},
 'scoringType': {'abbreviation': 'FG',
                 'displayName': 'Field Goal',
                 'name': 'field-goal'},
 'team': {'abbreviation': 'DET',
          'displayName': 'Detroit Lions',
          'id': '8',
          'links': [{'href': 'https://www.espn.com/nfl/team/_/name/det/detroit-lions',
                     'text': 'Clubhouse'},
                    {'href': 'https://www.espn.com/nfl/team/schedule/_/name/det',
                     'text': 'Schedule'}],
          'logo': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
          'logos': [{'alt': '',
                     'height': 500,
                     'href': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
                     'lastUpdated': '2018-06-05T12:11Z',
                     'rel': ['full', 'default'],
                     'width': 500},
                    {'alt': '',
                     'height': 500,
                     'href': 'https://a.espncdn.com/i/teamlogos/nfl/500-dark/det.png',
                     'lastUpdated': '2018-06-05T12:11Z',
                     'rel': ['full', 'dark'],
                     'width': 500},
                    {'alt': '',
                     'height': 500,
                     'href': 'https://a.espncdn.com/i/teamlogos/nfl/500/scoreboard/det.png',
                     'lastUpdated': '2018-06-05T12:11Z',
                     'rel': ['full', 'scoreboard'],
                     'width': 500},
                    {'alt': '',
                     'height': 500,
                     'href': 'https://a.espncdn.com/i/teamlogos/nfl/500-dark/scoreboard/det.png',
                     'lastUpdated': '2018-06-05T12:11Z',
                     'rel': ['full', 'scoreboard', 'dark'],
                     'width': 500}],
          'uid': 's:20~l:28~t:8'},
 'text': 'Michael Badgley Made 23 Yd Field Goal',
 'type': {'abbreviation': 'FG', 'id': '59', 'text': 'Field Goal Good'}}
'''

def _find_game_second(qtr: int, clock: int):
    elapsed_seconds_in_qtr = 900 - clock
    game_second = elapsed_seconds_in_qtr + ((qtr - 1) * 900)

    return game_second

def get_espn_every_min_scores(espnid):
    espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={espnid}"

    r = requests.get(espn_url)

    response = r.json()

    scores = []

    game_status = response.get('header', {}).get('competitions', [])[0].get('status', {}).get('type', {}).get("name")
    print(f"GAME STATUS {game_status}")

    if game_status not in ["STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_END_PERIOD", "STATUS_HALFTIME"]:
        return None


    current_clock = response.get('header', {}).get('competitions', [])[0].get('status', {}).get('displayClock')
    print(f"DH curr clock {current_clock}")
    current_qtr = response.get('header', {}).get('competitions', [])[0].get('status', {}).get('period')
    print(f"DH curr qtr {current_qtr}")
    if current_clock:
        current_min, current_second = current_clock.split(":")
        current_game_second = ((int(current_qtr) - 1) * 900) + (900 - (int(current_min) * 60) + (int(current_second)))

    for play in response.get('scoringPlays', {}):
        
        scoring_play = {
            "scoring_id" : play.get("id"),
            "away_score" : play.get("awayScore"),
            "home_score" : play.get("homeScore"),
            "clock_display" : play.get("clock", {}).get("displayValue"),
            "clock_value" : play.get("clock", {}).get("value"),
            "quarter" : play.get("period", {}).get("number"),
            "scoring_team" : play.get("team", {}).get("abbreviation"),
        }

        print(f"DH QUARTER {scoring_play['quarter']}")
            
        if current_qtr != 5 or current_qtr != "5":
            scores.append(scoring_play)

    if game_status == "STATUS_FINAL":
        last_scoring_play = scoring_play

    winners = []
    last_score_second = 0
    next_winner = {"away_score": 0, "home_score": 0}
    total_winning_minutes = 0

    # for OT - don't do any more than 60 scores
    i = 0
    score = None
    for idx, score in enumerate(scores):
        # print(f"DH SCORE {score}")
        game_second = _find_game_second(int(score["quarter"]), int(score["clock_value"]))
        winning_minutes = (game_second - last_score_second) // 60
        if last_score_second == 0:
            winning_minutes += 1 # start of game, 0/0 won the 0th minute
        total_winning_minutes += winning_minutes
        if total_winning_minutes < 60:
            last_score_second = game_second - (game_second % 60)  # round down to last minute
            winner = {
                "away_score": next_winner["away_score"],
                "home_score": next_winner["home_score"],
                "winning_minutes": winning_minutes,
                "type": "minute"
            }
            next_winner = {
                "away_score": score.get("away_score"),
                "home_score": score.get("home_score"),
            }
            winners.append(winner)
        
            

        if score:
            print(f"game second: {game_second}  last_score second: {last_score_second}  clock: {score['clock_display']}  qtr {score['quarter']}")
            print(f"{i}: {winner}\n")
        i += 1

    if score and game_status in ["STATUS_IN_PROGRESS", "STATUS_END_PERIOD", "STATUS_HALFTIME"]:
        # get current game time
        # calc current minutes won so far
        winning_minutes = (current_game_second - last_score_second) // 60
        winner = {
            "away_score": score.get("away_score"),
            "home_score": score.get("home_score"),
            "winning_minutes": winning_minutes,
            "type": "minute"
        }

        winners.append(winner)
        
        total_winning_minutes += winning_minutes
        print(f"game second: {current_game_second}  last_score second: {last_score_second}  clock: IN PROG WINNER")
        print(f"{i}: {winner}\n")

    elif not score and game_status in ["STATUS_IN_PROGRESS", "STATUS_END_PERIOD", "STATUS_HALFTIME"]:
        # get current game time
        # calc current minutes won so far
        winning_minutes = (current_game_second - last_score_second) // 60
        winner = {
            "away_score": 0,
            "home_score": 0,
            "winning_minutes": winning_minutes,
            "type": "minute"
        }

        winners.append(winner)

        total_winning_minutes += winning_minutes
        print(f"game second: {current_game_second}  last_score second: {last_score_second}  clock: IN PROG WINNER")
        print(f"{i}: {winner}\n")

    elif game_status == "STATUS_FINAL" and last_score_second < 3540:
        winning_minutes = (3540 - last_score_second) // 60
        winner = {
            "away_score": next_winner["away_score"],
            "home_score": next_winner["home_score"],
            "winning_minutes": winning_minutes,
            "type": "minute"
        }

        reverse_winner = {
            # "away_score": next_winner["home_score"],  # reversed away/home number
            # "home_score": next_winner["away_score"],
            "away_score": "29",  # reversed away/home number
            "home_score": "13",
            "winning_minutes": None,
            "type": "reverse"
        }

        final_winner = {
            # "away_score": next_winner["away_score"],
            # "home_score": next_winner["home_score"],
            "away_score": 29,
            "home_score": 13,
            "winning_minutes": None,
            "type": "final"
        }

        winners.extend([winner, reverse_winner, final_winner])
        
        total_winning_minutes += winning_minutes
        print(f"game second: 3540  last_score second: {last_score_second}  clock: FINAL")
        print(f"{i}: {winner}\n")

    elif game_status == "STATUS_FINAL" and last_score_second >= 3540: # we in OT
        print(f"DH IN OT {last_score_second}")
        winning_minutes = 0
        ot_final_winner = {
            "away_score": last_scoring_play["away_score"],
            "home_score": last_scoring_play["home_score"],
            "winning_minutes": winning_minutes,
            "type": "OT FINAL"
        }
        ot_reverse_winner = {
            "away_score": last_scoring_play["home_score"],  # reversed away/home number
            "home_score": last_scoring_play["away_score"],
            "winning_minutes": None,
            "type": "OT FINAL REVERSE"
        }
        winners.extend([winner, ot_reverse_winner, ot_final_winner])

    # print(winners)
    print(f"Total winning minutes: {total_winning_minutes}")

    return winners

# get_espn_every_min_scores(401547757) #det/tb
# get_espn_every_min_scores(401547758)  #kc/buf
# get_espn_every_min_scores(401547379)  #kc/bal
# get_espn_every_min_scores(401547380) # det/sf
# get_espn_every_min_scores(401547378) # superbowl