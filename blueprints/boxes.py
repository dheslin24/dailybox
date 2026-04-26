from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, Markup, send_file, current_app
from db_accessor.db_accessor import db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required, allowed_file
from services.box_service import (box_string, assign_xy, assign_numbers, count_avail,
                                   payout_calc, calc_winner, find_winning_user, check_box_limit,
                                   create_new_game, get_games, find_winning_box, sanity_checks,
                                   find_touching_boxes, activate_game, get_user_games)
from services.espn_client import get_espn_scores, get_espn_score_by_qtr, get_espn_summary_single_game, get_espn_every_min_scores
from email_helper import send_email
from werkzeug.utils import secure_filename
from collections import defaultdict
from datetime import datetime, timedelta
import json
import random
import os
import logging

bp = Blueprint('boxes', __name__)


@bp.route("/remove_image", methods=["POST", "GET"])
@login_required
def remove_image():
    userid = request.args['userid']
    remove_query = "UPDATE users SET image = NULL WHERE userid = %s;"
    db2(remove_query, (userid,))

    return redirect(url_for('auth.user_details'))


@bp.route('/upload_file', methods=["POST", "GET"])
@login_required
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            user = int(request.form.get('user'))
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

            user_query = "UPDATE users SET image = %s WHERE userid = %s;"
            db2(user_query, (file.filename, user))

            return redirect(url_for('auth.user_details', name=filename))

    userid = request.args['userid']
    return '''
    <!doctype html>
    <title>Upload new image to display in BOX selection</title>
    <h1>Upload new File</h1>
    <p>All of your boxes will display this image if you upload</p>
    <p>Only .png, .jpg, .jpeg, .gif filetypes are supported</p>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
      <input type=hidden value=''' + userid + ''' name=user>
    </form>
    '''


@bp.route("/start_game", methods=["POST", "GET"])
def start_game():
    boxid = request.form.get('boxid')
    error = activate_game(boxid)
    if error:
        return apology(error)
    return redirect(url_for("boxes.display_box", boxid=boxid))


@bp.route("/init_box_db")
@login_required
def init_box_db():
    b = ['box' + str(x) + " INT," for x in range(100)]
    s = "CREATE TABLE IF NOT EXISTS boxes(boxid INT AUTO_INCREMENT PRIMARY KEY, active, box_type, box_name, fee int, "
    for _ in b:
        s += _
    s = s[:-1]
    s += ")"
    db2(s)

    return redirect(url_for("auth.index"))

@bp.route("/create_game", methods=["POST", "GET"])
def create_game():
    fee = request.form.get('fee')
    espn_id = request.form.get('espn_id')
    if not request.form.get('box_name'):
        max_box = db2("SELECT max(boxid) from boxes;")[0][0]
        box_name = "db" + str(max_box + 1)
    else:
        box_name = request.form.get('box_name')

    box_type = request.form.get('box_type')
    pay_type = request.form.get('pay_type')
    # create string of c = columns to update
    home = request.form.get('home')
    away = request.form.get('away')
    create_new_game(box_type, pay_type, fee, box_name, home, away, espn_id)

    return redirect(url_for("auth.index"))

@bp.route("/gobble_games", methods=["POST", "GET"])
def gobble_games():
    boxid_1 = request.form.get('boxid_1')
    boxid_2 = request.form.get('boxid_2')
    boxid_3 = request.form.get('boxid_3')
    logging.info("gobble_games: %s %s %s", boxid_1, boxid_2, boxid_3)
    max_g = db2("SELECT max(gobbler_id) from boxes;")[0][0]
    g_id = max_g + 1
    db2("UPDATE boxes SET gobbler_id = %s WHERE boxid IN (%s, %s, %s);", (g_id, int(boxid_1), int(boxid_2), int(boxid_3)))

    return redirect(url_for("admin.admin_summary"))


@bp.route("/my_games", methods=["POST", "GET"])
@login_required
def my_games():
    show_active = request.form.get("active")
    game_list, completed_game_list, available = get_user_games(session['userid'])
    total = len(game_list)
    hover_text_1 = "Click on cell in this column to re-label"
    hover_text_2 = "box to something other than your username"

    if show_active == 'True' or show_active is None:
        return render_template("my_games.html", game_list=game_list, available=available,
                               total=total, hover_text_1=hover_text_1, hover_text_2=hover_text_2)
    else:
        return render_template("my_completed_games.html", game_list=completed_game_list)

@bp.route("/api/my_games", methods=["GET"])
@login_required
def api_my_games():
    game_list, completed_game_list, available = get_user_games(session['userid'])
    return jsonify({
        'total': len(game_list),
        'active_games': [
            {'boxid': g[0], 'box_name': g[1], 'box_num': g[2], 'alias': g[3],
             'fee': g[4], 'pay_type': g[5], 'home_num': g[6], 'away_num': g[7]}
            for g in game_list
        ],
        'completed_games': [
            {'boxid': g[0], 'box_type': g[1], 'box_name': g[2], 'box_num': g[3],
             'alias': g[4], 'fee': g[5], 'pay_type': g[6], 'winner': g[7]}
            for g in completed_game_list
        ],
        'available': {str(k): v for k, v in available.items()},
    })

@bp.route("/completed_games")
@login_required
def completed_games():
    #game_list_d = get_games(1, 0)
    game_list_c = get_games([2,3], 0)
    #game_list = game_list_d + game_list_c
    game_list_pre = game_list_c
    game_list_pre.sort(key=lambda x: x[0])

    # dedupe - if corrections were made in score entry a game can have multiple
    game_list = []
    seen = set()
    for game in game_list_pre:
        if game[0] not in seen:  # unique game, mark as seen and add to gl
            game_list.append(game)
            seen.add(game[0])
        else:  # seen this one already.. replace it with a new one
            del game_list[-1]
            game_list.append(game)


    return render_template("completed_games.html", game_list = game_list)

@bp.route("/completed_private_games")
@login_required
def completed_private_games():
    #game_list_d = get_games(1, 0)
    game_list_c = get_games([4], 0)
    #game_list = game_list_d + game_list_c
    game_list_pre = game_list_c
    game_list_pre.sort(key=lambda x: x[0])

    # dedupe - if corrections were made in score entry a game can have multiple
    game_list = []
    seen = set()
    for game in game_list_pre:
        if game[0] not in seen:  # unique game, mark as seen and add to gl
            game_list.append(game)
            seen.add(game[0])
        else:  # seen this one already.. replace it with a new one
            del game_list[-1]
            game_list.append(game)


    return render_template("completed_private_games.html", game_list = game_list)

@bp.route("/api/completed_games", methods=["GET"])
@login_required
def api_completed_games():
    game_list_pre = get_games([2, 3], 0)
    game_list_pre.sort(key=lambda x: x[0])
    game_list = []
    seen = set()
    for game in game_list_pre:
        if game[0] not in seen:
            game_list.append(game)
            seen.add(game[0])
        else:
            del game_list[-1]
            game_list.append(game)
    return jsonify({'games': [
        {'boxid': g[0], 'box_name': g[1], 'fee': g[2], 'pay_type': g[3], 'winner': g[4]}
        for g in game_list
    ]})

@bp.route("/api/game_list", methods=["GET"])
def api_game_list():
    games = get_games([1])
    return jsonify({'games': [
        {'boxid': g[0], 'box_name': g[1], 'fee': g[2], 'pay_type': g[3], 'available': g[4]}
        for g in games
    ]})

@bp.route("/game_list")
def game_list():
    game_list = get_games([1])

    return render_template("game_list.html", game_list = game_list)

@bp.route("/custom_game_list")
@login_required
def custom_game_list():
    game_list = get_games([2,3]) # pass a list of box types..

    no_active_games_string = ''
    if not game_list:
        no_active_games_string = 'No Active Games'

    # sorted(game_list, key=itemgetter(0))
    game_list.sort(key=lambda x: x[0])

    return render_template("custom_game_list.html", game_list = game_list, no_active_games_string = no_active_games_string)

@bp.route("/private_game_list")
@login_required
def private_game_list():
    game_list = get_games([4])  # takes a list of box_types.. only 4 for private here

    no_active_games_string = ''
    if not game_list:
        no_active_games_string = 'You have no active private games'
    else:
        game_list.sort(key=lambda x: x[0])

    return render_template("private_game_list.html", game_list = game_list, no_active_games_string = no_active_games_string)

@bp.route("/private_pswd", methods=["POST", "GET"])
@login_required
def private_pswd():
    if request.method == "POST":
        pswd = request.form.get('priv_password')

        # first check if this is valid#
        p = "SELECT boxid FROM privatepass WHERE pswd = %s;"
        box = db2(p, (pswd, ))
        if box:
            s = "INSERT INTO privategames (userid, boxid, paid) values (%s, %s, 0) ON DUPLICATE KEY UPDATE userid = %s, boxid=%s;"
            db2(s, (session['userid'], box[0][0], session['userid'], box[0][0]))

        else:
            display_error = "Invalid code - please try again or contact the game admin."
            return render_template("private_pswd.html", display_error=display_error)
        # for now
        return redirect("private_game_list")


    else:
        return render_template("private_pswd.html")


@bp.route("/display_box", methods=["GET", "POST"])
@login_required
def display_box():
    if request.method == "POST":
        boxid = request.form.get('boxid')
    else:
        boxid = request.args['boxid']


    logging.info("user {} just ran display_box for boxid {}".format(session['username'], boxid))
    box = list(db2("SELECT * FROM boxes where boxid = %s;", (int(boxid),)))[0]
    box_type = box[2]
    if box_type == 4:
        private_game_payment_link = "Click here for this game's payment status"
    else:
        private_game_payment_link = ""

    box_name = box[3]
    fee = box[4]
    ptype = box[5]
    for p in PAY_TYPE_ID:
        if ptype == PAY_TYPE_ID[p]:
            pay_type = p  # human form of a pay type
    gobbler_id = box[6]
    espn_id = box[7]
    payout = payout_calc(ptype, fee)
    rev_payout = 0
    #current_user = Session['userid']
    # if ptype != 2 and ptype != 5:
    if ptype == PAY_TYPE_ID['four_qtr']:
        final_payout = fee * 60
    elif ptype == PAY_TYPE_ID['single']:
        final_payout = fee * 100
    elif ptype == PAY_TYPE_ID['ten_man']:
        final_payout = fee * 10
    elif ptype == PAY_TYPE_ID['satellite']:
        final_payout = "Satellite"
    else:
        final_payout = None

    if box_type != BOX_TYPE_ID['dailybox']:
        teams = db2("SELECT home, away FROM teams WHERE boxid = %s;", (int(boxid),))
        home = teams[0][0]
        away = teams[0][1]
    else:
        home = 'XXX'
        away = 'YYY'

    game_status = get_espn_summary_single_game(espn_id)
    live_quarter = int(game_status['quarter'])
    status = game_status['game_status']
    game_clock = game_status['game_clock']
    kickoff_time = game_status['kickoff_time']
    team_scores = get_espn_score_by_qtr(espn_id) # team_scpre[abbr] = current_score, qtr_scores, name, nickname, logo

    logging.debug("team scores: %s", list(team_scores.keys()))
    game_dict = get_espn_score_by_qtr(espn_id)

    away_team = {}
    for i in range(10):
        away_team[str(i)] = ''
    if len(away) == 3:
        away_team['2'] = team_scores[away].get('logo', "TBD")
        away_team['3'] = away[0]
        away_team['4'] = away[1]
        away_team['5'] = away[2]
        away_team['6'] = team_scores[away].get('logo', "TBD")
    else:
        away_team['3'] = team_scores[away].get('logo', "TBD")
        away_team['4'] = away[0]
        away_team['5'] = away[1]
        away_team['6'] = team_scores[away].get('logo', "TBD")

    logging.debug("paytype: %s", pay_type)
    # check for final scores only
    if pay_type == 'single' or pay_type == 'ten_man' or pay_type == 'sattelite':

        if 'current_score' in team_scores[home]:
            home_digit = team_scores[home]['current_score'][-1]
            away_digit = team_scores[away]['current_score'][-1]
        else:
            home_digit = str(0)
            away_digit = str(0)

        # DH 11/25/22 - changing..
        # team_scores_digit = get_espn_scores(espnid = '')['team']
        # #game_dict = get_espn_score_by_qtr(espn_id)
        # print(f"team scores: {team_scores_digit}")
        # print(f"home and away: {home} {away}")
        # home_digit = str(0)
        # away_digit = str(0)
        # if home in team_scores_digit and away in team_scores_digit:
        #     print(f"home: {home}:{team_scores_digit[home]} away: {away}:{team_scores_digit[away]}")
        #     home_digit = team_scores_digit[home][-1]
        #     away_digit = team_scores_digit[away][-1]
        #     print(home_digit, away_digit)
        # else:
        #     print("one team is most likely on bye")

    elif pay_type == 'four_qtr':
        home_digit = str(0)
        away_digit = str(0)
        #game_dict = get_espn_score_by_qtr(espn_id)

    # create a dict of userid:username
    user_dict = dict(db2("SELECT userid, username FROM users;"))

    alias_query = "SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"
    alias_dict = dict(db2(alias_query))

    grid = []
    box_num = 0
    row = 0
    avail = 0
    alias = None
    current_user_box_count = 0
    # create a list (grid) of 10 lists (rows) of 10 tuples (boxes)
    for _ in range(10):
        l = []
        for box_userid in box[8 + row : 18 + row]:  # BOX DB CHANGE if boxes schema changes
            alias = None
            if box_userid == 1 or box_userid == 0:
                name = 'Available '
                avail += 1
            else:
                if box_userid in alias_dict:
                    alias = alias_dict[box_userid]
                name = user_dict[box_userid]

            l.append((box_num, name, box_userid, alias))
            box_num += 1
            if box_userid == session.get("userid"):
                current_user_box_count += 1
        grid.append(l)
        row += 10

    images = dict(db2("SELECT userid, image FROM users WHERE image IS NOT NULL;"))

    xy_string = "SELECT x, y FROM boxnums WHERE boxid = %s;"
    if avail != 0 or len(db2(xy_string, (int(boxid),))) == 0:
        num_selection = "Row/Column numbers will be randomly generated after all participants have paid."
        x = {}
        for n in range(10):
            x[str(n)] = '?'
        y = {}
        for n in range(10):
            y[str(n)] = '?'

        if ptype == 5:
            final_payout == fee * 10

    # gets row/column numbers and finds winner
    else:
        num_selection = ''
        xy = db2(xy_string, (int(boxid),))[0]
        x = json.loads(xy[0])
        y = json.loads(xy[1])

        logging.debug("xy: %s -- %s", x, y)

        winners = calc_winner(boxid)
        # no winners and not an every score (paytype = 3 or 8)
        logging.debug("paytype/winners: %s %s", ptype, winners)
        if len(winners) == 0 and (ptype != PAY_TYPE_ID['every_score'] and ptype != PAY_TYPE_ID['four_qtr'] and ptype != PAY_TYPE_ID['every_minute']):

            for col in x:
                if str(x[col]) == home_digit:
                    curr_win_col = int(col)
                    break
            for row in y:
                if str(y[row]) == away_digit:
                    curr_win_row = int(row)
                    break

            curr_winner_user = grid[curr_win_row][curr_win_col][1]
            #curr_winner = ['Current', 'WINNER', curr_winner_user]
            curr_winner = Markup(f'Current</br>WINNER</br>{curr_winner_user}') if status != 'Final' else Markup(f'WINNER</br>{curr_winner_user}')

            #f"this one here: {grid[curr_win_row][curr_win_col][0]}")
            curr_winner_boxnum = grid[curr_win_row][curr_win_col][0]
            curr_winner_userid = grid[curr_win_row][curr_win_col][2]
            grid[curr_win_row][curr_win_col] = (curr_winner_boxnum, curr_winner, curr_winner_userid)

            return render_template("display_box.html", current_user_box_count=current_user_box_count, grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection, team_scores=game_dict, private_game_payment_link=private_game_payment_link, images=images)
            # return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y, home=home, away=away)

        logging.debug("paytype %s winners %s", ptype, winners)
        if (ptype == PAY_TYPE_ID['single'] or ptype == PAY_TYPE_ID['ten_man'] or ptype == PAY_TYPE_ID['satellite'] or ptype == PAY_TYPE_ID['ten_man_final_reverse']) and len(winners) == 2:
            if ptype == PAY_TYPE_ID['single']:
                final_payment = fee * 100
            elif ptype == PAY_TYPE_ID['satellite']:
                final_payment = "Satellite"
            else:
                final_payment = fee * 10
            for item in x:
                if x[item] == int(winners[0]):
                    x_winner = int(item)
            for item in y:
                if y[item] == int(winners[1]):
                    y_winner = int(item)
            winning_username = grid[y_winner][x_winner][1]
            winning_userid = grid[y_winner][x_winner][2]
            winning_boxnum = int(str(y_winner) + str(x_winner))
            winner = Markup('WINNER</br>')
            grid[y_winner][x_winner] = (winning_boxnum, winner + winning_username, winning_userid)
            if (ptype == PAY_TYPE_ID['single'] or ptype == PAY_TYPE_ID['ten_man'] or ptype == PAY_TYPE_ID['satellite']) and len(winners) != 2:
                return apology("something went wrong with winner calculations")

        if ptype == PAY_TYPE_ID['ten_man_final_reverse']:
            pass # TODO NUTX - add reverse final here
            for item in x:
                if x[item] == int(winners[0]):  # x column == y winner
                    x_winner = int(item)
            for item in y:
                if y[item] == int(winners[1]):
                    y_winner = int(item)
            # rev_winning_username = grid[x_winner][y_winner][1]
            # rev_winning_boxnum = int(str(x_winner) + str(y_winner))
            # rev_winner = Markup('REVERSE</br>WINNER</br>')
            # grid[x_winner][y_winner] = (rev_winning_boxnum, rev_winner + rev_winning_username)
            grid[3][1] = (31, Markup('REVERSE</br>WINNER</br>')+'toddw26')

        if winners and ptype == PAY_TYPE_ID['four_qtr']:
            quarter = len(winners) // 2
            logging.debug("winners=%s quarter=%s live_quarter=%s status=%s", len(winners), quarter, live_quarter, game_status)
            final_payment = '' +  str(fee * 10) + ' / ' + str(fee * 20) + ' / ' + str(fee * 10) + ' / ' + str(fee * 60)

            for item in x:
                xq = 0
                if quarter > xq:
                    xq += 1
                    if x[item] == int(winners[0]):
                        q1_x_winner = int(item)

                if quarter > xq:
                    xq += 1
                    if x[item] == int(winners[2]):
                        q2_x_winner = int(item)

                if quarter > xq:
                    xq += 1
                    if x[item] == int(winners[4]):
                        q3_x_winner = int(item)

                if quarter > xq:
                    if x[item] == int(winners[6]):
                        q4_x_winner = int(item)

            for item in y:
                yq = 0
                if quarter > yq:
                    yq += 1
                    if y[item] == int(winners[1]):
                        q1_y_winner = int(item)

                if quarter > yq:
                    yq += 1
                    if y[item] == int(winners[3]):
                        q2_y_winner = int(item)

                if quarter > yq:
                    yq += 1
                    if y[item] == int(winners[5]):
                        q3_y_winner = int(item)

                if quarter > yq:
                    if y[item] == int(winners[7]):
                        q4_y_winner = int(item)

            if quarter >= 1:
                q1_winning_username = grid[q1_y_winner][q1_x_winner][1]
                q1_winning_userid = grid[q1_y_winner][q1_x_winner][2]
                q1_winning_boxnum = int(str(q1_y_winner) + str(q1_x_winner))
                if live_quarter > 1 or status == 'Final':
                    q1_winner = Markup('Q1 WINNER</br>')
                else:
                    q1_winner = Markup('WINNING Q1</br>')
                grid[q1_y_winner][q1_x_winner] = (q1_winning_boxnum, q1_winner + q1_winning_username, q1_winning_userid)

            if quarter >= 2:
                q2_winning_username = grid[q2_y_winner][q2_x_winner][1]
                q2_winning_userid = grid[q2_y_winner][q2_x_winner][2]
                q2_winning_boxnum = int(str(q2_y_winner) + str(q2_x_winner))
                if live_quarter > 2 or status == 'Halftime' or status == 'Final':
                    q2_winner = Markup('Q2 WINNER</br>')
                else:
                    q2_winner = Markup('WINNING Q2</br>')
                grid[q2_y_winner][q2_x_winner] = (q2_winning_boxnum, q2_winner + q2_winning_username, q2_winning_userid)

            if quarter >= 3:
                q3_winning_username = grid[q3_y_winner][q3_x_winner][1]
                q3_winning_userid = grid[q3_y_winner][q3_x_winner][2]
                q3_winning_boxnum = int(str(q3_y_winner) + str(q3_x_winner))
                if live_quarter > 3 or status == 'Final':
                    q3_winner = Markup('Q3 WINNER</br>')
                else:
                    q3_winner = Markup('WINNING Q3</br>')
                grid[q3_y_winner][q3_x_winner] = (q3_winning_boxnum, q3_winner + q3_winning_username, q3_winning_userid)

            if quarter == 4:
                q4_winning_username = grid[q4_y_winner][q4_x_winner][1]
                q4_winning_userid = grid[q4_y_winner][q4_x_winner][2]
                q4_winning_boxnum = int(str(q4_y_winner) + str(q4_x_winner))
                if status == 'Final':
                    q4_winner = Markup('Q4 WINNER</br>')
                else:
                    q4_winner = Markup('WINNING Q4</br>')
                grid[q4_y_winner][q4_x_winner] = (q4_winning_boxnum, q4_winner + q4_winning_username, q4_winning_userid)


        if ptype == PAY_TYPE_ID['every_score']:
            winners = db2("SELECT score_num, winning_box FROM everyscore where boxid = %s;", (int(boxid),))
            max_score_num = 1
            final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10)
            winner_dict = {}

            if len(winners) != 0:
                for w in winners:
                    if w[0] >= max_score_num and w[0] < 100:
                        max_score_num = w[0]
                if max_score_num <= 24:
                    final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10) - (fee * 8)
                    rev_payout = fee * 10
                elif max_score_num == 25:
                    final_payout = fee * 10
                    rev_payout = (fee * 10) - (fee * 3)
                elif max_score_num == 26:
                    final_payout = fee * 10
                    rev_payout = (fee * 10) - (fee * 6)
                else:
                    final_payout = fee * 10
                    rev_payout = fee

                for winning_box in winners:
                    if winning_box[0] < 100:  # regular winners
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += (fee * 3)
                        else:
                            winner_dict[winning_box[1]] = (fee * 3)
                    elif winning_box[0] == 101:  # touching reverse final
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += fee
                        else:
                            winner_dict[winning_box[1]] = fee
                    elif winning_box[0] == 201:  #touching final
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += fee
                        else:
                            winner_dict[winning_box[1]] = fee
                    elif winning_box[0] == 100 and max_score_num <= 24:  # reverse final winner max payout 1000
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += (fee * 10)
                        else:
                            winner_dict[winning_box[1]] = (fee * 10)
                    elif winning_box[0] == 100 and max_score_num <= 26 and max_score_num >24:  # 700, 400, 100....
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += 1000 - ((max_score_num - 24) * (fee * 3))
                        else:
                            winner_dict[winning_box[1]] = 1000 - ((max_score_num - 24) * (fee * 3))
                    elif winning_box[0] == 100 and max_score_num <= 27:  #100
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += fee
                        else:
                            winner_dict[winning_box[1]] = fee
                    elif winning_box[0] == 200:  # final winner
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += final_payout
                        else:
                            winner_dict[winning_box[1]] = final_payout


                for winning_box in winner_dict:
                    cash = winner_dict[winning_box]
                    if int(winning_box) > 9:
                        x_win = str(winning_box)[-1:]
                        y_win = str(winning_box)[:1]
                    elif int(winning_box) < 10:
                        x_win = str(winning_box)[-1:]
                        y_win = '0'

                    winner_username = grid[int(y_win)][int(x_win)][1]
                    winner_userid = grid[int(y_win)][int(x_win)][2]
                    winner_markup = Markup('WINNER</br>{}</br>{}'.format(winner_username[:10], cash))
                    grid[int(y_win)][int(x_win)] = (grid[int(y_win)][int(x_win)][0], winner_markup, winner_username, winner_userid)

                    logging.debug("winner_dict: %s", winner_dict)
            else:
                final_payout = (fee * 100) - (fee * 10) - (fee * 3)  # total pool - reverse - 0/0

            #winner_dict = {}
            scores = db2(
                "SELECT e.score_num, e.x_score, e.y_score, e.score_type, u.username, e.winning_box FROM everyscore e LEFT JOIN users u ON e.winner = u.userid where e.boxid = %s order by e.score_num, e.score_id;",
                (int(boxid),)
            )

            # final every score (paytype =3)
            # return render_template("display_box.html", grid=grid, boxid=boxid, box_name=box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, winner_dict=winner_dict, scores=scores, rev_payout=rev_payout, team_scores=team_scores, images=images, private_game_payment_link=private_game_payment_link,box_type=box_type)
            return render_template(
                "display_box.html",
                grid=grid,
                boxid=boxid,
                box_name=box_name,
                fee=fee,
                avail=avail,
                payout=payout,
                final_payout=final_payout,
                x=x, y=y,
                home=home, away=away, away_team=away_team,
                winner_dict=winner_dict,
                scores=scores,
                rev_payout=rev_payout,
                team_scores=team_scores,
                images=images,
                private_game_payment_link=private_game_payment_link,
                box_type=box_type,
                pay_type=ptype,
                current_user_box_count=current_user_box_count
            )

        if ptype == PAY_TYPE_ID["every_minute"]:
            """
            winner = {
                "away_score": score.get("away_score"),
                "home_score": score.get("home_score"),
                "winning_minutes": winning_minutes,
                "win_type": ["minute", "final", "reverse"]

            grid = [(box_num, name(user), userid, alias)]  <-- name is overloaded to include winning totals for display purposes
            }
            """
            winners = get_espn_every_min_scores(espn_id)
            if not winners:
                if x['0'] != '?':
                    for col in x:
                        if str(x[col]) == '0':
                            win_col = int(col)
                    for row in y:
                        if str(y[row]) == '0':
                            win_row = int(row)

                    winner_boxnum = grid[win_row][win_col][0]
                    winner_userid = grid[win_row][win_col][2]
                    winner_username = user_dict[winner_userid]

                    win_detail = (0, 0, 0, f"Pre-Game 0/0 Winner {str(int(fee * 1.5))}", winner_username, winner_boxnum)
                    minute_winner_list = [win_detail]

                    winner_markup = Markup(f'WINNER</br>{winner_username}</br>{int(fee * 1.5)}')
                    grid[win_row][win_col] = (winner_boxnum, winner_markup, winner_userid)

                # return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection, team_scores=team_scores, images=images, private_game_payment_link=private_game_payment_link, box_type=box_type, game_dict=game_dict)
                return render_template(
                    "display_box.html",
                    grid=grid,
                    boxid=boxid,
                    box_name = box_name,
                    fee=fee,
                    avail=avail,
                    payout=payout,
                    final_payout=final_payout,
                    x=x, y=y,
                    home=home, away=away, away_team=away_team,
                    num_selection=num_selection,
                    team_scores=team_scores,
                    scores=minute_winner_list,
                    images=images,
                    private_game_payment_link=private_game_payment_link,
                    box_type=box_type,
                    game_dict=game_dict,
                    pay_type=ptype,
                    current_user_box_count=current_user_box_count,
                    game_clock=game_clock
                )
            box_winners = defaultdict(int)  # {boxnum : minutes}
            reverse_payout = fee * 5
            final_payout = fee * 5
            minute = 0
            minute_winner_list = []  # (minute, home_num, away_num, description, userid, winning box)
            def _update_minute_winner_list(win_details, n):
                new_min = minute
                new_start = win_details[1:3]
                new_end = win_details[4:]

                for _ in range(n):
                    new_desc = (f"MINUTE {new_min}    {str(int(fee * 1.5))}", )
                    minute_winner_list.append((new_min,) + new_start + new_desc + new_end)
                    new_min += 1

            for winner in winners:
                logging.debug("win: %s", winner)
                away_num = str(winner["away_score"])[-1]
                home_num = str(winner["home_score"])[-1]
                winning_minutes = winner["winning_minutes"]
                win_type = winner["type"]

                for col in x:
                    if str(x[col]) == home_num:
                        win_col = int(col)
                for row in y:
                    if str(y[row]) == away_num:
                        win_row = int(row)

                # print(f"DH GRID!!!!!!!!!! {grid}")

                winner_boxnum = grid[win_row][win_col][0]
                winner_userid = grid[win_row][win_col][2]
                winner_username = user_dict[winner_userid]

                if win_type == "minute":
                    win_detail = (minute, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} {str(minute)} {str(int(fee * 1.5))}", winner_username, winner_boxnum)
                    _update_minute_winner_list(win_detail, winning_minutes)
                    minute += winning_minutes
                    box_winners[winner_boxnum] += int(winning_minutes * (fee * 1.5))
                    winner_markup = Markup(f'WINNER</br>{user_dict[winner_userid]}</br>{box_winners[winner_boxnum]}') # TODO figure out $ value
                elif win_type == "final":
                    win_detail = (200, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} {str(fee * 5)}", winner_username, winner_boxnum)
                    minute_winner_list.append(win_detail)
                    box_winners[winner_boxnum] += final_payout
                    winner_markup = Markup(f'WINNER</br>FINAL</br>{user_dict[winner_userid]}</br>{box_winners[winner_boxnum]}')
                elif win_type == "reverse":
                    box_winners[winner_boxnum] += reverse_payout
                    win_detail = (100, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} {str(fee * 5)}", winner_username, winner_boxnum)
                    minute_winner_list.append(win_detail)
                    winner_markup = Markup(f'WINNER</br>REVERSE</br>{user_dict[winner_userid]}</br>{box_winners[winner_boxnum]}')
                elif win_type == "OT FINAL":
                    box_winners[winner_boxnum] += reverse_payout
                    win_detail = (200, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} {str(fee * 5)}", winner_username, winner_boxnum)
                    minute_winner_list.append(win_detail)
                    winner_markup = Markup(f'WINNER</br>REVERSE</br>{user_dict[winner_userid]}</br>{box_winners[winner_boxnum]}')
                elif win_type == "OT FINAL REVERSE":
                    box_winners[winner_boxnum] += reverse_payout
                    win_detail = (100, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} {str(fee * 5)}", winner_username, winner_boxnum)
                    minute_winner_list.append(win_detail)
                    winner_markup = Markup(f'WINNER</br>REVERSE</br>{user_dict[winner_userid]}</br>{box_winners[winner_boxnum]}')
                grid[win_row][win_col] = (winner_boxnum, winner_markup, winner_userid)


            # return render_template("display_box.html", grid=grid, boxid=boxid, box_name=box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, scores=minute_winner_list ,team_scores=team_scores, images=images, private_game_payment_link=private_game_payment_link,box_type=box_type)
            return render_template(
                "display_box.html",
                grid=grid,
                boxid=boxid,
                box_name=box_name,
                fee=fee,
                avail=avail,
                payout=payout,
                final_payout=final_payout,
                x=x, y=y,
                home=home, away=away, away_team=away_team,
                scores=minute_winner_list,
                team_scores=team_scores,
                images=images,
                private_game_payment_link=private_game_payment_link,
                box_type=box_type,
                pay_type=ptype,
                current_user_box_count=current_user_box_count,
                game_clock=game_clock
            )

    if box_type == BOX_TYPE_ID['dailybox']:
        sf = ['' for x in range(10)]
        final_payout = ''
        return render_template("display_box.html", current_user_box_count=current_user_box_count, grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, sf=sf, home=home, away=away, away_team=away_team)

    elif pay_type == 'four_qtr':
        return render_template("display_box.html", current_user_box_count=current_user_box_count, grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection, team_scores=game_dict, game_clock=game_clock, kickoff_time=kickoff_time, images=images, private_game_payment_link=private_game_payment_link, box_type=box_type)

    # display box for all except every score, 4qtr, or dailybox
    else:
        final_payout = 'Current Final Payout: ' + str(final_payout)
        return render_template("display_box.html", current_user_box_count=current_user_box_count, grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection, team_scores=team_scores, images=images, private_game_payment_link=private_game_payment_link, box_type=box_type, game_dict=game_dict)


@bp.route("/select_box", methods=["GET", "POST"])
@login_required
def select_box():
    boxid = request.form.get('boxid')
    box_attr = db2("SELECT box_type, pay_type FROM boxes WHERE boxid = %s;", (int(boxid),))[0]
    box_type = box_attr[0]
    pay_type = box_attr[1]
    box_list = [] # the list of eventual boxes to get this user id
    boxes = db2("SELECT {} FROM boxes WHERE boxid = %s;".format(box_string()), (int(boxid),))[0]
    rand_list = []
    index = 0
    user_box_count = 0

    # create a list of available boxes by index
    for box in boxes:
        if box == 0 or box == 1:
            rand_list.append(index)
        if (box_type == BOX_TYPE_ID['nutcracker'] or pay_type == PAY_TYPE_ID['ten_man'] or pay_type == PAY_TYPE_ID['satellite']) and box == session['userid']:
            user_box_count += 1
        index += 1

    # randomly pick n boxes from available list above
    if request.form.get('rand') != None:
        rand = request.form.get('rand')
        if int(rand) > len(rand_list):
            return apology("Really??  You have requested {} boxes, but only {} available.".format(int(rand), len(rand_list)))
        else:
            rand_indexes = random.sample(range(len(rand_list)), int(rand))
            for i in rand_indexes:
                box_list.append(rand_list[i])

    # select all 10 boxes in a column
    elif request.form.get('column') != None:
        column = request.form.get('column') # will be 0-9
        for n in range((0 + int(column)), 100, 10):
            if n in rand_list:
                box_list.append(n)

    elif request.form.get('row') != None:
        row = request.form.get('row')  # will be 0-9
        for n in range((int(row) * 10), (int(row) * 10) + 10):
            if n in rand_list:
                box_list.append(n)

    # else just the one the user picked
    else:
        box_num = int(request.form.get('box_num'))
        if box_num in rand_list:
            # 10-man validation
            if (box_type == BOX_TYPE_ID['nutcracker'] or pay_type == PAY_TYPE_ID['ten_man']) and user_box_count >= 10:
                return apology("Really??  This is a 10-man.  10 boxes max.  100/10 = 10")
            elif pay_type == PAY_TYPE_ID['satellite'] and check_box_limit(session['userid']):
                return apology("Really??  You lost count - you're out of boxes.  Double check with TW to make sure he set you up correctly.")

            elif pay_type == PAY_TYPE_ID['ten_man_final_reverse'] and check_box_limit(session['userid']):
                return apology("Really??  Clearly you lost count.  You didn't win that many satellite boxes.")

            else:
                box_list.append(box_num)
        elif boxes[box_num] == session['userid']:
            # code to undo pick
            # first - if rand_list len == 0, game has started, can't undo
            if len(rand_list) == 0:
                return apology("Really??  numbers were drawn - can't undo now - too late!!")
            if box_type != BOX_TYPE_ID['nutcracker']:
                db2("UPDATE boxes SET box{}= 1 WHERE boxid = %s;".format(int(box_num)), (int(boxid),))
                logging.info("user {} just unselected box {} in boxid {}".format(session['username'], box_num, boxid))
            else:
                box_list.append(box_num) #still append, to eventually set back to 1 on all gobble boxes

        else:
            box_owner = db2("SELECT username FROM users WHERE userid = %s;", (boxes[box_num],))[0][0]
            return apology("Really??  Did you not see {} already has this box?".format(box_owner))


    # check balance of user first - then subtract fee
    check = db2("SELECT fee, box_type FROM boxes WHERE boxid = %s;", (int(boxid),))
    fee = check[0][0]
    balance = db2("SELECT balance FROM users WHERE userid = %s;", (session['userid'],))[0][0]

    if user_box_count + len(box_list) > 10 and (box_type == BOX_TYPE_ID['nutcracker'] or pay_type == PAY_TYPE_ID['ten_man']):
        return apology("Really?  This is a 10-man.  10 boxes max.  100/10=10")

    elif box_type == BOX_TYPE_ID['nutcracker']:
        gobbler_id = db2("SELECT gobbler_id FROM boxes WHERE boxid = %s;", (int(boxid),))[0][0]
        for b in box_list:
            if boxes[b] == session['userid']:
                db2("UPDATE boxes SET box{}=1 WHERE gobbler_id = %s;".format(int(b)), (gobbler_id,))
            else:
                db2("UPDATE boxes SET box{}=%s WHERE gobbler_id = %s;".format(int(b)), (session['userid'], gobbler_id))

        return redirect(url_for("boxes.display_box", boxid=boxid))


    else:
        for b in box_list:
            # assign box to user
            db2("UPDATE boxes SET box{}=%s WHERE boxid = %s;".format(int(b)), (session['userid'], int(boxid)))
            logging.info("user {} just picked box {} in boxid {}".format(session['username'], b, boxid))

        return redirect(url_for("boxes.display_box", boxid=boxid))

@bp.route("/es_payout_details", methods=["GET"])
def es_payout_details():
    #fee = 100
    fee = int(request.args['fee'])
    payouts = []
    for i in range(1,31):
        score = []
        score.append(i)
        if i <= 27:
            score.append(3 * fee * i)
        else:
            score.append(3 * fee * 27)
        score.append(str(fee) + 'x4')
        score.append(str(fee) + 'x4')
        if i <= 24:
            score.append(fee * 10)
            score.append(((fee * 100) - (fee * 8) - (fee * 10)) - (fee * 3 * i))
        elif i <=26:
            score.append((fee * 10) - ((fee * 3) * (i - 24)))
            score.append(fee * 10)
        else:
            score.append(fee)
            score.append(fee * 10)

        payouts.append(score)

    logging.info("{} just selected ran payout_details".format(session["username"]))

    return render_template('es_payout_details.html', payouts=payouts)


@bp.route("/enter_every_score", methods=["GET", "POST"])
@login_required
def enter_every_score():
    if request.method == "POST":
        # first check if used buttons, most common
        if request.form.get("HOME_BUTTON"):
            home_button = int(request.form.get("HOME_BUTTON"))
            score_list = db2("SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;")[0]
            score_num = score_list[0] + 1
            home_score = home_button + score_list[1]
            away_score = score_list[2]
        elif request.form.get("AWAY_BUTTON"):
            away_button = int(request.form.get("AWAY_BUTTON"))
            score_list = db2("SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;")[0]
            score_num = score_list[0] + 1
            home_score = score_list[1]
            away_score = away_button + score_list[2]
        else:
            if not request.form.get("home") or not request.form.get("away"):
                return apology("need 2 scores")
            score_num = int(request.form.get("score_num"))
            home_score = int(request.form.get("home"))
            away_score = int(request.form.get("away"))

        boxid_list = db2("SELECT boxid FROM boxes WHERE pay_type = 3 and active = 1;")
        if len(boxid_list) == 0:
            return apology("there are no active every score games")

        # get home/away teams for buttons
        # this assumes there will only ever be 1 active everyscore pool so all boxids have same home/away team
        teams = db2("SELECT home, away FROM teams WHERE boxid = %s;", (boxid_list[0][0],))[0]
        home_team = teams[0]
        away_team = teams[1]
        logging.info(("{} just entered a new score: {}-{} for home and {}-{} for away".format(session["username"], home_team, home_score, away_team, away_score)))

        box_list = []
        for entry in boxid_list:
            boxid = entry[0]
            box_list.append(boxid)
            win_box = find_winning_box(boxid, home_score, away_score)
            boxnum = win_box[0]
            winner = win_box[1]
            fee = db2("SELECT fee FROM boxes WHERE boxid = %s;", (int(boxid),))[0][0]

            db2(
                "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, %s, %s, %s, %s, %s, %s);",
                (str(boxid), str(score_num), f"Score Change {fee * 3}", str(home_score), str(away_score), str(winner), str(boxnum))
            )

        ### run sanity checks ###
        check_result_list = sanity_checks(box_list)

        scores = db2("SELECT e.boxid, e.score_id, e.score_num, e.x_score, e.y_score, e.score_type, e.winning_box, u.username, u.first_name, u.last_name FROM everyscore e LEFT JOIN users u ON e.winner = u.userid INNER JOIN boxes b ON b.boxid = e.boxid where b.active = 1 and b.pay_type = 3 order by e.boxid, e.score_num, e.score_id;")

        return render_template("enter_every_score.html", scores=scores, box_list=box_list, check_result_list=check_result_list, home_team=home_team, away_team=away_team)


    else:
        scores = db2("SELECT e.boxid, e.score_id, e.score_num, e.x_score, e.y_score, e.score_type, e.winning_box, u.username, u.first_name, u.last_name FROM everyscore e LEFT JOIN users u ON e.winner = u.userid INNER JOIN boxes b ON b.boxid = e.boxid where b.active = 1 and b.pay_type = 3 order by e.boxid, e.score_num, e.score_id;")
        boxid_list = db2("SELECT boxid FROM boxes WHERE pay_type = 3 and active = 1;")
        if len(boxid_list) == 0:
            return apology("there are no active every score games")
        # get home/away teams for buttons
        # this assumes there will only ever be 1 active everyscore pool so all boxids have same home/away team
        teams = db2("SELECT home, away FROM teams WHERE boxid = %s;", (boxid_list[0][0],))[0]
        home_team = teams[0]
        away_team = teams[1]
        logging.info(f"home team: {home_team}, away team: {away_team}")

        box_list = []
        for boxid in boxid_list:
            box_list.append(boxid[0])
        check_result_list = sanity_checks(box_list)

        return render_template("enter_every_score.html", scores=scores, box_list=box_list, check_result_list=check_result_list, home_team=home_team, away_team=away_team)

@bp.route("/delete_score", methods=["POST", "GET"])
@login_required
def delete_score():
    score_id = request.form.get('score_id')
    db2("DELETE FROM everyscore WHERE score_id = %s;", (int(score_id),))
    return redirect(url_for('boxes.enter_every_score'))

@bp.route("/current_winners/<boxid>", methods=["POST", "GET"])
@login_required
def current_winners(boxid):
    if request.method == "POST":
        return redirect(url_for("boxes.display_box", boxid))
    else:
        scores = db2("SELECT e.score_type, e.x_score, e.y_score, e.winning_box, u.username FROM everyscore e LEFT JOIN users u ON e.winner = u.userid WHERE boxid = %s order by e.score_num;", (int(boxid),))

        return render_template("current_winners.html", scores=scores, boxid=boxid)

@bp.route("/end_game", methods=["POST", "GET"])
@login_required
def end_game():
    if request.method == "POST":
        boxid = request.form.get('boxid')
        home_score = request.form.get('home')
        away_score = request.form.get('away')

        all_boxnum = db2("SELECT fee, {} FROM boxes WHERE boxid = %s;".format(box_string()), (int(boxid),))[0]

        fee = all_boxnum[0]

        max_score_num = db2("SELECT max(score_num) FROM everyscore WHERE boxid = %s;", (int(boxid),))[0][0]
        if max_score_num <= 23:
            rev_cash = fee * 10
            fin_cash = ((24 - max_score_num) * (fee * 3)) + 1000
        elif max_score_num == 24:
            rev_cash = fee * 10
            fin_cash = fee * 10
        elif max_score_num == 25:
            rev_cash = (fee * 10) - (fee * 3)
            fin_cash = fee * 10
        elif max_score_num == 26:
            rev_cash = (fee * 10) - (fee * 6)
            fin_cash = fee * 10
        else:
            rev_cash = fee
            fin_cash = fee * 10

        box_counter = 0
        boxnum_dict = {}
        fee = all_boxnum[0]
        for userid in all_boxnum[1:]:
            boxnum_dict[box_counter] = userid
            box_counter += 1

        logging.debug("boxnum_dict: %s", boxnum_dict)

        # find the reverse winner - running function with home/away backward
        rev_box = find_winning_box(boxid, away_score, home_score)
        rev_boxnum = rev_box[0]
        rev_winner = rev_box[1]
        # all reverse score_num are 100
        db2(
            "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, '100', %s, %s, %s, %s, %s);",
            (str(boxid), f"Reverse Final {rev_cash}", str(away_score), str(home_score), str(rev_winner), str(rev_boxnum))
        )

        # reverse touch scores are 101
        rev_boxes = find_touching_boxes(int(rev_boxnum))
        for box in rev_boxes:
            db2("INSERT INTO everyscore (boxid, score_num, score_type, winner, winning_box) VALUES (%s, 101, %s, %s, %s);",
                (boxid, f"Touch Reverse {fee}", boxnum_dict[box], box))

        # find final winner
        final_box = find_winning_box(boxid, home_score, away_score)
        final_boxnum = final_box[0]
        final_winner = final_box[1]
        # all final score_num are 200
        db2(
            "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, '200', %s, %s, %s, %s, %s);",
            (str(boxid), f"Final Score {fin_cash}", str(home_score), str(away_score), str(final_winner), str(final_boxnum))
        )

        # final touch scores are 201
        fin_boxes = find_touching_boxes(int(final_boxnum))
        for box in fin_boxes:
            db2("INSERT INTO everyscore (boxid, score_num, score_type, winner, winning_box) VALUES (%s, 201, %s, %s, %s);",
                (boxid, f"Touch Final {fee}", boxnum_dict[box], box))

        return redirect(url_for("boxes.enter_every_score"))
    else:
        return render_template("end_game.html")

@bp.route("/end_games", methods=["POST", "GET"])
@login_required
def end_games():
    if request.method == "POST":
        # what games am i ending?
        g = "SELECT boxid FROM boxes WHERE active = 1 and pay_type = 3;"
        games = db2(g)

        for box in games:
            boxid = box[0]
            all_boxnum = db2("SELECT fee, {} FROM boxes WHERE boxid = %s;".format(box_string()), (int(boxid),))[0]

            fee = all_boxnum[0]

            max_score_num = db2("SELECT max(score_num) FROM everyscore WHERE boxid = %s;", (int(boxid),))[0][0]

            score = db2("SELECT x_score, y_score FROM everyscore WHERE score_num = %s and boxid = %s;", (max_score_num, int(boxid)))
            home_score = score[0][0]
            away_score = score[0][1]

            if max_score_num <= 23:
                rev_cash = fee * 10
                fin_cash = ((24 - max_score_num) * (fee * 3)) + (fee * 10)
            elif max_score_num == 24:
                rev_cash = fee * 10
                fin_cash = fee * 10
            elif max_score_num == 25:
                rev_cash = (fee * 10) - (fee * 3)
                fin_cash = fee * 10
            elif max_score_num == 26:
                rev_cash = (fee * 10) - (fee * 6)
                fin_cash = fee * 10
            else:
                rev_cash = fee
                fin_cash = fee * 10

            box_counter = 0
            boxnum_dict = {}
            fee = all_boxnum[0]
            for userid in all_boxnum[1:]:
                boxnum_dict[box_counter] = userid
                box_counter += 1

            logging.debug("boxnum_dict: %s", boxnum_dict)

            # find the reverse winner - running function with home/away backward
            rev_box = find_winning_box(boxid, away_score, home_score)
            rev_boxnum = rev_box[0]
            rev_winner = rev_box[1]
            # all reverse score_num are 100
            db2(
                "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, '100', %s, %s, %s, %s, %s);",
                (str(boxid), f"Reverse Final {rev_cash}", str(away_score), str(home_score), str(rev_winner), str(rev_boxnum))
            )

            # reverse touch scores are 101
            rev_boxes = find_touching_boxes(int(rev_boxnum))
            for box in rev_boxes:
                db2("INSERT INTO everyscore (boxid, score_num, score_type, winner, winning_box) VALUES (%s, 101, %s, %s, %s);",
                    (boxid, f"Touch Reverse {fee}", boxnum_dict[box], box))

            # find final winner
            final_box = find_winning_box(boxid, home_score, away_score)
            final_boxnum = final_box[0]
            final_winner = final_box[1]
            # all final score_num are 200
            db2(
                "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, '200', %s, %s, %s, %s, %s);",
                (str(boxid), f"Final Score {fin_cash}", str(home_score), str(away_score), str(final_winner), str(final_boxnum))
            )

            # final touch scores are 201
            fin_boxes = find_touching_boxes(int(final_boxnum))
            for box in fin_boxes:
                db2("INSERT INTO everyscore (boxid, score_num, score_type, winner, winning_box) VALUES (%s, 201, %s, %s, %s);",
                    (boxid, f"Touch Final {fee}", boxnum_dict[box], box))

        return redirect(url_for("boxes.enter_every_score"))
    else:
        return render_template("end_game.html")


@bp.route("/enter_custom_scores", methods=["GET", "POST"])
@login_required
def enter_custom_scores():

    send_email(None, None, "DH Testing", None, None)

    if request.method == "POST":
        if not request.form.get("boxid"):
            return apology("boxid required")
        if not request.form.get("x4") or not request.form.get("y4"):
            return apology("at a minimum, need 2 final scores")
        boxid = int(request.form.get("boxid"))
        if request.form.get("x1") == '':
            x1 = None
        else:
            x1 = int(request.form.get("x1"))
        if request.form.get("y1") == '':
            y1 = None
        else:
            y1 = int(request.form.get("y1"))
        if request.form.get("x2") == '':
            x2 = None
        else:
            x2 = int(request.form.get("x2"))
        if request.form.get("y2") == '':
            y2 = None
        else:
            y2 = int(request.form.get("y2"))
        if request.form.get("x3") == '':
            x3 = None
        else:
            x3 = int(request.form.get("x3"))
        if request.form.get("y3") == '':
            y3 = None
        else:
            y3 = int(request.form.get("y3"))

        x4 = int(request.form.get("x4"))
        y4 = int(request.form.get("y4"))

        if count_avail(boxid) != 0:
            return apology("Game not full yet - can't enter scores")

        else:
            value_list = [('boxid',boxid), ('x1',x1), ('y1',y1), ('x2',x2), ('y2',y2), ('x3',x3), ('y3',y3), ('x4',x4), ('y4',y4)]
            c = ""
            v = ""
            for item in value_list:
                if item[1] != None:
                    c += str(item[0]) + ", "
                    v += "'" + str(item[1]) + "', "
            c = c[:-2] # chop off last ', '
            v = v[:-2]

            db2("INSERT INTO scores({}) VALUES({});".format(c, v))
            # and... make game inactive in db
            db2("UPDATE boxes SET active = 0 WHERE boxid = %s;", (int(boxid),))
            # and... update the winner in db
            pay_type = db2("SELECT pay_type FROM boxes WHERE boxid = %s;", (int(boxid),))[0][0]
            if pay_type == 2 or pay_type == 5 or pay_type == 6:
                db2("UPDATE scores SET winner = %s WHERE boxid = %s;", (find_winning_user(boxid)[0], int(boxid)))
            elif pay_type == 1:
                # will save in db as json string of quarter:winner
                wl = find_winning_user(boxid)
                j = '{'
                qtr = 1
                for q in wl:
                    j += '"q{}":{}, '.format(qtr,q)
                    qtr += 1
                j = j[:-2] # chop last ", "
                j += '}'
                db2("UPDATE scores SET winner = %s WHERE boxid = %s;", (j, int(boxid)))

            elif pay_type == 7:
                wl = find_winning_user(boxid)[0]
                db2("UPDATE scores SET winner = %s WHERE boxid = %s;", (wl, int(boxid)))

            return redirect(url_for("admin.admin_summary"))

    else:
        return render_template("enter_custom_scores.html")


# test for displaying/parsing live scores from espn API
@bp.route("/live_scores", methods=["GET", "POST"])
def live_scores():

    response = get_espn_scores(False)
    game_dict = response['game']
    team_dict = response['team']
    logging.debug("teamdict keys: %s", list(team_dict.keys()))

    # get users picks
    picks = db2("SELECT espnid, pick FROM bowlpicks WHERE userid = %s ORDER BY pick_id ASC;", (session['userid'],))
    now = datetime.utcnow() - timedelta(hours=5)

    return render_template("live_scores.html", game_dict = game_dict, picks=dict(picks), now=now)

@bp.route("/payment_status", methods=["GET", "POST"])
@login_required
def payment_status():

    if request.method == "POST":
        sort_method = request.form.get('sort_method')
    else:
        sort_method = request.args['sort_method']
        priv = request.args['priv']

    users_list = db2("SELECT userid, username FROM users WHERE active = 1;")

    # get actual names for our demanding 'admin'
    usernames = db2("SELECT userid, username, first_name, last_name FROM users;")
    user_dict = {}
    for userid, username, first_name, last_name in usernames:
        user_dict[userid] = {"username": username, "first_name": first_name, "last_name": last_name}

    paid = dict(db2("SELECT userid, amt_paid FROM users;"))
    for item in paid:
        if paid[item] == None:
            paid[item] = 0

    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string_val = ''
    for _ in box_list:
        box_string_val += _
    box_string_val = box_string_val[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 and boxid NOT IN (SELECT boxid FROM privatepass);".format(box_string_val)
    all_boxes = db2(box)
    #print(all_boxes)
    user_box_count = {}
    user_fees = {}

    alias_string = "SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"
    aliases = dict(db2(alias_string))

    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10 # these are 10-man pools
        for b in game[2:]:
            if b in aliases:
                userid = aliases[b]
            else:
                userid = b
            if userid != 0 and userid != 1:
                if userid in user_box_count.keys():
                    user_box_count[userid] += 1
                    user_fees[userid] += fee
                else:
                    user_box_count[userid] = 1
                    user_fees[userid] = fee

    thumbs_up = '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16')
    thumbs_down = '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16')
    middle_finger = '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16')
    check = '\u2714'
    ex = '\u274c'

    users = []
    emoji = {}
    for user in users_list:
        if user[0] in user_fees:
            users.append(user)
            if user[0] in [31]:
                emoji[user[0]] = middle_finger
            elif user_fees[user[0]] > paid[user[0]]:
                emoji[user[0]] = ex
            else:
                emoji[user[0]] = check

    if sort_method == 'user':
        users.sort(key=lambda x:x[1].upper())
    elif sort_method == 'pay_status':
        users.sort(key=lambda x:user_fees[x[0]] - paid[x[0]], reverse=True)

    # find list of admins who can update status
    a = db2("SELECT userid FROM users WHERE is_admin = 1;")
    admins = []
    for admin in a:
        admins.append(admin[0])

    return render_template("payment_status.html", users=users, user_dict=user_dict, sort_method=sort_method, d=user_box_count, fees=user_fees, paid=paid, admins=admins, emoji=emoji, priv=False)

@bp.route("/api/payment_status", methods=["GET"])
@login_required
def api_payment_status():
    sort_method = request.args.get('sort_method', 'user')
    users_list = db2("SELECT userid, username FROM users WHERE active = 1;")
    usernames = db2("SELECT userid, username, first_name, last_name FROM users;")
    user_dict = {u[0]: {'first_name': u[2], 'last_name': u[3]} for u in usernames}
    paid = dict(db2("SELECT userid, amt_paid FROM users;"))
    for item in paid:
        if paid[item] is None:
            paid[item] = 0
    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string_val = ''.join(box_list)[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 and boxid NOT IN (SELECT boxid FROM privatepass);".format(box_string_val)
    all_boxes = db2(box)
    aliases = dict(db2("SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"))
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type in (5, 6, 7):
            fee = fee // 10
        for b in game[2:]:
            userid = aliases.get(b, b)
            if userid not in (0, 1):
                user_box_count[userid] = user_box_count.get(userid, 0) + 1
                user_fees[userid] = user_fees.get(userid, 0) + fee
    check, ex, middle_finger = '✔', '❌', '\U0001f595'
    users = []
    emoji = {}
    for uid, username in users_list:
        if uid in user_fees:
            users.append({'userid': uid, 'username': username})
            if uid in [31]:
                emoji[uid] = middle_finger
            elif user_fees[uid] > paid[uid]:
                emoji[uid] = ex
            else:
                emoji[uid] = check
    if sort_method == 'user':
        users.sort(key=lambda x: x['username'].upper())
    elif sort_method == 'pay_status':
        users.sort(key=lambda x: user_fees[x['userid']] - paid[x['userid']], reverse=True)
    admins = [r[0] for r in db2("SELECT userid FROM users WHERE is_admin = 1;")]
    return jsonify({
        'users': users,
        'user_details': {str(k): v for k, v in user_dict.items()},
        'box_counts': {str(k): v for k, v in user_box_count.items()},
        'fees': {str(k): v for k, v in user_fees.items()},
        'paid': {str(k): v for k, v in paid.items()},
        'emoji': {str(k): v for k, v in emoji.items()},
        'admins': admins,
        'sort_method': sort_method,
        'current_userid': session['userid'],
    })

@bp.route("/mark_paid", methods=["GET", "POST"])
def mark_paid():
    userid = int(request.form.get("userid"))
    # paid = request.form.get("paid")
    fees = int(request.form.get("fees"))
    # amt_paid = int(request.form.get("amt_paid"))
    sort_method = request.form.get("sort_method")

    update_amt = fees

    u = "UPDATE users SET amt_paid = %s WHERE userid = %s;"
    db2(u, (update_amt, userid))

    return redirect(url_for("boxes.payment_status", sort_method=sort_method, priv=False))

@bp.route("/priv_mark_paid", methods=["GET", "POST"])
def priv_mark_paid():
    userid = int(request.form.get("userid"))
    paid = request.form.get("paid")
    if paid:
        db_paid = 1
    else:
        db_paid = 0
    sort_method = request.form.get("sort_method")
    boxid = request.form.get('boxid')

    u = "UPDATE privategames SET paid = %s WHERE userid = %s and boxid = %s;"
    db2(u, (db_paid, userid, boxid))

    return redirect(url_for("boxes.priv_payment_status", sort_method=sort_method, priv=True, boxid=boxid))


@bp.route("/priv_payment_status", methods=["POST", "GET"])
@login_required
def priv_payment_status():
    if request.method == "POST":
        sort_method = request.form.get('sort_method')
        boxid = request.form.get("boxid")

    else:
        sort_method = request.args['sort_method']
        boxid = request.args['boxid']


    s = "SELECT userid, username FROM users WHERE active = 1 and userid in (SELECT userid FROM privategames WHERE boxid = %s);"
    users_list = db2(s, (boxid, ))

    p = "SELECT userid, paid FROM privategames WHERE boxid = %s;"
    paid = dict(db2(p, (boxid, )))

    # get actual names for our demanding 'admin'
    uname_string = "SELECT userid, username, first_name, last_name FROM users;"
    usernames = db2(uname_string)
    user_dict = {}
    for userid, username, first_name, last_name in usernames:
        user_dict[userid] = {"username": username, "first_name": first_name, "last_name": last_name}

    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string_val = ''
    for _ in box_list:
        box_string_val += _
    box_string_val = box_string_val[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 and boxid = {};".format(box_string_val, boxid)
    all_boxes = db2(box)
    #print(all_boxes)
    user_box_count = {}
    user_fees = {}

    alias_string = "SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"
    aliases = dict(db2(alias_string))

    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10
        for b in game[2:]:
            if b in aliases:
                userid = aliases[b]
            else:
                userid = b
            if userid != 0 and userid != 1:
                if userid in user_box_count.keys():
                    user_box_count[userid] += 1
                    user_fees[userid] += fee
                else:
                    user_box_count[userid] = 1
                    user_fees[userid] = fee

    thumbs_up = '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16')
    thumbs_down = '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16')
    middle_finger = '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16')
    check = '\u2714'
    ex = '\u274c'

    users = []
    emoji = {}
    for user in users_list:
        if user[0] in user_fees:
            users.append(user)
            if user[0] in [67, 113, 15]:
                emoji[user[0]] = middle_finger
            elif not paid[user[0]]:
                emoji[user[0]] = ex
            else:
                paid[user[0]] = user_fees[user[0]]
                emoji[user[0]] = check

    if sort_method == 'user':
        users.sort(key=lambda x:x[1].upper())
    elif sort_method == 'pay_status':
        users.sort(key=lambda x:user_fees[x[0]] - paid[x[0]], reverse=True)

    # find list of admins who can update status
    s = "SELECT admin FROM privatepass WHERE boxid = %s;"
    a = db2(s, (boxid, ))
    admins = []
    for admin in a:
        admins.append(admin[0])
        admins.append(3) # DH superuser

    return render_template("payment_status.html", user_dict=user_dict, users=users, sort_method=sort_method, d=user_box_count, fees=user_fees, paid=paid, admins=admins, emoji=emoji, priv=True, boxid=boxid, box_type=4)
