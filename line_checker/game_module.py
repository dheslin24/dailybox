import time
from datetime import datetime, timedelta, date

def get_games(espn_data, abbrev=True):
    r = espn_data
    game_dict = {}
    game_num = 1
    team_dict = {}
    
    for team in r['events']:
        for game in team['competitions']:
            competitors = []
            abbreviations = {}
            headline = ''
            if 'odds' in game:
                #print(f"len odds: {len(game['odds'])}")
                line = game['odds'][0]['details'].split(' ')

                # get rid of the -10.0 float to int.  only show float when it's a .5 spread
                print(f"line line {line}")
                if line != 'TBD' and line[0] != 'EVEN':
                    if line[1][-2:] == '.0':
                        line[1] = line[1][:-2]
                over_under = game['odds'][0]['overUnder']
                if over_under % 2 == 0:
                    over_under = int(over_under)
            else:
                line = 'TBD'
                over_under = 'TBD'

            if line[0] != 'EVEN':
                print(f"line:  {line}  o/u: {over_under}  {type(line[1])}")
            else:
                print(f"line: EVEN EVEN {game} with {line}")
            if 'notes' in game:
                if len(game['notes']) > 0:
                    if 'headline' in game['notes'][0]:
                        headline = game['notes'][0]['headline']

            for team in game['competitors']:
                #print(f"team:  {team['team']['displayName']}")
                #print("\br \br ################ \br \br")
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

            # if game_num == 1:
            #     line = ['TOL', '-10.5']

            game_dict[game_num] = {
                'espn_id': int(game['id']), 
                'date': game_date, # date string for printing
                'datetime': game_datetime, # datetime object for comparison
                'venue': game['venue']['fullName'], 
                'competitors': competitors,  # (home/away, team name, team score)
                'abbreviations': abbreviations,
                'line': line,
                'over_under': over_under,
                'headline': headline,
                'location': game['venue']['address']['city'] + ', ' + game['venue']['address']['state']
                }
            game_num += 1
    return {'game': game_dict, 'team': team_dict}