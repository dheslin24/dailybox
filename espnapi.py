import requests
from datetime import datetime, timedelta
from db_accessor.db_accessor import db2

def get_espn_scores(abbrev = True, insert_mode = False):
    season_type = 3  # 1: preseason, 2: regular, 3: post
    week = 1 # will make this an input soon
    league = 'nfl'
    espn_url_hc = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=9"  # hard coded url
    espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type}&week={week}"
    #espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?seasontype={season_type}&week={week}&limit=900"

    #response = requests.get(espn_url)
    response = requests.get(espn_ncaa_url)
    r = response.json()

    game_dict = {}
    game_num = 1
    team_dict = {}
    now = datetime.utcnow() - timedelta(hours=5)
    print(now)

    # <<<<<<<<<TESTING>>>>>>>>
    # print(r.keys())
    # print(r['events'][0]['competitions'][0]['notes'][0]['headline'])
    # print(r['events'][0]['competitions'][0]['competitors'][0]['order'])
    # print(r)
    print("dh test")
    print(r['events'][0]['competitions'][0]['status'])
    # print(r['events'][0]['competitions'][0]['odds'][0]['details'])
    # print(r['events'][0]['competitions'][0]['odds'][0]['overUnder'])
    #print(f"events: {r['events']}")
    #print("##########################")
    #print(f"games: {r['events'][0]['competitions']}")
    # <<<<<<<<<END TESTING >>>>>>>>>>>>>>

    espn_q = "SELECT espnid, fav, spread FROM latest_lines"
    espn_db = db2(espn_q)
    print(f"espndb: {espn_db}")

    espn_dict = {}
    for game in espn_db:
        if len(game) == 3:
            espn_dict[str(game[0])] = {'fav': game[1], 'spread': game[2]}
        else:
            espn_dict[str(game[0])] = {'fav': game[1], 'spread': ''}

    print(f"espn dict: {espn_dict}")

    winloss_dict = {}

    for team in r['events']:
        for game in team['competitions']:
            competitors = []
            abbreviations = {}
            headline = ''
            status = {}
            if 'status' in game:
                print(f"status! {game['status']}")
                game_status = game['status']['type']['description']  # 1: scheduled, 2: inprogress, 3: final, 5: canceled
                if game_status == 'Scheduled':
                    status['status'] = game_status

                elif game_status == 'Canceled':
                    status['status'] = game_status
                    status['detail'] = game_status

                elif game_status != 'Final':
                    status['status'] = game['status']['type']['description']
                    status['detail'] = game['status']['type']['detail']
                    status['displayClock'] = game['status']['displayClock']
                    status['quarter'] = game['status']['period']
                else:
                    status['status'] = 'Final'
                
            if 'odds' in game:
                over_under = game['odds'][0]['overUnder']
                if over_under % 2 == 0:
                    over_under = int(over_under)
            else:
                # line = 'TBD'
                over_under = 'TBD'

            if game['id'] in espn_dict:
                if espn_dict[game['id']]['fav'] != 'EVEN':
                    espn_fav = espn_dict[game['id']]['fav']
                    espn_spread = espn_dict[game['id']]['spread']
                    if len(espn_spread) > 2 and espn_spread[-2:] == '.0':
                        espn_spread = espn_spread[:-2]
                    line = [espn_fav, espn_spread]
                else:
                    espn_fav = 'EVEN'
                    espn_spread = ''
                    line = [espn_fav]
            else:
                line = 'TBD'

            if line[0] != 'EVEN':
                print(f"line:  {line}  o/u: {over_under}  {type(line[1])}")
            else:
                print(f"line: EVEN EVEN {line}")
                #print(f"game with even {game}")
            if 'notes' in game:
                if len(game['notes']) > 0:
                    if 'headline' in game['notes'][0]:
                        headline = game['notes'][0]['headline']

            for team in game['competitors']:
                home_away = team['homeAway'].upper()
                if abbrev:
                    competitors.append((home_away, team['team']['abbreviation'], team['score']))
                else:
                    competitors.append((home_away, team['team']['displayName'] + ' ' + team['team']['name'], team['score']))
                    abbreviations[home_away] = team['team']['abbreviation']

                team_dict[team['team']['abbreviation']] = team['score']
                
            # convert string to datetime e.g.:  
            # 'date': '2022-01-01T17:00Z'
            game_datetime = datetime.strptime(game['date'], '%Y-%m-%dT%H:%MZ') - timedelta(hours=5)
            game_date = game_datetime.strftime('%Y-%m-%d %I:%M %p EST') 
            game_date_short = game_datetime.strftime('%m-%d %H:%M')


            game_dict[game_num] = {
                'espn_id': int(game['id']), 
                'date': game_date, # date string for printing
                'date_short': game_date_short,
                'datetime': game_datetime, # datetime object for comparison
                'venue': game['venue']['fullName'], 
                'competitors': competitors,
                'abbreviations': abbreviations,
                'line': line,
                'over_under': over_under,
                'headline': headline,
                'location': game['venue']['address']['city'] + ', ' + game['venue']['address']['state'],
                'status': status
                }
            game_num += 1
            
    # post processing of game_dict for winner/loser
    for game in game_dict:
        fav = ''
        dog = ''
        spread = 0
        fav_score = 0
        dog_score = 0
        game_dict[game]['current_winner'] = ''

        if game_dict[game]['datetime'] < now:
            #print(f"even check {game_dict[game]['line']}")
            if game_dict[game]['line'][0] == 'EVEN':
                fav = game_dict['abbreviations']['HOME']
                fav_score = team_dict[fav]
                dog = game_dict['abbreviations']['AWAY']
                dog_score = team_dict[dog]
            elif game_dict[game]['line'] != 'TBD':
                for team in game_dict[game]['abbreviations'].values():
                    print(f"team: {team}")
                    if team == game_dict[game]['line'][0]:
                        spread = game_dict[game]['line'][1]
                        fav = team
                        fav_score = int(team_dict[team]) + float(spread)
                    else:
                        dog_score = float(team_dict[team])
                        dog = team
            # if fav_score != 0 or dog_score != 0:
            print(f"favdogscores 1 {fav} 2 {dog} 3 {fav_score} 4 {dog_score}")
            if fav_score > dog_score:
                game_dict[game]['current_winner'] = fav
            elif dog_score > fav_score:
                game_dict[game]['current_winner'] = dog
            else:
                game_dict[game]['current_winner'] = 'PUSH'
            print(f"curr winner {game_dict[game]['current_winner']}")
            # else:
    #print(f"GAME DICT {game_dict}")
                
    #return (game_dict, team_dict)
    return {"game": game_dict, "team": team_dict}