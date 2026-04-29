from flask import Blueprint, jsonify, redirect, request, session
from db_accessor.db_accessor import db2
from utils import apology, login_required
from services.pickem_service import get_pickem_games, sref_to_pickem
from services.espn_client import get_espn_scores, get_ncaab_games
from funnel_helper import elimination_check
from collections import OrderedDict
from datetime import datetime, timedelta
import logging

bp = Blueprint('pickem', __name__)


@bp.route("/add_bowl_user", methods=["POST"])
def add_bowl_user():
    userid = int(request.form.get('userid'))
    db2("UPDATE users SET is_bowl_user = 1 WHERE userid = %s;", (userid,))
    return redirect('/app/bowl_payment_status')

@bp.route("/bowl_mark_paid", methods=["POST"])
def bowl_mark_paid():
    userid = int(request.form.get("userid"))
    season = datetime.utcnow().year - 1

    s = f"SELECT userid, payment_status FROM bowl_payment where season = {season};"
    paid_status = dict(db2(s))

    if userid not in paid_status:
        s = "INSERT INTO bowl_payment (userid, payment_status, season) VALUES (%s, %s, %s);"
        db2(s, (userid, True, season))
    elif paid_status[userid] == False:
        s = "UPDATE bowl_payment SET payment_status = %s, payment_status_dh = %s WHERE userid = %s;"
        db2(s, (True, False, userid))
    else:
        s = "UPDATE bowl_payment SET payment_status = %s, payment_status_dh = %s WHERE userid = %s;"
        db2(s, (False, False, userid))

    return redirect('/app/bowl_payment_status')

@bp.route("/bowl_mark_paid_dh", methods=["POST"])
def bowl_mark_paid_dh():
    userid = int(request.form.get("userid"))
    season = datetime.utcnow().year - 1

    s = f"SELECT userid, payment_status_dh FROM bowl_payment where season = {season};"
    paid_status = dict(db2(s))

    if userid not in paid_status:
        s = "INSERT INTO bowl_payment (userid, payment_status, payment_status_dh, season) VALUES (%s, %s, %s, %s);"
        db2(s, (userid, True, True, season))
    elif paid_status[userid] == False:
        s = "UPDATE bowl_payment SET payment_status = %s, payment_status_dh = %s WHERE userid = %s;"
        db2(s, (True, True, userid))
    else:
        s = "UPDATE bowl_payment SET payment_status = %s, payment_status_dh = %s WHERE userid = %s;"
        db2(s, (False, False, userid))

    return redirect('/app/bowl_payment_status')

@bp.route("/lock_pickem_game", methods=["POST"])
def lock_pickem_game():
    game_name = request.form.get('game_name')
    if not game_name:
        return apology("what game you locking??")
    lock_val = request.form.get('lock')
    if lock_val is None:
        return apology("lock or unlock?  which is it??")
    lock = int(lock_val)

    games_dict = {"WC-Sat" : (1,2,3), "WC-Sun": (4,5,6), "DIV-Sat" : (7,8), "DIV-Sun" : (9,10), "CONF-NFC" : (11,), "CONF-AFC" : (12,), "Super Bowl" : (13,)}
    game_tup = (lock, ) + games_dict[game_name]

    param_string = ', '.join(['%s'] * len(games_dict[game_name]))
    s = "UPDATE pickem.games SET locked = %s WHERE gameid in ({});".format(param_string)
    db2(s, game_tup)

    current_game = games_dict[game_name][0]
    if current_game != 1 and lock == 1:
        last_game = current_game - 1
        s = "SELECT userid, gameid, pick FROM pickem.userpicks WHERE gameid in ({}, {}) ORDER BY pickid DESC;".format(last_game, current_game)
        picks = db2(s)

        user_dict = {}
        for user in picks:
            if user[0] not in user_dict:
                user_dict[user[0]] = {user[1] : user[2]}
            elif user[1] not in user_dict[user[0]]:
                user_dict[user[0]][user[1]] = user[2]

        x_list = [u for u in user_dict if current_game not in user_dict[u]]
        for x in x_list:
            u = "INSERT INTO pickem.userpicks (userid, season, gameid, pick) VALUES ({}, 2021, {}, 'x');".format(x, current_game)
            db2(u)

    return redirect('/app/pickem_admin')


@bp.route("/create_pickem_game", methods=["POST"])
def create_pickem_game():
    season = request.form.get('season')
    if not season:
        return apology("what season?  2021?")
    game_name = request.form.get('game_name')
    if not game_name:
        return apology("pick a game name please")
    fav = request.form.get('fav')
    if not fav:
        return apology("missing favorite")
    spread = request.form.get('spread')
    if not spread:
        return apology("missing spread")
    dog = request.form.get('dog')
    if not dog:
        return apology("missing underdog")

    if game_name == "Super Bowl":
        gameid = 13
    elif game_name[0] == "C":
        gameid = game_name[-2:]
    elif game_name == "DIV 10":
        gameid = 10
    else:
        gameid = int(game_name[-1:])

    s = "INSERT INTO pickem.games (season, gameid, game_name, fav, dog, spread, locked) values (%s, %s, %s, %s, %s, %s, 0);"
    db2(s, (season, gameid, game_name, fav, dog, spread))

    return redirect('/app/pickem_admin')


@bp.route("/pickem_mark_paid", methods=["POST"])
def pickem_mark_paid():
    userid = int(request.form.get("userid"))

    s = "SELECT * FROM pickem.pickem_payment;"
    paid_status = dict(db2(s))

    if userid not in paid_status:
        s = "INSERT INTO pickem.pickem_payment (userid, payment_status) VALUES (%s, %s);"
        db2(s, (userid, True))
    else:
        s = "UPDATE pickem.pickem_payment SET payment_status = %s WHERE userid = %s;"
        db2(s, (True, userid))

    return redirect('/app/pickem_payment_status')

@bp.route("/pickem_enable_user", methods=["POST"])
def pickem_enable_user():
    userid = int(request.form.get("userid"))
    db2("UPDATE users SET is_pickem_user = 1 WHERE userid = %s", (userid,))
    return redirect('/app/pickem_admin')


@bp.route("/api/ncaab_games", methods=["GET"])
@login_required
def api_ncaab_games():
    data = get_ncaab_games()
    events = []
    for event in data.get('events', []):
        competitors = []
        for competition in event.get('competitions', []):
            for competitor in competition.get('competitors', []):
                competitors.append({'abbr': competitor['team']['abbreviation'], 'score': competitor['score']})
        events.append({'id': event['id'], 'date': event['date'], 'name': event['shortName'], 'competitors': competitors})
    return jsonify({'events': events})


@bp.route("/api/pickem_admin", methods=["GET"])
def api_pickem_admin():
    if not session.get('userid'):
        return jsonify({'error': 'unauthorized'}), 401
    season = 2021
    game_name_list = ["WC 1", "WC 2", "WC 3", "WC 4", "WC 5", "WC 6", "DIV 7", "DIV 8", "DIV 9", "DIV 10", "CONF 11", "CONF 12", "Super Bowl"]
    game_group_list = ["WC-Sat", "WC-Sun", "DIV-Sat", "DIV-Sun", "CONF-NFC", "CONF-AFC", "Super Bowl"]
    return jsonify({'game_name_list': game_name_list, 'game_group_list': game_group_list, 'season': season})


@bp.route("/api/pickem_game_list", methods=["GET"])
@login_required
def api_pickem_game_list():
    season = 2021
    game_list = get_pickem_games(season)
    game_dict = get_pickem_games(season, True)

    p = "SELECT gameid, pick FROM pickem.userpicks WHERE userid = %s ORDER BY pickid DESC"
    picks = db2(p, (session['userid'],))
    user_picks = {}
    for pick in picks:
        if pick[0] not in user_picks:
            user_picks[pick[0]] = pick[1]

    t = "SELECT tiebreak FROM pickem.tiebreak WHERE userid = %s ORDER BY tiebreak_id DESC;"
    tb = db2(t, (session['userid'],))
    user_picks['tb'] = tb[0][0] if tb else ''

    games_json = {}
    for gid in game_list:
        g = game_dict[gid]
        games_json[str(gid)] = {
            'game_name': g.game_name,
            'fav': g.fav,
            'spread': g.spread,
            'dog': g.dog,
            'locked': g.locked,
            'winner': g.winner,
        }

    picks_json = {str(k): v for k, v in user_picks.items()}
    return jsonify({'game_list': game_list, 'games': games_json, 'user_picks': picks_json})


@bp.route("/api/select_pickem_games", methods=["POST"])
def api_select_pickem_games():
    if not session.get('userid'):
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    season = 2021
    game_list = get_pickem_games(season)

    for game in game_list:
        pick = data.get(str(game), '').strip().upper()
        if pick:
            p = "INSERT INTO pickem.userpicks (userid, season, gameid, pick, datetime) VALUES (%s, %s, %s, %s, convert_tz(now(), '-00:00', '-05:00'));"
            db2(p, (session['userid'], season, game, pick))

    tiebreak = data.get('tb', '').strip()
    if tiebreak:
        t = "INSERT INTO pickem.tiebreak (season, userid, tiebreak, datetime) values (%s, %s, %s, convert_tz(now(), '-00:00', '-05:00'));"
        db2(t, (season, session['userid'], tiebreak))

    logging.info("{} just selected picks".format(session["username"]))
    return jsonify({'success': True})


@bp.route("/api/pickem_payment_status", methods=["GET"])
def api_pickem_payment_status():
    if not session.get('userid'):
        return jsonify({'error': 'unauthorized'}), 401
    season = 2021

    u = "SELECT DISTINCT up.userid, u.username FROM pickem.userpicks up LEFT JOIN users u ON up.userid = u.userid WHERE up.season = {};".format(season)
    pickem_users = dict(db2(u))

    p = "SELECT * FROM pickem.pickem_payment;"
    payment_dict = dict(db2(p))

    uid = "SELECT userid, username FROM users WHERE is_pickem_user = 1"
    empty_users = db2(uid)
    if empty_users:
        for user in empty_users:
            pickem_users[user[0]] = user[1]

    prize_pool = 50 * len(pickem_users)
    admins = [a[0] for a in db2("SELECT userid FROM users WHERE is_admin = 1;")]

    check = '✔'
    ex = '❌'
    middle_finger = '\U0001f595'

    display_list = []
    for user in pickem_users:
        if user not in payment_dict:
            status = ex
        elif user == 113:
            status = middle_finger
        elif payment_dict[user]:
            status = check
        else:
            status = ex
        display_list.append({'userid': user, 'username': pickem_users[user], 'status': status})

    return jsonify({'display_list': display_list, 'admins': admins, 'total_users': len(display_list), 'prize_pool': prize_pool})


@bp.route("/api/enter_pickem_scores", methods=["POST"])
def api_enter_pickem_scores():
    if not session.get('userid'):
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    gameid = data.get('gameid')
    fav_score = data.get('fav')
    dog_score = data.get('dog')
    s = "INSERT INTO pickem.pickem_scores (gameid, fav_score, dog_score) values (%s, %s, %s);"
    db2(s, (int(gameid), int(fav_score), int(dog_score)))
    return jsonify({'success': True})


@bp.route("/api/bowl_payment_status", methods=["GET"])
@login_required
def api_bowl_payment_status():
    season = datetime.utcnow().year - 1

    e = f"SELECT espnid FROM latest_lines WHERE season = {season} and league = 'nfl';"
    espnids = db2(e)
    if not espnids:
        return jsonify({'display_list': [], 'admins': [], 'total_users': 0, 'prize_pool': 0, 'user_dict': {}})

    espn_string = ', '.join(str(e[0]) for e in espnids)

    u = f"SELECT DISTINCT up.userid, u.username FROM bowlpicks up LEFT JOIN users u ON up.userid = u.userid WHERE up.espnid in ({espn_string});"
    bowl_users = dict(db2(u))

    bu = "SELECT userid, username FROM users WHERE is_bowl_user = 1"
    no_picks_users = db2(bu)
    for user in no_picks_users:
        if user[0] not in bowl_users:
            bowl_users[user[0]] = user[1]

    uname_string = "SELECT userid, username, first_name, last_name FROM users;"
    usernames = db2(uname_string)
    user_dict = {uid: {'username': un, 'first_name': fn, 'last_name': ln} for uid, un, fn, ln in usernames}

    prize_pool = 50 * len(bowl_users)
    admins = [a[0] for a in db2("SELECT userid FROM users WHERE is_admin = 1;")]

    check = '✔'
    ex = '❌'
    thumbs_up = '👍'
    thumbs_down = '👎'
    middle_finger = '🖕'

    p = f"SELECT userid, payment_status, payment_status_dh FROM bowl_payment where season = {season};"
    payments = db2(p)
    payment_list = []
    payment_list_dh = []
    for pu in payments:
        if pu[1]: payment_list.append(pu[0])
        if pu[2]: payment_list_dh.append(pu[0])

    display_list = []
    for user in bowl_users:
        if user == 113:
            paid_status = check if user in payment_list else middle_finger
            dh_status = thumbs_down
        elif user not in payment_list and user not in payment_list_dh:
            paid_status = ex
            dh_status = thumbs_down
        elif user in payment_list_dh:
            paid_status = check
            dh_status = thumbs_up
        else:
            paid_status = check
            dh_status = thumbs_down
        display_list.append({'userid': user, 'username': bowl_users[user], 'paid': paid_status, 'paid_dh': dh_status})

    return jsonify({'display_list': display_list, 'user_dict': user_dict, 'admins': admins, 'total_users': len(display_list), 'prize_pool': prize_pool})


@bp.route("/api/pickem_all_picks", methods=["GET"])
@login_required
def api_pickem_all_picks():
    season = 2021

    g = "SELECT max(gameid) FROM pickem.pickem_scores;"
    max_game = db2(g)[0][0]
    if max_game:
        games_left = 13 - max_game
    else:
        games_left = 13
        max_game = 0
    eliminated_list = []

    game_dict = get_pickem_games(season, True)
    game_list = get_pickem_games(season)
    game_details = []
    for game in game_list:
        if game_dict[game].spread != 0:
            game_details.append("{} {} {}".format(game_dict[game].fav, game_dict[game].spread, game_dict[game].dog))
        else:
            game_details.append("TBD")

    p = "SELECT pickid, userid, gameid, pick from pickem.userpicks order by pickid desc;"
    all_picks = db2(p)

    user_pick_list = []
    user_picks = {}
    user_picks_unplayed_list = []
    user_picks_unplayed = {}
    current_user = session['userid']

    u = "SELECT userid, username FROM users;"
    usernames = dict(db2(u))

    for pick in all_picks:
        if pick[1] in usernames:
            username = usernames[pick[1]]
        else:
            username = '*****DELETE'
        if game_dict[pick[2]].locked == 1 or current_user == pick[1]:
            if (pick[1], pick[2]) not in user_pick_list:
                user_pick_list.append((pick[1], pick[2]))
                if username not in user_picks:
                    user_picks[username] = {'picks': {n: '' for n in range(1, 14)}, 'win_count': 0, 'max_wins': 13}
                    user_picks[username]['picks'][pick[2]] = pick[3]
                else:
                    user_picks[username]['picks'][pick[2]] = pick[3]
            if (pick[1], pick[2]) not in user_picks_unplayed_list:
                user_picks_unplayed_list.append((pick[1], pick[2]))
                if username not in user_picks_unplayed and pick[2] > max_game and game_dict[pick[2]].locked == 1:
                    user_picks_unplayed[username] = [pick[3]]
                elif pick[2] > max_game and game_dict[pick[2]].locked == 1:
                    user_picks_unplayed[username].append(pick[3])
        else:
            if (pick[1], pick[2]) not in user_pick_list:
                user_pick_list.append((pick[1], pick[2]))
                if username not in user_picks:
                    user_picks[username] = {'picks': {n: '' for n in range(1, 14)}, 'win_count': 0, 'max_wins': 13}
                    user_picks[username]['picks'][pick[2]] = 'hidden'
                else:
                    user_picks[username]['picks'][pick[2]] = 'hidden'

    uid = "SELECT userid FROM users WHERE is_pickem_user = 1"
    empty_users = db2(uid)
    if empty_users:
        for userid_row in empty_users:
            if usernames.get(userid_row[0]) and usernames[userid_row[0]] not in user_picks:
                user_picks[usernames[userid_row[0]]] = {'picks': {n: '' for n in range(1, 14)}, 'win_count': 0, 'max_wins': 13}

    t = "SELECT userid, tiebreak FROM pickem.tiebreak WHERE season = %s ORDER BY tiebreak_id DESC;"
    tbs = db2(t, (season,))
    tb_dict = {}
    for tb in tbs:
        username = usernames.get(tb[0], '')
        if game_dict[13].locked == 1 or current_user == tb[0]:
            if username not in tb_dict:
                tb_dict[username] = tb[1]
        else:
            if username not in tb_dict:
                tb_dict[username] = 'hidden'

    max_wins = 0
    max_win_users = []
    second_best_users = []

    for user in user_picks:
        no_pick_count = 0
        for game in user_picks[user]['picks']:
            if game_dict[game].winner.upper() == user_picks[user]['picks'][game] and user_picks[user]['picks'][game] != '':
                user_picks[user]['win_count'] += 1
            elif user_picks[user]['picks'][game] == 'x':
                no_pick_count += 1

        if user_picks[user]['win_count'] > max_wins:
            max_wins = user_picks[user]['win_count']
            if max_win_users:
                second_best_users = max_win_users
            max_win_users = [user]
        elif user_picks[user]['win_count'] == max_wins:
            max_win_users.append(user)
        elif user_picks[user]['win_count'] == max_wins - 1:
            second_best_users.append(user)

        user_picks[user]['max_wins'] = user_picks[user]['win_count'] + games_left - no_pick_count

    for user in user_picks:
        wins_behind = max_wins - user_picks[user]['win_count']
        diff = games_left - wins_behind
        if user_picks[user]['max_wins'] < max_wins:
            eliminated_list.append(user)

    winner = []
    tie_break_log = []
    if game_dict[13].winner != "TBD":
        score = db2("SELECT fav_score, dog_score FROM pickem.pickem_scores WHERE gameid = 13 ORDER BY score_id DESC;")
        if len(max_win_users) == 1:
            winner.append(max_win_users[0])
        elif len(max_win_users) > 1 and score:
            total_score = score[0][0] + score[0][1]
            closest_score = 1000
            closest_users = []
            for user in max_win_users:
                if user in tb_dict and isinstance(tb_dict[user], (int, float)):
                    tb_log_entry = "{}'s tiebreak of {} is {} away from {}".format(user, tb_dict[user], abs(tb_dict[user] - total_score), total_score)
                    if abs(tb_dict[user] - total_score) < closest_score:
                        closest_score = abs(tb_dict[user] - total_score)
                        closest_users = [user]
                        tie_break_log.insert(0, tb_log_entry)
                    elif abs(tb_dict[user] - total_score) == closest_score:
                        closest_users.append(user)
                        tie_break_log.append(tb_log_entry)
                    else:
                        tie_break_log.append(tb_log_entry)
            winner = closest_users

    winning_user = '{} Playoff Pickem Winner'.format(season)
    if len(winner) > 1:
        winning_user += 's: ' + ' and '.join(winner)
    elif len(winner) == 1:
        winning_user += ': {}'.format(winner[0])
    else:
        winning_user = ''

    eliminated_list += ['jzhao8', 'GC1', 'Algo_O', 'rgimbel']

    sorted_user_picks = dict(sorted(user_picks.items(), key=lambda x: x[1]['win_count'], reverse=True))
    game_dict_json = {str(gid): {'fav': g.fav, 'spread': g.spread, 'dog': g.dog, 'locked': g.locked, 'winner': g.winner} for gid, g in game_dict.items()}
    user_picks_json = {u: {'picks': {str(k): v for k, v in up['picks'].items()}, 'win_count': up['win_count'], 'max_wins': up['max_wins']} for u, up in sorted_user_picks.items()}

    return jsonify({
        'game_details': game_details,
        'user_picks': user_picks_json,
        'game_dict': game_dict_json,
        'current_username': session['username'],
        'tb_dict': tb_dict,
        'winning_user': winning_user,
        'tie_break_log': tie_break_log,
        'winner': winner,
        'eliminated_list': eliminated_list,
    })


def _serialize_game(g):
    """Convert a game_dict entry with a datetime to a JSON-safe dict."""
    return {
        'espn_id': g['espn_id'],
        'date': g['date'],
        'date_short': g.get('date_short', ''),
        'datetime': g['datetime'].isoformat(),
        'venue': g.get('venue', ''),
        'competitors': g['competitors'],
        'abbreviations': g['abbreviations'],
        'line': g['line'],
        'over_under': g.get('over_under', 'TBD'),
        'headline': g.get('headline', ''),
        'location': g.get('location', ''),
        'status': g['status'],
        'current_winner': g.get('current_winner', ''),
        'winner': g.get('winner', 'TBD'),
    }


@bp.route("/api/display_pickem_games", methods=["GET"])
@login_required
def api_display_pickem_games():
    now = datetime.utcnow() - timedelta(hours=5)
    season = 2021
    season_type = 3
    weeks = [1, 2, 3, 5]
    league = 'nfl'
    game_dicts = []
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])
    game_dict = {k: v for d in game_dicts for k, v in d.items()}
    sorted_game_dict = OrderedDict(sorted(game_dict.items(), key=lambda x: x[1]['datetime']))

    p = "SELECT espnid, pick FROM bowlpicks WHERE userid = %s ORDER BY pick_id ASC;"
    picks = dict(db2(p, (session['userid'],)))

    t = "SELECT tiebreak FROM bowl_tiebreaks WHERE userid = %s and season = %s ORDER BY tiebreak_id DESC LIMIT 1;"
    tb = db2(t, (session['userid'], season))
    tiebreak = tb[0][0] if tb else ''

    return jsonify({
        'games': {str(k): _serialize_game(v) for k, v in sorted_game_dict.items()},
        'picks': {str(k): v for k, v in picks.items()},
        'tiebreak': tiebreak,
        'now': now.isoformat(),
    })


@bp.route("/api/select_bowl_games", methods=["POST"])
@login_required
def api_select_bowl_games():
    data = request.get_json()
    picks = data.get('picks', {})
    tiebreak = data.get('tiebreak', '').strip()
    season_type = 3
    weeks = [1, 2, 3, 5]
    league = 'nfl'
    game_dicts = []
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])
    game_dict = {k: v for d in game_dicts for k, v in d.items()}
    for game in game_dict:
        espnid = str(game_dict[game]['espn_id'])
        if espnid in picks and picks[espnid] and picks[espnid] != 'TBD':
            s = "INSERT INTO bowlpicks (userid, espnid, pick, datetime) VALUES (%s, %s, %s, now());"
            db2(s, (session['userid'], game_dict[game]['espn_id'], picks[espnid]))
    season = 2021
    if tiebreak:
        t = "INSERT INTO bowl_tiebreaks (season, userid, tiebreak, datetime) VALUES (%s, %s, %s, now());"
        db2(t, (season, session['userid'], tiebreak))
    logging.info("{} just selected bowl picks via API".format(session["username"]))
    return jsonify({'success': True})


@bp.route("/api/view_all_picks", methods=["GET"])
@login_required
def api_view_all_picks():
    season_type = 3
    weeks = [1, 2, 3, 5]
    league = 'nfl'
    now = datetime.utcnow() - timedelta(hours=5)
    annual = now.year - 2010
    game_dicts = []
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])
    game_dict = {k: v for d in game_dicts for k, v in d.items()}

    espnid_string = ', '.join(str(g) for g in game_dict) if game_dict else '0'

    u = "SELECT userid, username, first_name, last_name, is_admin FROM users WHERE active = 1;"
    user_info = db2(u)
    user_dict = {user[0]: {'username': user[1], 'name': user[2] + ' ' + user[3], 'is_admin': user[4]} for user in user_info}

    l = "SELECT datetime FROM latest_lines WHERE datetime IS NOT NULL ORDER BY datetime DESC LIMIT 1"
    ll = db2(l)
    last_line_time = (ll[0][0] - timedelta(hours=5)).isoformat() if ll else ''

    locked_games = set()
    winning_teams = set()
    winning_d = {}
    for game in game_dict:
        if game_dict[game]['datetime'] > datetime.utcnow() - timedelta(hours=5) or game_dict[game]['status'].get('status') == 'Canceled':
            locked_games.add(game_dict[game]['espn_id'])
            game_dict[game]['winner'] = 'TBD'
        else:
            home_score = float(game_dict[game]['competitors'][0][2] or 0)
            away_score = float(game_dict[game]['competitors'][1][2] or 0)
            line = game_dict[game]['line']
            if isinstance(line, list) and len(line) > 1 and line[0] == game_dict[game]['abbreviations'].get('HOME'):
                home_score += float(line[1])
            elif isinstance(line, list) and len(line) > 1 and line[0] == game_dict[game]['abbreviations'].get('AWAY'):
                away_score += float(line[1])
            if home_score > away_score:
                game_dict[game]['winner'] = game_dict[game]['abbreviations'].get('HOME')
                winning_teams.add((game, game_dict[game]['abbreviations'].get('HOME')))
                winning_d[game] = game_dict[game]['abbreviations'].get('HOME')
            elif away_score > home_score:
                game_dict[game]['winner'] = game_dict[game]['abbreviations'].get('AWAY')
                winning_teams.add((game, game_dict[game]['abbreviations'].get('AWAY')))
                winning_d[game] = game_dict[game]['abbreviations'].get('AWAY')
            else:
                game_dict[game]['winner'] = 'PUSH'
                winning_d[game] = 'PUSH'

    s = f"SELECT userid, espnid, pick FROM bowlpicks WHERE espnid in ({espnid_string}) and pick_id in (SELECT max(pick_id) from bowlpicks GROUP BY userid, espnid);"
    all_picks = db2(s)

    t = "SELECT userid, tiebreak FROM bowl_tiebreaks WHERE tiebreak_id in (SELECT max(tiebreak_id) FROM bowl_tiebreaks GROUP BY userid);"
    tb_dict = dict(db2(t))

    ignore = [401331242, 401331217, 401331220, 401339628, 401331225, 401352013]
    d = {}
    for pick in all_picks:
        pick_userid, pick_espnid, pick_team = pick
        if pick_espnid not in ignore:
            if pick_userid not in d:
                d[pick_userid] = {pick_espnid: pick_team, 'wins': 1 if (pick_espnid, pick_team) in winning_teams else 0}
            else:
                d[pick_userid][pick_espnid] = pick_team
                if (pick_espnid, pick_team) in winning_teams:
                    d[pick_userid]['wins'] += 1
        if pick_userid in tb_dict:
            d[pick_userid]['tb'] = tb_dict[pick_userid]

    bu = "SELECT userid FROM users WHERE is_bowl_user = 1;"
    bowl_users = db2(bu)
    if bowl_users:
        for user in bowl_users:
            if user[0] not in d:
                d[user[0]] = {'wins': 0}

    sorted_d = OrderedDict(sorted(d.items(), key=lambda x: x[1]['wins'], reverse=True))
    sorted_game_dict = OrderedDict(sorted(game_dict.items(), key=lambda x: x[1]['datetime']))

    if sorted_d:
        eliminated_check = elimination_check(sorted_game_dict, sorted_d, user_dict)
        eliminated_list = eliminated_check['elim']
        winner = eliminated_check['winner']
        tb_log = eliminated_check['tb_log']
    else:
        eliminated_list = []
        winner = []
        tb_log = []

    t2 = "SELECT userid, tiebreak FROM bowl_tiebreaks WHERE tiebreak_id in (SELECT max(tiebreak_id) FROM bowl_tiebreaks GROUP BY userid);"
    tb_dict = dict(db2(t2))

    return jsonify({
        'games': {str(k): _serialize_game(v) for k, v in sorted_game_dict.items()},
        'picks': {str(k): {str(ek): ev for ek, ev in v.items()} for k, v in sorted_d.items()},
        'locked_games': list(locked_games),
        'user_dict': {str(k): v for k, v in user_dict.items()},
        'tb_dict': {str(k): v for k, v in tb_dict.items()},
        'now': now.isoformat(),
        'last_line_time': last_line_time,
        'eliminated_list': eliminated_list,
        'winner': winner,
        'tb_log': tb_log,
        'annual': annual,
        'current_userid': session['userid'],
        'current_username': session['username'],
        'is_admin': user_dict.get(session['userid'], {}).get('is_admin', 0),
    })
