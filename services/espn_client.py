import logging
import requests
from datetime import datetime, timedelta, timezone
from db_accessor.db_accessor import db2

_BASE = "https://site.api.espn.com/apis/site/v2/sports/football"


def _espn_url(league, endpoint, **params):
    sport = 'nfl' if league == 'nfl' else 'college-football'
    url = f"{_BASE}/{sport}/{endpoint}"
    if params:
        url += '?' + '&'.join(f"{k}={v}" for k, v in params.items())
    return url


def get_ncaab_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20230302"
    return requests.get(url).json()


def get_espn_ids(season_type=3, week=1, league='ncaaf'):
    if league == 'ncaaf':
        url = _espn_url('ncaaf', 'scoreboard', seasontype=season_type, week=week, limit=900)
    else:
        url = _espn_url('nfl', 'scoreboard', seasontype=season_type, week=week)
    return requests.get(url).json()


def get_all_games_for_week(season_type=3, week=1, league='nfl', season=2025):
    url = f"{_BASE}/{league}/scoreboard?seasontype={season_type}&week={week}&dates={season}"
    r = requests.get(url).json()

    events = []
    for event in r.get('events', []):
        for comp in event.get('competitions', []):
            home_team = home_logo = away_team = away_logo = winner_team = None
            for c in comp.get('competitors', []):
                if c.get('homeAway') == 'home':
                    home_team = c['team']['abbreviation']
                    home_logo = c['team'].get('logo') or c['team'].get('logos', [{}])[0].get('href')
                elif c.get('homeAway') == 'away':
                    away_team = c['team']['abbreviation']
                    away_logo = c['team'].get('logo') or c['team'].get('logos', [{}])[0].get('href')
                if c.get('winner'):
                    winner_team = c['team']['abbreviation']
            odds = comp.get('odds', [{}])[0]
            events.append({
                'id': comp.get('id'),
                'home_team': home_team,
                'home_logo': home_logo,
                'away_team': away_team,
                'away_logo': away_logo,
                'start_date': comp.get('startDate'),
                'odds_details': odds.get('details'),
                'odds_spread': odds.get('spread'),
                'winner_team': winner_team,
            })
    return events


def get_espn_scores(abbrev=True, season_type=3, week=5, league='nfl', espnid=False):
    """Return {'game': {espnid: {...}}, 'team': {abbr: score}}."""
    if league == 'ncaaf':
        url = _espn_url('ncaaf', 'scoreboard', seasontype=season_type, week=week, limit=900)
    else:
        url = _espn_url('nfl', 'scoreboard', seasontype=season_type, week=week)

    r = requests.get(url).json()

    game_dict = {}
    team_dict = {}
    now = datetime.utcnow() - timedelta(hours=5)
    logging.info("now: %s", now)

    espn_db = db2(f"SELECT espnid, fav, spread FROM latest_lines WHERE league = '{league}'")
    espn_dict = {}
    for row in espn_db:
        espn_dict[str(row[0])] = {'fav': row[1], 'spread': row[2] if len(row) == 3 else ''}

    for event in r.get('events', []):
        for game in event.get('competitions', []):
            eid = int(game['id'])
            competitors = []
            abbreviations = {}
            headline = ''
            status = {}

            if 'status' in game:
                game_status = game['status']['type']['description']
                if game_status == 'Scheduled':
                    status['status'] = game_status
                elif game_status in ('Canceled', 'Postponed'):
                    status['status'] = game_status
                    status['detail'] = game_status
                elif game_status != 'Final':
                    status['status'] = game_status
                    status['detail'] = game['status']['type'].get('detail')
                    status['displayClock'] = game['status'].get('displayClock')
                    status['quarter'] = game['status'].get('period')
                else:
                    status['status'] = 'Final'

            if 'odds' in game and game['odds']:
                over_under = game['odds'][0].get('overUnder')
                try:
                    if isinstance(over_under, (int, float)) and over_under % 2 == 0:
                        over_under = int(over_under)
                except Exception:
                    pass
            else:
                over_under = 'TBD'

            if game['id'] in espn_dict:
                if espn_dict[game['id']]['fav'] != 'EVEN':
                    espn_fav = espn_dict[game['id']]['fav']
                    espn_spread = espn_dict[game['id']]['spread']
                    if isinstance(espn_spread, str) and len(espn_spread) > 2 and espn_spread.endswith('.0'):
                        espn_spread = espn_spread[:-2]
                    line = [espn_fav, espn_spread]
                else:
                    line = ['EVEN']
            else:
                line = 'TBD'

            if 'notes' in game and game['notes']:
                if 'headline' in game['notes'][0]:
                    headline = game['notes'][0]['headline']

            for team in game.get('competitors', []):
                home_away = team.get('homeAway', '').upper()
                if abbrev:
                    competitors.append((home_away, team['team'].get('abbreviation'), team.get('score')))
                else:
                    competitors.append((home_away, team['team'].get('displayName'), team.get('score')))
                    abbreviations[home_away] = team['team'].get('abbreviation')
                team_dict[team['team'].get('abbreviation')] = team.get('score')

            try:
                game_datetime = datetime.strptime(game['date'], '%Y-%m-%dT%H:%MZ') - timedelta(hours=5)
            except Exception:
                game_datetime = now
            game_date = game_datetime.strftime('%Y-%m-%d %I:%M %p EST')
            game_date_short = game_datetime.strftime('%m-%d %H:%M')

            if 'venue' in game:
                venue = game['venue'].get('fullName', 'TBD')
                location = (game['venue'].get('address', {}).get('city', 'TBD') + ', ' +
                            game['venue'].get('address', {}).get('state', 'TBD'))
            else:
                venue = 'TBD'
                location = 'TBD'

            if isinstance(headline, str) and headline.endswith('Playoffs'):
                headline = headline[:-8]

            game_dict[eid] = {
                'espn_id': eid,
                'date': game_date,
                'date_short': game_date_short,
                'datetime': game_datetime,
                'venue': venue,
                'competitors': competitors,
                'abbreviations': abbreviations,
                'line': line,
                'over_under': over_under,
                'headline': headline,
                'location': location,
                'status': status,
            }

    for game in game_dict:
        fav = dog = ''
        fav_score = dog_score = 0
        game_dict[game]['current_winner'] = ''

        if game_dict[game]['datetime'] < now:
            if isinstance(game_dict[game]['line'], list) and game_dict[game]['line'][0] == 'EVEN':
                fav = game_dict[game]['abbreviations'].get('HOME')
                fav_score = int(team_dict.get(fav) or 0)
                dog = game_dict[game]['abbreviations'].get('AWAY')
                dog_score = int(team_dict.get(dog) or 0)
            elif game_dict[game]['line'] != 'TBD' and isinstance(game_dict[game]['line'], list):
                for team in game_dict[game]['abbreviations'].values():
                    if team == game_dict[game]['line'][0]:
                        fav = team
                        fav_score = int(team_dict.get(team) or 0) + float(game_dict[game]['line'][1])
                    else:
                        dog = team
                        dog_score = float(team_dict.get(team) or 0)

            if fav_score > dog_score:
                game_dict[game]['current_winner'] = fav
            elif dog_score > fav_score:
                game_dict[game]['current_winner'] = dog
            else:
                game_dict[game]['current_winner'] = 'PUSH'
            logging.info('curr winner %s', game_dict[game]['current_winner'])

    return {"game": game_dict, "team": team_dict}


def get_espn_score_by_qtr(eventid, league='nfl'):
    logging.info('eventid: %s', eventid)
    if league == 'ncaaf':
        url = _espn_url('ncaaf', f'summary?event={eventid}')
    else:
        url = _espn_url('nfl', f'summary?event={eventid}')

    r = requests.get(url).json()
    logging.info('espn summary keys: %s', list(r.keys()))

    d = {}
    logging.info('----------BOXSCORE------------')
    for teams in r.get('boxscore', {}).get('teams', []):
        for k, v in teams.items():
            if k == 'team':
                logging.info('%s - %s %s', v.get('abbreviation'), v.get('displayName'), v.get('name'))
                v.setdefault('logo', '')
                d[v.get('abbreviation')] = {
                    'schoolName': v.get('displayName'),
                    'nickname': v.get('name'),
                    'logo': v.get('logo'),
                }

    for competition in r.get('header', {}).get('competitions', []):
        for competitor in competition.get('competitors', []):
            team = competitor.get('team', {}).get('abbreviation')
            if 'score' in competitor:
                qtrs = {}
                for q, qtr in enumerate(competitor.get('linescores', []), start=1):
                    qtrs[q] = qtr.get('displayValue')
                d[team]['current_score'] = competitor.get('score')
                d[team]['qtr_scores'] = qtrs
            else:
                d.setdefault(team, {})
                d[team]['current_score'] = '0'
                d[team]['qtr_scores'] = {}

    return d


def get_espn_summary_single_game(espnid, league='nfl'):
    if league == 'ncaaf':
        url = _espn_url('ncaaf', f'summary?event={espnid}')
    else:
        url = _espn_url('nfl', f'summary?event={espnid}')

    r = requests.get(url).json()
    game_status = r['header']['competitions'][0]['status']

    return {
        'game_status': game_status['type']['description'],
        'kickoff_time': game_status['type']['detail'],
        'game_clock': game_status.get('displayClock', ''),
        'quarter': game_status.get('period', 0),
    }


def _find_game_second(qtr: int, clock: int) -> int:
    return (900 - clock) + ((qtr - 1) * 900)


def get_espn_every_min_scores(espnid):
    url = _espn_url('nfl', f'summary?event={espnid}')
    response = requests.get(url).json()

    header_comp = response.get('header', {}).get('competitions', [{}])[0]
    game_status = header_comp.get('status', {}).get('type', {}).get('name')
    logging.info('GAME STATUS %s', game_status)

    active = {"STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_END_PERIOD", "STATUS_HALFTIME"}
    if game_status not in active:
        return None

    current_clock = header_comp.get('status', {}).get('displayClock')
    current_qtr = header_comp.get('status', {}).get('period')
    current_game_second = None
    if current_clock:
        current_min, current_sec = current_clock.split(":")
        current_game_second = ((int(current_qtr) - 1) * 900) + (900 - (int(current_min) * 60) + int(current_sec))

    scores = []
    for play in response.get('scoringPlays', []):
        if current_qtr != 5 and current_qtr != "5":
            scores.append({
                "scoring_id": play.get("id"),
                "away_score": play.get("awayScore"),
                "home_score": play.get("homeScore"),
                "clock_display": play.get("clock", {}).get("displayValue"),
                "clock_value": play.get("clock", {}).get("value"),
                "quarter": play.get("period", {}).get("number"),
                "scoring_team": play.get("team", {}).get("abbreviation"),
            })

    winners = []
    last_score_second = 0
    next_winner = {"away_score": 0, "home_score": 0}
    total_winning_minutes = 0
    score = None
    last_scoring_play = None

    for score in scores:
        game_second = _find_game_second(int(score["quarter"]), int(score["clock_value"]))
        winning_minutes = (game_second - last_score_second) // 60
        if last_score_second == 0:
            winning_minutes += 1
        total_winning_minutes += winning_minutes
        if total_winning_minutes < 60:
            last_score_second = game_second - (game_second % 60)
            winner = {
                "away_score": next_winner["away_score"],
                "home_score": next_winner["home_score"],
                "winning_minutes": winning_minutes,
                "type": "minute",
            }
            next_winner = {"away_score": score.get("away_score"), "home_score": score.get("home_score")}
            winners.append(winner)
        last_scoring_play = score

    if game_status == "STATUS_FINAL":
        logging.info('Total winning minutes: %s', total_winning_minutes)

    in_progress = game_status in {"STATUS_IN_PROGRESS", "STATUS_END_PERIOD", "STATUS_HALFTIME"}

    if score and in_progress:
        winning_minutes = (current_game_second - last_score_second) // 60
        winners.append({
            "away_score": score.get("away_score"),
            "home_score": score.get("home_score"),
            "winning_minutes": winning_minutes,
            "type": "minute",
        })
        total_winning_minutes += winning_minutes

    elif not score and in_progress:
        winning_minutes = (current_game_second - last_score_second) // 60
        winners.append({"away_score": 0, "home_score": 0, "winning_minutes": winning_minutes, "type": "minute"})
        total_winning_minutes += winning_minutes

    elif game_status == "STATUS_FINAL" and last_score_second < 3540:
        winning_minutes = (3540 - last_score_second) // 60
        winners.append({
            "away_score": next_winner["away_score"],
            "home_score": next_winner["home_score"],
            "winning_minutes": winning_minutes,
            "type": "minute",
        })
        winners.append({
            "away_score": next_winner["home_score"],
            "home_score": next_winner["away_score"],
            "winning_minutes": None,
            "type": "reverse",
        })
        winners.append({
            "away_score": next_winner["away_score"],
            "home_score": next_winner["home_score"],
            "winning_minutes": None,
            "type": "final",
        })
        total_winning_minutes += winning_minutes

    elif game_status == "STATUS_FINAL" and last_score_second >= 3540 and last_scoring_play:
        logging.info('OT final %s', last_score_second)
        winners.extend([
            {
                "away_score": last_scoring_play["away_score"],
                "home_score": last_scoring_play["home_score"],
                "winning_minutes": 0,
                "type": "OT FINAL",
            },
            {
                "away_score": last_scoring_play["home_score"],
                "home_score": last_scoring_play["away_score"],
                "winning_minutes": None,
                "type": "OT FINAL REVERSE",
            },
        ])

    logging.info('Total winning minutes: %s', total_winning_minutes)
    return winners
