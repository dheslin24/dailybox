import logging
import re
import time
import requests
from datetime import datetime, timedelta, timezone, date
from db_accessor.db_accessor import db2

# Simple in-memory TTL cache: key → (value, expires_at)
_cache: dict = {}

def _cache_get(key):
    entry = _cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None

def _cache_set(key, value, ttl):
    _cache[key] = (value, time.time() + ttl)

_BASE = "https://site.api.espn.com/apis/site/v2/sports/football"
_GOLF_BASE = "https://site.api.espn.com/apis/site/v2/sports/golf/pga"


def get_golf_tournaments():
    """Fetch the next 5 upcoming PGA Tour events from ESPN (6-month lookahead)."""
    from datetime import date, timedelta
    today = date.today()
    end   = today + timedelta(days=180)
    date_range = f"{today.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    try:
        r = requests.get(f"{_GOLF_BASE}/scoreboard?dates={date_range}&limit=20", timeout=10).json()
        events = []
        for event in r.get('events', []):
            comps = event.get('competitions', [])

            def _extract_venue(obj):
                name = obj.get('fullName', '') or obj.get('name', '')
                if name:
                    return name
                city  = obj.get('address', {}).get('city', '')
                state = obj.get('address', {}).get('state', '')
                return f"{city}, {state}".strip(', ')

            venue = ''
            # top-level event.venue (common for golf scoreboard)
            if not venue and event.get('venue'):
                venue = _extract_venue(event['venue'])
            # competitions[0].venue
            if not venue and comps and comps[0].get('venue'):
                venue = _extract_venue(comps[0]['venue'])
            # top-level location string
            if not venue:
                venue = event.get('location', '')
            logging.debug("golf event %s venue=%r", event.get('id'), venue)
            status_obj  = event.get('status', {}).get('type', {})
            status_name = status_obj.get('name', '')
            events.append({
                'espn_event_id': event['id'],
                'name':        event.get('name', ''),
                'start_date':  (event.get('date')    or '')[:10],
                'end_date':    (event.get('endDate') or '')[:10],
                'status_name': status_name,
                'status_desc': status_obj.get('description', 'Scheduled'),
                'venue':       venue,
            })

        # Prefer upcoming/in-progress over completed; return at most 5
        completed = {'STATUS_FINAL', 'STATUS_COMPLETE', 'STATUS_END_TOURNAMENT'}
        upcoming  = [e for e in events if e['status_name'] not in completed]
        return (upcoming if upcoming else events)[:5]
    except Exception as e:
        logging.error("get_golf_tournaments error: %s", e)
        return []


def get_golf_event_venue(espn_event_id):
    """Fetch course name for a PGA event via ESPN core API."""
    try:
        url = (f"https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"
               f"/events/{espn_event_id}?lang=en&region=us")
        r = requests.get(url, timeout=10).json()
        courses = r.get('courses', [])
        if courses:
            c = courses[0]
            name = c.get('name', '')
            if name:
                return name
            city  = c.get('address', {}).get('city', '')
            state = c.get('address', {}).get('state', '')
            return f"{city}, {state}".strip(', ')
        return ''
    except Exception as e:
        logging.error("get_golf_event_venue(%s) error: %s", espn_event_id, e)
        return ''


def get_golf_world_rankings():
    """Return {espn_athlete_id_str: world_rank_int} from ESPN's OWGR data.
    Tries the most recent weekly ranking date (searches back up to 10 days)."""
    cached = _cache_get('golf_world_rankings')
    if cached is not None:
        return cached
    today = date.today()
    for delta in range(4):
        d = today - timedelta(days=delta)
        url = (f"https://sports.core.api.espn.com/v2/sports/golf/leagues/all"
               f"/seasons/{d.year}/rankings/1/dates/{d.strftime('%Y%m%d')}"
               f"?lang=en&region=us&limit=300")
        try:
            ranks = requests.get(url, timeout=4).json().get('ranks', [])
            if not ranks:
                continue
            rank_map = {}
            for item in ranks:
                ref = item.get('athlete', {}).get('$ref', '')
                m = re.search(r'/athletes/(\d+)', ref)
                if m:
                    rank_map[m.group(1)] = item.get('current')
            logging.info("Loaded %d world golf rankings for %s", len(rank_map), d)
            _cache_set('golf_world_rankings', rank_map, 86400)  # 24h
            return rank_map
        except Exception as e:
            logging.debug("golf rankings %s: %s", d, e)
    logging.warning("Could not load golf world rankings")
    return {}


def get_golf_event_detail(espn_event_id):
    """Return (event_info dict, players list) for a PGA event.
    Uses scoreboard?id= which works pre-tournament and live. Cached 60s."""
    cache_key = f'golf_event_detail_{espn_event_id}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{_GOLF_BASE}/scoreboard?id={espn_event_id}", timeout=10).json()

        target = next(
            (e for e in r.get('events', []) if str(e.get('id')) == str(espn_event_id)),
            None
        )
        if not target:
            return {}, []

        status_obj = target.get('status', {}).get('type', {})
        event_info = {
            'name': target.get('name', ''),
            'status_name': status_obj.get('name', ''),
            'status_desc': status_obj.get('description', ''),
        }

        comps = target.get('competitions', [])
        if not comps:
            return event_info, []

        players = []
        for competitor in comps[0].get('competitors', []):
            athlete = competitor.get('athlete', {}) or {}

            # Status — present during/after event, absent pre-tournament
            c_status = competitor.get('status', {}) or {}
            c_status_type = c_status.get('type', {}) or {}
            status_name = c_status_type.get('name', 'STATUS_ACTIVE')
            is_eliminated = status_name in (
                'STATUS_CUT', 'STATUS_WITHDRAWN', 'STATUS_WD', 'STATUS_DQ', 'STATUS_MC'
            )
            pos_obj = c_status.get('position', {}) or {}
            display_pos = pos_obj.get('displayName') or str(competitor.get('order', '-'))

            # Round scores — pre-tournament linescores have no displayValue
            rounds = {}
            for ls in competitor.get('linescores', []):
                period = str(ls.get('period', ''))
                val = ls.get('displayValue', '')
                if period and val:
                    rounds[period] = val

            # Score: 'E' pre-tournament, signed int string or int during event
            raw = competitor.get('score', 'E')
            try:
                if raw in ('E', None, ''):
                    total_value, total_display = 0, 'E'
                else:
                    total_value = int(raw)
                    total_display = ('E' if total_value == 0
                                     else (f'+{total_value}' if total_value > 0
                                           else str(total_value)))
            except (ValueError, TypeError):
                total_value, total_display = 0, 'E'

            players.append({
                'espn_id': competitor.get('id') or athlete.get('id', ''),
                'name': athlete.get('displayName') or athlete.get('fullName', ''),
                'short_name': athlete.get('shortName') or athlete.get('displayName', ''),
                'status': status_name,
                'is_eliminated': is_eliminated,
                'sort_order': competitor.get('order', 9999),
                'display_position': display_pos,
                'total_display': total_display,
                'total_value': total_value,
                'total_strokes': '-',
                'rounds': rounds,
                'world_rank': None,
                'tee_time': None,
                'thru': None,
            })

        # Annotate with world rankings
        rankings = get_golf_world_rankings()
        for p in players:
            p['world_rank'] = rankings.get(str(p['espn_id']))

        # Pre-tournament: sort by world rank (ranked first, then alpha by name)
        # During event: sort by leaderboard position (sort_order)
        event_status = event_info.get('status_name', '')
        if event_status in ('STATUS_SCHEDULED', ''):
            players.sort(key=lambda p: (
                p['world_rank'] is None,
                p['world_rank'] or 0,
                p['name'],
            ))
        else:
            players.sort(key=lambda p: p['sort_order'])

        result = (event_info, players)
        _cache_set(cache_key, result, 60)  # 60s
        return result
    except Exception as e:
        logging.error("get_golf_event_detail(%s) error: %s", espn_event_id, e)
        return {}, []


def get_golf_tee_times(espn_event_id):
    """Return {player_espn_id: {tee_time, thru}} for all competitors.
    Makes one HTTP call per player in parallel. Cached 60s."""
    cache_key = f'golf_tee_times_{espn_event_id}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    from concurrent.futures import ThreadPoolExecutor, as_completed
    _core = ("https://sports.core.api.espn.com/v2/sports/golf/leagues/pga"
             f"/events/{espn_event_id}/competitions/{espn_event_id}/competitors")

    # Get the current field to know which player IDs to fetch
    _, players = get_golf_event_detail(espn_event_id)
    player_ids = [p['espn_id'] for p in players if p['espn_id']]

    def _fetch_status(player_id):
        url = f"{_core}/{player_id}/status?lang=en&region=us"
        try:
            s = requests.get(url, timeout=6).json()
            raw_tt = s.get('teeTime') or s.get('displayValue', '')
            tee_time = None
            if raw_tt:
                try:
                    dt = datetime.fromisoformat(raw_tt.replace('Z', '+00:00'))
                    tee_time = dt.astimezone(timezone(timedelta(hours=-4))).strftime('%-I:%M %p')
                except Exception:
                    tee_time = raw_tt
            return player_id, tee_time, s.get('thru')
        except Exception:
            return player_id, None, None

    result = {}
    try:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(_fetch_status, pid): pid for pid in player_ids}
            for f in as_completed(futures):
                pid, tee_time, thru = f.result()
                result[str(pid)] = {'tee_time': tee_time, 'thru': thru}
    except Exception as e:
        logging.warning("get_golf_tee_times(%s) error: %s", espn_event_id, e)

    _cache_set(cache_key, result, 60)  # 60s
    return result


def get_golf_event_raw(espn_event_id):
    """Return the raw first competitor object and competition-level odds from ESPN.
    Used for inspecting what fields ESPN exposes (odds, futures, etc.)."""
    try:
        r = requests.get(f"{_GOLF_BASE}/scoreboard?id={espn_event_id}", timeout=10).json()
        target = next(
            (e for e in r.get('events', []) if str(e.get('id')) == str(espn_event_id)),
            None
        )
        if not target:
            return {'error': 'event not found'}
        comps = target.get('competitions', [])
        if not comps:
            return {'error': 'no competitions'}
        comp = comps[0]
        competitors = comp.get('competitors', [])
        return {
            'competition_keys':       list(comp.keys()),
            'competition_odds':       comp.get('odds'),
            'competition_futures':    comp.get('futures'),
            'first_competitor_raw':   competitors[0] if competitors else None,
            'second_competitor_raw':  competitors[1] if len(competitors) > 1 else None,
        }
    except Exception as e:
        return {'error': str(e)}


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
