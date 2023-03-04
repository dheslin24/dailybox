import requests
from datetime import datetime, timedelta
from db_accessor.db_accessor import db2

def get_ncaab_games():
    espn_ncaab_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230302"

    response = requests.get(espn_ncaab_url).json()

    return response

def get_espn_ids(season_type = 3, week = 1, league='ncaaf'):
    espn_nfl_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type}&week={week}"
    espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?seasontype={season_type}&week={week}&limit=900"

    if league == 'ncaaf':
        response = requests.get(espn_ncaa_url)
    else:
        response = requests.get(espn_nfl_url)

    r = response.json()

    return r

def get_espn_scores(abbrev = True, season_type = 3, week = 5, league='nfl', espnid=False):
    # season_type = 3  # 1: preseason, 2: regular, 3: post
    # week = 1 # will make this an input soon
    espn_url_hc = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=9"  # hard coded url
    espn_nfl_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype={season_type}&week={week}"
    #espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    espn_ncaa_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?seasontype={season_type}&week={week}&limit=900"

    #response = requests.get(espn_url)

    if league == 'ncaaf':
        response = requests.get(espn_ncaa_url)
    else:
        response = requests.get(espn_nfl_url)

    r = response.json()

    game_dict = {}
    #game_num = 1
    team_dict = {}
    now = datetime.utcnow() - timedelta(hours=5)
    print(now)

    espn_q = f"SELECT espnid, fav, spread FROM latest_lines WHERE league = '{league}'"
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

    for event in r['events']:
        for game in event['competitions']:
            espnid = int(game['id'])
            competitors = []
            abbreviations = {}
            headline = ''
            status = {}
            if 'status' in game:
                print(f"status! {game['status']}")
                game_status = game['status']['type']['description']  # 1: scheduled, 2: inprogress, 3: final, 5: canceled
                if game_status == 'Scheduled':
                    status['status'] = game_status

                elif game_status == 'Canceled' or game_status == 'Postponed':
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
                    competitors.append((home_away, team['team']['displayName'], team['score']))
                    abbreviations[home_away] = team['team']['abbreviation']

                team_dict[team['team']['abbreviation']] = team['score']
                
            # convert string to datetime e.g.:  
            # 'date': '2022-01-01T17:00Z'
            game_datetime = datetime.strptime(game['date'], '%Y-%m-%dT%H:%MZ') - timedelta(hours=5)
            game_date = game_datetime.strftime('%Y-%m-%d %I:%M %p EST') 
            game_date_short = game_datetime.strftime('%m-%d %H:%M')

            if 'venue' in game:
                venue = game['venue']['fullName']
                location = game['venue']['address']['city'] + ', ' + game['venue']['address']['state']
            else:
                venue = 'TBD'
                location = 'TBD'

            if headline[-8:] == 'Playoffs':
                headline = headline[:-8]

            game_dict[espnid] = {
                'espn_id': int(game['id']), 
                'date': game_date, # date string for printing
                'date_short': game_date_short,
                'datetime': game_datetime, # datetime object for comparison
                'venue': venue, 
                'competitors': competitors,  # list of competitors [(home/away, team, score), ... ]
                'abbreviations': abbreviations,  # {'HOME': abbrev, 'AWAY', abbrev}
                'line': line,
                'over_under': over_under,
                'headline': headline,
                'location': location,
                'status': status
                }
            #game_num += 1
            
    # post processing of game_dict for winner/loser
    for game in game_dict:
        fav = ''
        dog = ''
        spread = 0
        fav_score = 0
        dog_score = 0
        game_dict[game]['current_winner'] = ''

        if game_dict[game]['datetime'] < now:
            #print(f"even check {game_dict[game]['line']}"
            if game_dict[game]['line'][0] == 'EVEN':
                print(f"gamedict in espnapi ###################################### {game_dict[game]['abbreviations']}")
                fav = game_dict[game]['abbreviations']['HOME']
                fav_score = team_dict[fav]
                dog = game_dict[game]['abbreviations']['AWAY']
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


def get_espn_score_by_qtr(eventid, league='nfl'):
    # season_type = 3
    # week = 1
    event = 401331242   # 401331242 is CFP final
    print(eventid)
    espn_url_nfl = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={eventid}"  # change to eventid eventually
    espn_url_ncaaf = f"http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={eventid}"

    if league == 'ncaaf':
        response = requests.get(espn_url_ncaaf)
    else:
        response = requests.get(espn_url_nfl)
    print(response)
    r = response.json()
    espn_dict = dict(r)
    print(espn_dict.keys())

    d = {}

    print("----------BOXSCORE------------")
    # print(f"boxscore keys:  {espn_dict['boxscore'].keys()}")
    # print(f"boxscore teams: {espn_dict['boxscore']['teams']}")
    for teams in espn_dict['boxscore']['teams']:
        for k, v in teams.items():
            #print(f"{k}\n{v}")
            #print(teams[k])
            if k == 'team':
                print(v['abbreviation'] + ' - ' + v['displayName'] + ' ' + v['name'])
                if 'logo' in v:
                    print(v['logo'])
                else:
                    v['logo'] = ''
                d[v['abbreviation']] = {'schoolName': v['displayName'], 'nickname': v['name'], 'logo': v['logo']}

    # result of above:
    # dheslin@DESKTOP-IF8M32H:~/bygtech/line_checker$ ./espn_tester.py
    # UGA - Georgia Bulldogs
    # ALA - Alabama Crimson Tide

    print("\n-----------GAMEINFO--------------")
    print(espn_dict['gameInfo'])

    print("\n------------HEADER----------")
    print(f"header: {espn_dict['header']}")
    for competition in espn_dict['header']['competitions']:
        print(type(competition))
        for competitor in competition['competitors']:
            print(f"competitor!!!:  {competitor}")
            team = competitor['team']['abbreviation']
            if 'score' in competitor:
                #print(competitor['team']['abbreviation'], competitor['score'])
                
                curr_score = competitor['score']
                qtrs = {}
                q = 1
                for qtr in competitor['linescores']:
                    #print(qtr['displayValue'])
                    qtrs[q] = qtr['displayValue']
                    q += 1
                d[team]['current_score'] = curr_score
                d[team]['qtr_scores'] = qtrs
            else:
                qtrs = {}
                d[team]['current_score'] = '0'
                d[team]['qtr_scores'] = qtrs
    
    return d


def get_espn_summary_single_game(espnid, league='nfl'):
    if league == 'ncaaf':
        espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={espnid}"
    elif league == 'nfl':
        espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={espnid}"
    else:
        espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={espnid}"


    r = requests.get(espn_url).json()

    game_status = r['header']['competitions'][0]['status']

    clock = ''
    quarter = 0

    if 'displayClock' in game_status:
        clock = game_status['displayClock']

    if 'period' in game_status:
        quarter = game_status['period']

    response = {
        'game_status': game_status['type']['description'],
        'kickoff_time': game_status['type']['detail'],
        'game_clock': clock,
        'quarter': quarter
    }

    return response
    
    

