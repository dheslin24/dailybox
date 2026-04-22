from flask import Blueprint, flash, redirect, render_template, request, session, url_for, Markup
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required
from services.pickem_service import get_pickem_games, sref_to_pickem
from espnapi import get_espn_scores, get_ncaab_games
from funnel_helper import elimination_check
from collections import OrderedDict
from datetime import datetime, timedelta
import logging

bp = Blueprint('pickem', __name__)


# @bp.route("/display_bowl_games", methods=["GET", "POST"])
@bp.route("/display_pickem_games", methods=["GET", "POST"])
@login_required
def display_pickem_games():

    now = datetime.utcnow() - timedelta(hours=5)
    season = 2021
    season_type = 3
    weeks = [1, 2, 3, 5] #  - [1, 2, 3, 5] - 4 is probowl
    league = 'nfl'
    game_dicts = []
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])

    game_dict = {k: v for d in game_dicts for k, v in d.items()}

    sorted_game_dict = OrderedDict(sorted(game_dict.items(), key=lambda x:x[1]['datetime']))
    print(f"sorted game dict in display picks {sorted_game_dict}")

    # get users picks
    p = "SELECT espnid, pick FROM bowlpicks WHERE userid = %s ORDER BY pick_id ASC;"
    picks = db2(p, (session['userid'],))
    print(f"dict picks: {dict(picks)}")

    # get tiebreaks
    t = "SELECT tiebreak FROM bowl_tiebreaks WHERE userid = %s and season = %s ORDER BY tiebreak_id DESC LIMIT 1;"
    tb = db2(t, (session['userid'], season))
    if tb:
        tiebreak = tb[0][0]
    else:
        tiebreak = ''
    if session:
        logging.info(f"user {session['username']} just hit display all games")
    else:
        logging.info("someone just hit display all bowls but isn't logged in")
    return render_template("display_pickem_games.html", game_dict = sorted_game_dict, picks=dict(picks), now=now, tiebreak=tiebreak)

@bp.route("/select_bowl_games", methods=["GET", "POST"])
@login_required
def select_bowl_games():

    season_type = 3
    weeks = [1, 2, 3, 5] # [1, 2, 3, 5]  - week 4 is probowl
    league = 'nfl'
    game_dicts = []
    # get list of active espn ids
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])

    game_dict = {k: v for d in game_dicts for k, v in d.items()}
    print(game_dict)

    # iterate through them, getting the pick value
    # insert picks into bowlpicks table
    for game in game_dict:
        if request.form.get(str(game_dict[game]['espn_id'])) and request.form.get(str(game_dict[game]['espn_id'])) != "TBD":
            s = "INSERT INTO bowlpicks (userid, espnid, pick, datetime) VALUES (%s, %s, %s, now());"  # local time, EST
            db2(s, (session['userid'], game_dict[game]['espn_id'], request.form.get(str(game_dict[game]['espn_id']))))

    tiebreak = request.form.get('tb')
    print(f"tiebreak:  {tiebreak}")

    season = 2021
    if tiebreak != None and len(tiebreak) != 0:
        t = "INSERT INTO bowl_tiebreaks (season, userid, tiebreak, datetime) VALUES (%s, %s, %s, now());"
        db2(t, (season, session['userid'], tiebreak))

    print(f"{session['username']} just selected bowl picks")
    logging.info("{} just actually selected picks".format(session["username"]))

    return redirect(url_for('pickem.view_all_picks'))

@bp.route("/view_all_picks", methods = ["GET", "POST"])
@login_required
def view_all_picks():

    season_type = 3
    weeks = [1, 2, 3, 5] # [1, 2, 3, 5]  - week 4 is probowl
    league = 'nfl'
    now = datetime.utcnow() - timedelta(hours=5)
    annual = now.year - 2010
    # get list of active games first
    #game_dict = get_espn_scores(False)['game']
    game_dicts = []
    for week in weeks:
        game_dicts.append(get_espn_scores(False, season_type, week, league)['game'])

    game_dict = {k: v for d in game_dicts for k, v in d.items()}

    # print("\n\n\n-------------------- GAME DICT -------------------\n\n\n")
    # print(game_dict)
    # print("\n\n\n-------------- END GAME DICT ---------------------\n\n\n")

    espnid_string = ''
    for game in game_dict:
        espnid_string += str(game) + ', '
    espnid_string = espnid_string[:-2]

    # get dict of userid: username for display
    u = "SELECT userid, username, first_name, last_name, is_admin FROM users WHERE active = 1;"
    user_info = db2(u)
    #print(f"user info: {user_info}")

    # user0:  userid   user1:  username   user2: first name  user3: last name   user4: is_admin (1 or 0)
    user_dict = {}
    for user in user_info:
        user_dict[user[0]] = {'username': user[1], 'name': user[2] + ' ' + user[3], 'is_admin': user[4]}

    print(user_dict)

    # get last update in latest_lines table - display to admins
    l = "SELECT datetime FROM latest_lines WHERE datetime IS NOT NULL ORDER BY datetime DESC LIMIT 1"
    ll = db2(l)

    last_line_time = ll[0][0] - timedelta(hours=5)

    # create set of locked games to hide in view all screen for non user
    # and if unlocked, calc winner
    locked_games = set()
    winning_teams = set()
    winning_d = {}
    for game in game_dict:
        # print(f"game:  {game}")
        # print(f"{game_dict[game]['datetime']} vs {datetime.utcnow()}")
        if game_dict[game]['datetime'] > datetime.utcnow() - timedelta(hours=5) or game_dict[game]['status']['status'] == 'Canceled':
            locked_games.add(game_dict[game]['espn_id'])
            game_dict[game]['winner'] = 'TBD'
        else:  # game winner calcs here.. if in progress, winner is just 'current winner'
            # get current score
            home_score = float(game_dict[game]['competitors'][0][2])
            away_score = float(game_dict[game]['competitors'][1][2])

            # is home or away fav?  or 'EVEN' do nothing?
            if game_dict[game]['line'][0] == game_dict[game]['abbreviations']['HOME']:  # home team is fav
                home_score += float(game_dict[game]['line'][1])
            elif game_dict[game]['line'][0] == game_dict[game]['abbreviations']['AWAY']:  # away is fav
                away_score += float(game_dict[game]['line'][1])

            # who is winning (or won)?  home or away?
            if home_score > away_score:
                game_dict[game]['winner'] = game_dict[game]['abbreviations']['HOME']
                winning_teams.add((game, game_dict[game]['abbreviations']['HOME']))
                winning_d[game] = game_dict[game]['abbreviations']['HOME']
            elif away_score > home_score:
                game_dict[game]['winner'] = game_dict[game]['abbreviations']['AWAY']
                winning_teams.add((game, game_dict[game]['abbreviations']['AWAY']))
                winning_d[game] = game_dict[game]['abbreviations']['AWAY']
            else:  #pushing
                game_dict[game]['winner'] = 'PUSH'
                winning_d[game] = 'PUSH'

    print("HHHHHHHHHHHHHHHEEEEEEEEEEEEEEEEERRRRRRRRRRRRRRRREEEEEEEEEEEEEEE")
    print("#<br>#<br>#<br>")
    print(f"locked games {locked_games}")
    print(f"winning teams {winning_teams}")
    print(f"winning d {winning_d}")


    # get user picks
    #           |pick0| |pick1||pick2|
    #s = "SELECT userid, espnid, pick FROM bowlpicks ORDER BY pick_id ASC;"
    s = f"SELECT userid, espnid, pick FROM bowlpicks WHERE espnid in ({espnid_string}) and pick_id in (SELECT max(pick_id) from bowlpicks GROUP BY userid, espnid);"
    all_picks = db2(s)

    # get user tiebreaks
    t = "SELECT userid, tiebreak FROM bowl_tiebreaks WHERE tiebreak_id in (SELECT max(tiebreak_id) FROM bowl_tiebreaks GROUP BY userid);"
    tb_dict = dict(db2(t))
    logging.info(f"TB DICT {tb_dict}")

    logging.info(f"all_picks {all_picks}")

    # dict of {userid:  {espnid/wins: pick/wintotal}}
    d = {}
    ignore = [401331242, 401331217, 401331220, 401339628, 401331225, 401352013] # 401331242 is final
    for pick in all_picks:
        pick_userid, pick_espnid, pick_team = pick
        if pick_espnid not in ignore:
            if pick_userid not in d:
                d[pick_userid] = {pick_espnid: pick_team}
                if(pick_espnid, pick_team) in winning_teams:
                    d[pick_userid]['wins'] = 1
                else:
                    d[pick_userid]['wins'] = 0
            else:
                d[pick_userid][pick_espnid] = pick_team
                if (pick_espnid, pick_team) in winning_teams:
                    d[pick_userid]['wins'] += 1
        if pick_userid in tb_dict:
            d[pick_userid]['tb'] = tb_dict[pick_userid]


    # add users who are in but haven't picked yet, with 0 wins
    bu = "SELECT userid FROM users WHERE is_bowl_user = 1;"
    bowl_users = db2(bu)
    print(f"bowl users: {bowl_users}")

    if bowl_users:
        for user in bowl_users:
            if user[0] not in d:
                d[user[0]] = {'wins': 0}

    sorted_d = OrderedDict(sorted(d.items(), key=lambda x:x[1]['wins'], reverse=True))
    sorted_game_dict = OrderedDict(sorted(game_dict.items(), key=lambda x:x[1]['datetime']))

    # check for winners, eliminated users, and tie break scenarios
    if sorted_d:
        eliminated_check = elimination_check(sorted_game_dict, sorted_d, user_dict)
        eliminated_list = eliminated_check['elim']
        winner = eliminated_check['winner']
        tb_log = eliminated_check['tb_log']
    else:
        eliminated_list = []
        winner = []
        tb_log = []

    # get tiebreaks
    t = "SELECT userid, tiebreak FROM bowl_tiebreaks WHERE tiebreak_id in (SELECT max(tiebreak_id) FROM bowl_tiebreaks GROUP BY userid);"
    tb_dict = dict(db2(t))
    print(f"tb_dict {tb_dict}")

    return render_template("view_all_picks.html", game_dict=sorted_game_dict, d=sorted_d, locked_games=locked_games, user_dict=user_dict, tb_dict=tb_dict, now=now, last_line_time=last_line_time, emojis=EMOJIS, eliminated_list=eliminated_list, winner=winner, tb_log=tb_log, annual=annual)

@bp.route("/bowl_payment_status", methods=["GET", "POST"])
@login_required
def bowl_payment_status():

    # if request.method == "POST":
    #     sort_method = request.form.get('sort_method')
    # else:
    #     sort_method = request.args['sort_method']

    season = datetime.utcnow().year - 1  # will only ever be run after new yrs from the season that started prev yr
    # get list of espnids
    e = f"SELECT espnid FROM latest_lines WHERE season = {season} and league = 'nfl';"
    espnids = db2(e)
    espn_string = ''
    for espnid in espnids:
        espn_string += str(espnid[0]) + ', '
    espn_string = espn_string[:-2]

    # find users that have a bowl entry
    u = f"SELECT DISTINCT up.userid, u.username FROM bowlpicks up LEFT JOIN users u ON up.userid = u.userid WHERE up.espnid in ({espn_string});"
    bowl_users = dict(db2(u))

    # or ones that are in and haven't picked yet
    bu = "SELECT userid, username FROM users WHERE is_bowl_user = 1"
    no_picks_users = db2(bu)

    # get actual names for our demanding 'admin'
    uname_string = "SELECT userid, username, first_name, last_name FROM users;"
    usernames = db2(uname_string)
    user_dict = {}
    for userid, username, first_name, last_name in usernames:
        user_dict[userid] = {"username": username, "first_name": first_name, "last_name": last_name}

    for user in no_picks_users:
        if user[0] not in bowl_users:
            bowl_users[user[0]] = user[1]

    entry = 50
    prize_pool = entry * len(bowl_users)

    # find list of admins who can update status
    s = "SELECT userid FROM users WHERE is_admin = 1;"
    a = db2(s)
    admins = []
    for admin in a:
        admins.append(admin[0])
    print(admins)

    thumbs_up = '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16')
    thumbs_down = '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16')
    middle_finger = '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16')
    check = '\u2714'
    ex = '\u274c'

    p = f"SELECT userid, payment_status, payment_status_dh FROM bowl_payment where season = {season};"
    payments = db2(p)
    payment_list = []
    payment_list_dh = []
    for payment_user in payments:
        if payment_user[1]:
            payment_list.append(payment_user[0])
        if payment_user[2]:
            payment_list_dh.append(payment_user[0])

    display_list = []
    for user in bowl_users:
        if user == 113:
            if user in payment_list:
                display_list.append((user, bowl_users[user], check, thumbs_down))
            else:
                display_list.append((user, bowl_users[user], middle_finger, thumbs_down))
        elif user not in payment_list and user not in payment_list_dh:
            display_list.append((user, bowl_users[user], ex, thumbs_down))
        elif user in payment_list_dh:
            display_list.append((user, bowl_users[user], check, thumbs_up))
        else:
            display_list.append((user, bowl_users[user], check, thumbs_down))

    # print("before {}".format(display_list))

    # if sort_method == 'user':
    #     display_list.sort(key=lambda x:x[1].upper())
    # elif sort_method == 'pay_status':
    #     display_list.sort(key=lambda x:x[2], reverse=True)

    # print("after {}".format(display_list))

    print("payment stuff")
    print(bowl_users)
    print(payment_list)
    print(payment_list_dh)
    print(display_list)

    logging.info(f"{session['username']} just hit view bowl payment status")

    return render_template("bowl_payment_status.html", display_list=display_list, user_dict=user_dict, admins=admins, total_users=len(display_list), prize_pool=prize_pool)

@bp.route("/add_bowl_user", methods=["GET", "POST"])
def add_bowl_user():
    userid = int(request.form.get('userid'))

    s = "UPDATE users SET is_bowl_user = 1 WHERE userid = %s;"
    db2(s, (userid,))

    return redirect(url_for('pickem.bowl_payment_status'))

@bp.route("/bowl_mark_paid", methods=["GET", "POST"])
def bowl_mark_paid():
    userid = int(request.form.get("userid"))
    paid = request.form.get("paid")
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

    return redirect(url_for('pickem.bowl_payment_status'))

@bp.route("/bowl_mark_paid_dh", methods=["GET", "POST"])
def bowl_mark_paid_dh():
    userid = int(request.form.get("userid"))
    paid = request.form.get("paid_dh")
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

    return redirect(url_for('pickem.bowl_payment_status'))

# 'threes' dice game
@bp.route("/threes", methods=["GET", "POST"])
def threes():
    return render_template("threes.html")

@bp.route("/select_pickem_games", methods=["GET", "POST"])
def select_pickem_games():
    season = 2021
    # first get the list of games from db
    game_list = get_pickem_games(season)

    for game in game_list:
        if request.form.get(str(game)):
            pick = request.form.get(str(game))
            p = "INSERT INTO pickem.userpicks (userid, season, gameid, pick, datetime) VALUES (%s, %s, %s, %s, convert_tz(now(), '-00:00', '-05:00'));"
            db2(p, (session['userid'], season, game, pick))

    tiebreak = request.form.get('tb')
    print("tbtiebreaktb!!")
    print(tiebreak)
    if tiebreak != None and len(tiebreak) != 0:
        t = "INSERT INTO pickem.tiebreak (season, userid, tiebreak, datetime) values (%s, %s, %s, convert_tz(now(), '-00:00', '-05:00'));"
        db2(t, (season, session['userid'], tiebreak))

    logging.info("{} just selected picks".format(session["username"]))

    return redirect(url_for('pickem.pickem_all_picks'))

@bp.route("/pickem_game_list", methods=["GET", "POST"])
@login_required
def pickem_game_list():
    # if not logged in, error out (it'll crash if not)
    if not session['userid']:
        return apology("Please log in first.  This page still under construction and requires a successful login")

    # season hardcoded for now - will store in db set by admin
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

    print("pickem game list tie breaks {}".format(tb))

    if len(tb) != 0:
        user_picks['tb'] = tb[0][0]
    else:
        user_picks['tb'] = ''

    print(user_picks)

    return render_template("pickem_game_list.html", game_dict=game_dict, game_list=game_list, user_picks=user_picks)

@bp.route("/pickem_all_picks", methods=["GET", "POST"])
@login_required
def pickem_all_picks():
    season = 2021

    # see who is eliminated
    g = "SELECT max(gameid) FROM pickem.pickem_scores;"
    max_game = db2(g)[0][0]
    if max_game:
        games_left = 13 - max_game
    else:
        games_left = 13
        max_game = 0
    print("max game {}".format(max_game))
    eliminated_list = []


    # first get all active/locked games (you can only show locked games to others)
    game_dict = get_pickem_games(season, True)
    game_list = get_pickem_games(season) # first column heading - gameid
    game_details = [] # 2nd column heading with fav/spread/dog
    games_locked = []
    for game in game_list:
        if game_dict[game].spread != 0:
            game_details.append("{} {} {}".format(game_dict[game].fav, game_dict[game].spread, game_dict[game].dog))
            if game_dict[game].locked == 1:
                games_locked.append(game)
        else:
            game_details.append("TBD")
            games_locked.append(game)

    class User:
        def __init__(self, userid):
            d = {}  # initialize user with 13 empty picks
            for n in range(1,14):
                d[n] = ''

            self.userid = userid
            self.picks = d  # gameid:pick
            self.win_count = 0
            self.max_wins = 13  # will make this configurable.. may change down the road

    # get all the user picks, eventually change unlocked picks to "hidden" if still open
    # p = "SELECT DISTINCT p.userid, p.gameid, p.pick FROM pickem.userpicks p INNER JOIN (SELECT userid, gameid, MAX(pickid) as maxid FROM pickem.userpicks GROUP BY gameid) gp ON p.gameid = gp.gameid AND p.pickid = gp.maxid"
    p = "SELECT pickid, userid, gameid, pick from pickem.userpicks order by pickid desc;"
    all_picks = db2(p)

    user_pick_list = []  # only used for deduping picks
    user_picks = {} # dictionary of user objects
    user_picks_unplayed_list = []  # only used for deduping
    user_picks_unplayed = {} # dictionary of non played games used for elimination analysis
    current_user = session['userid']

    u = "SELECT userid, username FROM users;"
    usernames = dict(db2(u))

    for pick in all_picks:
        if pick[1] in usernames:
            username = usernames[pick[1]]
        else:
            username = '*****DELETE'
        if game_dict[pick[2]].locked == 1 or current_user == pick[1]:
            if (pick[1], pick[2]) not in user_pick_list:   # then this is the latest pick for that game for this user
                user_pick_list.append((pick[1], pick[2]))  # make sure the rest skip ovr this then
                if username not in user_picks:              # first pick for this user
                    user_picks[username] = User(pick[1])           # so create a user object
                    user_picks[username].picks[pick[2]] = pick[3]       # and set it's first pick
                else:
                    user_picks[username].picks[pick[2]] = pick[3]       # obj already exists, add new game and it's pick
            if (pick[1], pick[2]) not in user_picks_unplayed_list:  # make sure latest pick for user
                user_picks_unplayed_list.append((pick[1], pick[2]))
                if username not in user_picks_unplayed and pick[2] > max_game and game_dict[pick[2]].locked == 1:  # locked but unplayed game, add to dict for elimination check
                    user_picks_unplayed[username] = [pick[3]]
                elif pick[2] > max_game and game_dict[pick[2]].locked == 1:
                    user_picks_unplayed[username].append(pick[3])

        else: # add them, but hidden
            if (pick[1], pick[2]) not in user_pick_list:   # then this is the latest pick for that game for this user
                user_pick_list.append((pick[1], pick[2]))  # make sure the rest skip ovr this then
                if username not in user_picks:              # first pick for this user
                    user_picks[username] = User(pick[1])           # so create a user object
                    user_picks[username].picks[pick[2]] = "hidden"      # and set it's first pick
                else:
                    user_picks[username].picks[pick[2]] = "hidden"      # obj already exists, add new game and it's pick

    print("userpicks unplayed {}".format(user_picks_unplayed))

    # add pickem users who haven't selected any picks yet - for tracking
    uid = "SELECT userid FROM users WHERE is_pickem_user = 1"
    empty_users = db2(uid)

    # create empty User objects for them
    print("empty users {}".format(empty_users))
    if len(empty_users) > 0:
        for userid in empty_users:
            if usernames[userid[0]] not in user_picks:
                user_picks[usernames[userid[0]]] = User(userid) # create user object with no picks

    t = "SELECT userid, tiebreak FROM pickem.tiebreak WHERE season = %s ORDER BY tiebreak_id DESC;"
    tbs= db2(t, (season,))
    tb_dict = {}  # userid:tiebreak

    for tb in tbs:
        username = usernames[tb[0]]
        if game_dict[13].locked == 1 or current_user == tb[0]:
            if username not in tb_dict:
                tb_dict[username] = tb[1]
        else:
            if username not in tb_dict:
                tb_dict[username] = 'hidden'

    # p = "SELECT * FROM pickem.pickem_payment;"
    # payment_status = dict(db2(p))
    thumbs_up = '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16')
    thumbs_down = '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16')
    middle_finger = '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16')
    check = '\u2714'
    ex = '\u274c'

    max_wins = 0  # this is the most someone has NOW
    max_win_users = []  # and who has that amount NOW
    second_best_users = [] # will check top 2 scores

    for user in user_picks:
        no_pick_count = 0
        # add win totals to user object
        for game in user_picks[user].picks:
            if game_dict[game].winner.upper() == user_picks[user].picks[game] and user_picks[user].picks[game] != '':
                user_picks[user].win_count += 1
            elif user_picks[user].picks[game] == 'x':
                no_pick_count += 1

        if user_picks[user].win_count > max_wins:
            max_wins = user_picks[user].win_count
            if len(max_win_users) > 0:
                second_best_users = max_win_users  # swap out max to second
            max_win_users = [user]

        elif user_picks[user].win_count == max_wins:
            max_win_users.append(user)

        elif user_picks[user].win_count == max_wins -1:
            second_best_users.append(user)

        # eliminated?
        user_picks[user].max_wins = user_picks[user].win_count + games_left - no_pick_count

    for user in user_picks:
        # how far behind?
        wins_behind = max_wins - user_picks[user].win_count
        diff = games_left - wins_behind # if number of matching picks with leader > diff - eliminated

        # see who's eliminated...
        if user_picks[user].max_wins < max_wins:  # easy - you can't possibly catch the leader
            eliminated_list.append(user)

        elif max_game == 13 and game_dict[13].locked == 1:  # locked sb picks - trumped?
            if max_wins - user_picks[user].max_wins == 1:
                for leader in max_win_users:
                    if user_picks[leader].picks[13] == user_picks[user].picks[13]:
                        eliminated_list.append(user)  # can't catch them

        elif max_game == 12 and game_dict[12].locked == 1:  # we've locked conf picks - see who may get trumped
            if max_wins - user_picks[user].max_wins == 3:  # you need to be completely opposite all leaders
                for leader in max_win_users:
                    if user_picks[leader].picks[11] == user_picks[user].picks[11] or user_picks[leader].picks[12] == user_picks[user].picks[12]:
                        eliminated_list.append(user)  # can't catch them... needed both opposite
            elif max_wins - user_picks[user].max_wins == 2: # you need at least 1 diff
                for leader in max_win_users:
                    if user_picks[leader].picks[11] == user_picks[user].picks[11] and user_picks[leader].picks[12] == user_picks[user].picks[12]:
                        eliminated_list.append(user)  # needed at least 1 diff

        else:
            for leader in max_win_users:
                if len(user_picks_unplayed) > 0:
                    match = 0
                    for p in user_picks_unplayed[leader]:
                        if p in user_picks_unplayed[user]:
                            match += 1
                    if match > diff:  # you need your win differential to be greater than matching picks, otherwise see ya!
                        eliminated_list.append(user)

            for runnerup in second_best_users:
                if len(user_picks_unplayed) > 0:
                    match = 0
                    for p in user_picks_unplayed[runnerup]:
                        if p in user_picks_unplayed[user]:
                            match += 1
                    if match > diff + 1:  # comparing against 2nd best here, so 1 higher
                        eliminated_list.append(user)


    winner = []
    tie_break_log = []
    if game_dict[13].winner != "TBD":  # someone won the SB, figure out who won the pool
        s = "SELECT fav_score, dog_score FROM pickem.pickem_scores WHERE gameid = 13 ORDER BY score_id DESC;"
        score = db2(s)
        print("maxwinuser{}".format(max_win_users))
        print(score)

        if len(max_win_users) == 1:  #only one winner - easy
            winner.append(max_win_users[0])
        elif len(max_win_users) > 1:  # do some tie breaking
            total_score = score[0][0] + score[0][1]
            closest_score = 1000
            closest_users = []
            for user in max_win_users:
                print("user {}'s tiebreak of {} is {} away from the total score of {}".format(user, tb_dict[user], abs(tb_dict[user] - total_score), total_score))
                tb_log = "{}'s tiebreak of {} is {} away from the total score of {}".format(user, tb_dict[user], abs(tb_dict[user] - total_score), total_score)
                if abs(tb_dict[user] - total_score) < closest_score:
                    closest_score = abs(tb_dict[user] - total_score)
                    closest_users = [user]
                    tie_break_log.insert(0, tb_log)  # want this tb to display first always, as it's potentially the winner
                elif abs(tb_dict[user] - total_score) == closest_score:
                    closest_users.append(user)
                    tie_break_log.append(tb_log)
                else:
                    tie_break_log.append(tb_log) # not closest user, but still will display this result

            if len(closest_users) == 1:  #one winner
                winner.append(closest_users[0])

            else:
                for w in closest_users:
                    winner.append(w)

        else:
            print("something went very wrong figuring out who won")

    winning_user = '{} Playoff Pickem Winner'.format(season)
    if len(winner) > 1:
        winning_user += 's: '
        for w in winner:
            winning_user += w + ' and '
        winning_user = winning_user[:-5]
    elif len(winner) == 1:
        winning_user += ': {}'.format(winner[0])
    else:
        winning_user = ''

    crown = '\uD83C\uDFC6'.encode('utf-16', 'surrogatepass').decode('utf-16')

    sorted_user_picks = sorted(user_picks.items(), key=lambda x: x[1].win_count, reverse=True)
    user_picks_dict = dict(sorted_user_picks)

    logging.info("{} just ran all_picks".format(session["username"]))

    eliminated_list.append('jzhao8')
    eliminated_list.append('GC1')
    eliminated_list.append('Algo_O')
    eliminated_list.append('rgimbel')
    print("eliminated list: {}".format(eliminated_list))

    return render_template("pickem_all_picks.html", game_details=game_details, user_picks=user_picks_dict, game_dict=game_dict, current_username=session['username'], tb_dict=tb_dict, winning_user=winning_user, tie_break_log=tie_break_log, winner=winner, crown=crown, eliminated_list=eliminated_list)

@bp.route("/ncaab_games", methods=["GET", "POST"])
def ncaab_games():
    ncaab_games = get_ncaab_games()

    events = []
    scores = []

    for event in ncaab_games['events']:
        events.append((event['id'], event['date'], event['shortName']))

        for competition in event['competitions']:
            for competitor in competition['competitors']:
                scores.append((competitor['team']['abbreviation'], competitor['score']))

    return render_template("ncaab_games.html", events=events, scores=scores)

@bp.route("/enter_pickem_scores", methods=["GET", "POST"])
def enter_pickem_scores():

    if request.method == "POST":
        fav_score = request.form.get('fav')
        dog_score = request.form.get('dog')
        gameid = request.form.get('gameid')

        s = "INSERT INTO pickem.pickem_scores (gameid, fav_score, dog_score) values (%s, %s, %s);"
        db2(s, (int(gameid), int(fav_score), int(dog_score)))

    return render_template("enter_pickem_scores.html")

@bp.route("/pickem_admin", methods=["GET", "POST"])
def pickem_admin():
    season = 2021

    game_name_list = ["WC 1", "WC 2", "WC 3", "WC 4", "WC 5", "WC 6", "DIV 7", "DIV 8", "DIV 9", "DIV 10", "CONF 11", "CONF 12", "Super Bowl"]
    game_group_list = ["WC-Sat", "WC-Sun", "DIV-Sat", "DIV-Sun", "CONF-NFC", "CONF-AFC", "Super Bowl"]
    return render_template("pickem_admin.html", game_name_list=game_name_list, game_group_list=game_group_list, season=season)

@bp.route("/lock_pickem_game", methods=["GET", "POST"])
def lock_pickem_game():
    if request.form.get('game_name'):
        game_name = request.form.get('game_name')
    else:
        return apology("what game you locking??")
    if request.form.get('lock'):
        lock = int(request.form.get('lock'))
    else:
        return apology("lock or unlock?  which is it??")

    games_dict = {"WC-Sat" : (1,2,3), "WC-Sun": (4,5,6), "DIV-Sat" : (7,8), "DIV-Sun" : (9,10), "CONF-NFC" : (11,), "CONF-AFC" : (12,), "Super Bowl" : (13,)}
    game_tup = (lock, ) + games_dict[game_name]

    param_string = ''
    for _ in range(len(games_dict[game_name])):
        param_string += '%s, '
    param_string = param_string[:-2]  # get rid of ", "

    s = "UPDATE pickem.games SET locked = %s WHERE gameid in ({});".format(param_string)
    db2(s, game_tup)
    print("setting game {} lock status to {}".format(game_name, lock))

    # set anyone who hasn't picked to 'x'
    # 1. what is the first current game, and last game from last period?
    #    - so gamedict gamename [0] and gamename [0]-1... if gamename [0] is not 1 (first period)
    # 2. get full list of users with picks in last round
    #    - if had last round and no pick this round, make x
    picks = "nothin yet"
    current_game = games_dict[game_name][0]
    if current_game != 1 and lock == 1:
        last_game = current_game - 1
        s = "SELECT userid, gameid, pick FROM pickem.userpicks WHERE gameid in ({}, {}) ORDER BY pickid DESC;".format(last_game, current_game)
        picks = db2(s)

        user_dict = {}
        for user in picks:
            if user[0] not in user_dict:
                user_dict[user[0]] = {user[1] : user[2]}
            elif user[1] not in user_dict[user[0]]:  # do not overwrite if multiple picks for a game, only use the first (really last) as we sorted by pickid desc
                user_dict[user[0]][user[1]] = user[2]

        print(user_dict)

        x_list = []
        for u in user_dict:
            if current_game not in user_dict[u]:
                x_list.append(u)

        print(x_list)

        print(picks)

        for x in x_list:
            u = "INSERT INTO pickem.userpicks (userid, season, gameid, pick) VALUES ({}, 2021, {}, 'x');".format(x, current_game)
            db2(u)

    return redirect(url_for('pickem.pickem_admin'))


@bp.route("/create_pickem_game", methods=["GET", "POST"])
def create_pickem_game():
    if request.form.get('season'):
        season = request.form.get('season')
    else:
        return apology("what season?  2021?")
    if request.form.get('game_name'):
        game_name = request.form.get('game_name')
    else:
        return apology("pick a game name please")
    if request.form.get('fav'):
        fav = request.form.get('fav')
    else:
        return apology("missing favorite")
    if request.form.get('spread'):
        spread = request.form.get('spread')
    else:
        return apology("missing spread")
    if request.form.get('dog'):
        dog = request.form.get('dog')
    else:
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

    return redirect(url_for('pickem.pickem_all_picks'))


@bp.route("/pickem_payment_status", methods=["GET", "POST"])
def pickem_payment_status():
    season = 2021
    # find users that have a pickem entry
    u = "SELECT DISTINCT up.userid, u.username FROM pickem.userpicks up LEFT JOIN users u ON up.userid = u.userid WHERE up.season = {};".format(season)
    pickem_users = dict(db2(u))

    p = "SELECT * FROM pickem.pickem_payment;"
    payment_dict = dict(db2(p))

    # add users who are in but haven't made picks yet
    uid = "SELECT userid, username FROM users WHERE is_pickem_user = 1"
    empty_users = db2(uid)
    if len(empty_users) > 0:
        for user in empty_users:
            pickem_users[user[0]] = user[1]

    entry = 50
    prize_pool = 50 * len(pickem_users)

    # find list of admins who can update status
    s = "SELECT userid FROM users WHERE is_admin = 1;"
    a = db2(s)
    admins = []
    for admin in a:
        admins.append(admin[0])
    print(admins)

    thumbs_up = '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16')
    thumbs_down = '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16')
    middle_finger = '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16')
    check = '\u2714'
    ex = '\u274c'


    display_list = []
    for user in pickem_users:
        if user not in payment_dict:
            display_list.append((user, pickem_users[user], ex))
        else:
            if user == 113:
                display_list.append((user, pickem_users[user], middle_finger))
            elif payment_dict[user] == True:
                display_list.append((user, pickem_users[user], check))
            else:
                display_list.append((user, pickem_users[user], ex))
    print("payment stuff")
    print(pickem_users)
    print(payment_dict)
    print(display_list)

    return render_template("pickem_payment_status.html", display_list=display_list, admins=admins, total_users=len(display_list), prize_pool=prize_pool)

@bp.route("/pickem_mark_paid", methods=["GET", "POST"])
def pickem_mark_paid():
    userid = int(request.form.get("userid"))
    paid = request.form.get("paid")

    s = "SELECT * FROM pickem.pickem_payment;"
    paid_status = dict(db2(s))

    if userid not in paid_status:
        s = "INSERT INTO pickem.pickem_payment (userid, payment_status) VALUES (%s, %s);"
        db2(s, (userid, True))
    else:
        s = "UPDATE pickem.pickem_payment SET payment_status = %s WHERE userid = %s;"
        db2(s, (True, userid))

    return redirect(url_for('pickem.pickem_payment_status'))

@bp.route("/pickem_enable_user", methods=["GET", "POST"])
def pickem_enable_user():
    userid = int(request.form.get("userid"))

    s = "UPDATE users SET is_pickem_user = 1 WHERE userid = %s"
    db2(s, (userid,))

    return redirect(url_for('pickem.pickem_admin'))

@bp.route("/pickem_rules", methods=["GET", "POST"])
def pickem_rules():
    return render_template("pickem_rules.html")
