from flask import Blueprint, flash, jsonify, redirect, request, session, current_app
from db_accessor.db_accessor import db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID
from utils import apology, login_required, allowed_file
from services.box_service import (box_string, count_avail,
                                   payout_calc, calc_winner, find_winning_user, check_box_limit,
                                   create_new_game, get_games, find_winning_box, sanity_checks,
                                   find_touching_boxes, activate_game, get_user_games)
from services.espn_client import get_espn_scores, get_espn_score_by_qtr, get_espn_summary_single_game, get_espn_every_min_scores
from werkzeug.utils import secure_filename
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

    return redirect('/app/user_details')


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

            return redirect('/app/user_details')

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
    return redirect(f'/app/display_box?boxid={boxid}')


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

    return redirect('/app/landing_page')

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

    return redirect('/app/landing_page')

@bp.route("/gobble_games", methods=["POST", "GET"])
def gobble_games():
    boxid_1 = request.form.get('boxid_1')
    boxid_2 = request.form.get('boxid_2')
    boxid_3 = request.form.get('boxid_3')
    logging.info("gobble_games: %s %s %s", boxid_1, boxid_2, boxid_3)
    max_g = db2("SELECT max(gobbler_id) from boxes;")[0][0]
    g_id = max_g + 1
    db2("UPDATE boxes SET gobbler_id = %s WHERE boxid IN (%s, %s, %s);", (g_id, int(boxid_1), int(boxid_2), int(boxid_3)))

    return redirect('/app/admin_summary')


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

@bp.route("/api/completed_private_games", methods=["GET"])
@login_required
def api_completed_private_games():
    game_list_pre = get_games([4], 0)
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

@bp.route("/api/custom_game_list", methods=["GET"])
@login_required
def api_custom_game_list():
    games = get_games([2, 3])
    games.sort(key=lambda x: x[0])
    return jsonify({
        'games': [{'boxid': g[0], 'box_name': g[1], 'fee': g[2], 'pay_type': g[3], 'available': g[4]} for g in games],
        'no_active_games_string': '' if games else 'No Active Games',
    })

@bp.route("/api/private_game_list", methods=["GET"])
@login_required
def api_private_game_list():
    games = get_games([4])
    if games:
        games.sort(key=lambda x: x[0])
    return jsonify({
        'games': [{'boxid': g[0], 'box_name': g[1], 'fee': g[2], 'pay_type': g[3], 'available': g[4]} for g in games],
        'no_active_games_string': '' if games else 'You have no active private games',
    })

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

        return redirect(f'/app/display_box?boxid={boxid}')


    else:
        for b in box_list:
            # assign box to user
            db2("UPDATE boxes SET box{}=%s WHERE boxid = %s;".format(int(b)), (session['userid'], int(boxid)))
            logging.info("user {} just picked box {} in boxid {}".format(session['username'], b, boxid))

        return redirect(f'/app/display_box?boxid={boxid}')

@bp.route("/api/es_payout_details", methods=["GET"])
@login_required
def api_es_payout_details():
    fee = int(request.args['fee'])
    payouts = []
    for i in range(1, 31):
        if i <= 27:
            es_total = 3 * fee * i
        else:
            es_total = 3 * fee * 27
        touch_rev = f'{fee}x4'
        touch_fin = f'{fee}x4'
        if i <= 24:
            rev_final = fee * 10
            final = ((fee * 100) - (fee * 8) - (fee * 10)) - (fee * 3 * i)
        elif i <= 26:
            rev_final = (fee * 10) - ((fee * 3) * (i - 24))
            final = fee * 10
        else:
            rev_final = fee
            final = fee * 10
        payouts.append({'scores': i, 'es_total': es_total, 'touch_rev': touch_rev, 'touch_fin': touch_fin, 'rev_final': rev_final, 'final': final})
    return jsonify({'fee': fee, 'payouts': payouts})

@bp.route("/api/private_pswd", methods=["POST"])
@login_required
def api_private_pswd():
    pswd = request.get_json().get('password', '')
    box = db2("SELECT boxid FROM privatepass WHERE pswd = %s;", (pswd,))
    if box:
        db2("INSERT INTO privategames (userid, boxid, paid) values (%s, %s, 0) ON DUPLICATE KEY UPDATE userid = %s, boxid=%s;",
            (session['userid'], box[0][0], session['userid'], box[0][0]))
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid code - please try again or contact the game admin.'})

@bp.route("/api/enter_every_score", methods=["GET", "POST"])
@login_required
def api_enter_every_score():
    boxid_list = db2("SELECT boxid FROM boxes WHERE pay_type = 3 and active = 1;")
    if not boxid_list:
        return jsonify({'error': 'no active every score games'}), 404
    teams = db2("SELECT home, away FROM teams WHERE boxid = %s;", (boxid_list[0][0],))[0]
    home_team, away_team = teams[0], teams[1]
    box_list = [b[0] for b in boxid_list]

    if request.method == "POST":
        data = request.get_json()
        if data.get("HOME_BUTTON"):
            last = db2("SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;")[0]
            score_num, home_score, away_score = last[0] + 1, int(data["HOME_BUTTON"]) + last[1], last[2]
        elif data.get("AWAY_BUTTON"):
            last = db2("SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;")[0]
            score_num, home_score, away_score = last[0] + 1, last[1], int(data["AWAY_BUTTON"]) + last[2]
        else:
            score_num = int(data.get("score_num"))
            home_score = int(data.get("home"))
            away_score = int(data.get("away"))
        for boxid in box_list:
            win_box = find_winning_box(boxid, home_score, away_score)
            fee = db2("SELECT fee FROM boxes WHERE boxid = %s;", (int(boxid),))[0][0]
            db2("INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES(%s, %s, %s, %s, %s, %s, %s);",
                (str(boxid), str(score_num), f"Score Change {fee * 3}", str(home_score), str(away_score), str(win_box[1]), str(win_box[0])))

    scores = db2("SELECT e.boxid, e.score_id, e.score_num, e.x_score, e.y_score, e.score_type, e.winning_box, u.username, u.first_name, u.last_name FROM everyscore e LEFT JOIN users u ON e.winner = u.userid INNER JOIN boxes b ON b.boxid = e.boxid WHERE b.active = 1 and b.pay_type = 3 ORDER BY e.boxid, e.score_num, e.score_id;")
    check_result_list = sanity_checks(box_list)
    return jsonify({
        'box_list': box_list,
        'home_team': home_team,
        'away_team': away_team,
        'check_results': list(check_result_list),
        'scores': [{'boxid': s[0], 'score_id': s[1], 'score_num': s[2], 'home': s[3], 'away': s[4],
                    'desc': s[5], 'box': s[6], 'username': s[7], 'first_name': s[8], 'last_name': s[9]} for s in scores],
    })

@bp.route("/delete_score", methods=["POST", "GET"])
@login_required
def delete_score():
    score_id = request.form.get('score_id')
    db2("DELETE FROM everyscore WHERE score_id = %s;", (int(score_id),))
    return redirect('/app/enter_every_score')

@bp.route("/api/current_winners/<boxid>", methods=["GET"])
@login_required
def api_current_winners(boxid):
    scores = db2(
        "SELECT e.score_type, e.x_score, e.y_score, e.winning_box, u.username "
        "FROM everyscore e LEFT JOIN users u ON e.winner = u.userid "
        "WHERE boxid = %s ORDER BY e.score_num;",
        (int(boxid),)
    )
    return jsonify({
        'boxid': boxid,
        'scores': [{'score_type': s[0], 'x_score': s[1], 'y_score': s[2], 'winning_box': s[3], 'winner': s[4]} for s in scores],
    })

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

        return redirect('/app/enter_every_score')
    else:
        return redirect('/app/end_game')

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

        return redirect('/app/enter_every_score')
    else:
        return redirect('/app/end_game')


@bp.route("/enter_custom_scores", methods=["GET", "POST"])
@login_required
def enter_custom_scores():

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

            return redirect('/app/admin_summary')

    else:
        return redirect('/app/enter_custom_scores')


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

    return redirect(f'/app/payment_status?sort_method={sort_method}')

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

    return redirect(f'/app/payment_status?sort_method={sort_method}&priv=True&boxid={boxid}')


@bp.route("/api/live_scores", methods=["GET"])
@login_required
def api_live_scores():
    response = get_espn_scores(False)
    game_dict = response['game']
    now = datetime.utcnow() - timedelta(hours=5)
    picks = dict(db2("SELECT espnid, pick FROM bowlpicks WHERE userid = %s ORDER BY pick_id ASC;", (session['userid'],)))
    games_json = {}
    for gid, g in sorted(game_dict.items(), key=lambda x: x[1]['datetime']):
        games_json[str(gid)] = {
            'espn_id': g['espn_id'],
            'date': g['date'],
            'datetime': g['datetime'].isoformat(),
            'venue': g.get('venue', ''),
            'competitors': g['competitors'],
            'abbreviations': g['abbreviations'],
            'line': g['line'],
            'headline': g.get('headline', ''),
            'location': g.get('location', ''),
            'status': g['status'],
            'current_winner': g.get('current_winner', ''),
        }
    return jsonify({
        'games': games_json,
        'picks': {str(k): v for k, v in picks.items()},
        'now': now.isoformat(),
    })


@bp.route("/api/display_box", methods=["GET"])
@login_required
def api_display_box():
    boxid = request.args.get('boxid')
    if not boxid:
        return jsonify({"error": "boxid required"}), 400

    box = list(db2("SELECT * FROM boxes where boxid = %s;", (int(boxid),)))[0]
    box_type = box[2]
    private_game_payment_link = "Click here for this game's payment status" if box_type == 4 else ""

    box_name = box[3]
    fee = box[4]
    ptype = box[5]
    pay_type = next(p for p in PAY_TYPE_ID if PAY_TYPE_ID[p] == ptype)
    espn_id = box[7]
    payout = payout_calc(ptype, fee)
    rev_payout = 0

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
    team_scores = get_espn_score_by_qtr(espn_id)

    team_scores_json = {}
    for abbr, ts in team_scores.items():
        team_scores_json[abbr] = {
            'current_score': ts.get('current_score', '0'),
            'qtr_scores': {str(k): v for k, v in ts.get('qtr_scores', {}).items()},
            'name': ts.get('name', ''),
            'nickname': ts.get('nickname', ''),
            'logo': ts.get('logo', ''),
        }

    if pay_type in ('single', 'ten_man', 'satellite', 'sattelite', 'ten_man_final_reverse'):
        ts_home = team_scores.get(home, {})
        ts_away = team_scores.get(away, {})
        home_digit = ts_home['current_score'][-1] if ts_home.get('current_score') else '0'
        away_digit = ts_away['current_score'][-1] if ts_away.get('current_score') else '0'
    else:
        home_digit = '0'
        away_digit = '0'

    away_team = {str(i): '' for i in range(10)}
    if len(away) == 3:
        away_team['2'] = team_scores.get(away, {}).get('logo', '')
        away_team['3'] = away[0]
        away_team['4'] = away[1]
        away_team['5'] = away[2]
        away_team['6'] = team_scores.get(away, {}).get('logo', '')
    elif len(away) >= 2:
        away_team['3'] = team_scores.get(away, {}).get('logo', '')
        away_team['4'] = away[0]
        away_team['5'] = away[1]
        away_team['6'] = team_scores.get(away, {}).get('logo', '')

    user_dict = dict(db2("SELECT userid, username FROM users;"))
    alias_dict = dict(db2("SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"))

    grid = []
    box_num = 0
    row_offset = 0
    avail = 0
    current_user_box_count = 0
    for _ in range(10):
        row_cells = []
        for box_userid in box[8 + row_offset: 18 + row_offset]:
            alias = None
            if box_userid == 1 or box_userid == 0:
                name = 'Available '
                avail += 1
            else:
                if box_userid in alias_dict:
                    alias = alias_dict[box_userid]
                name = user_dict.get(box_userid, str(box_userid))
            row_cells.append({
                'box_num': box_num,
                'name': name,
                'userid': box_userid,
                'alias': alias,
                'winner_type': None,
                'winner_label': None,
            })
            box_num += 1
            if box_userid == session.get('userid'):
                current_user_box_count += 1
        grid.append(row_cells)
        row_offset += 10

    images = {str(k): v for k, v in dict(db2("SELECT userid, image FROM users WHERE image IS NOT NULL;")).items()}

    xy_string = "SELECT x, y FROM boxnums WHERE boxid = %s;"
    scores = []
    if avail != 0 or len(db2(xy_string, (int(boxid),))) == 0:
        num_selection = "Row/Column numbers will be randomly generated after all participants have paid."
        x = {str(n): '?' for n in range(10)}
        y = {str(n): '?' for n in range(10)}
    else:
        num_selection = ''
        xy = db2(xy_string, (int(boxid),))[0]
        x = json.loads(xy[0])
        y = json.loads(xy[1])

        winners = calc_winner(boxid)

        if len(winners) == 0 and ptype not in (PAY_TYPE_ID['every_score'], PAY_TYPE_ID['four_qtr'], PAY_TYPE_ID['every_minute']):
            try:
                curr_win_col = next(int(col) for col in x if str(x[col]) == home_digit)
                curr_win_row = next(int(r) for r in y if str(y[r]) == away_digit)
                cell = grid[curr_win_row][curr_win_col]
                cell['winner_type'] = 'final_winner' if status == 'Final' else 'current_winner'
                cell['winner_label'] = 'WINNER' if status == 'Final' else 'Current WINNER'
            except StopIteration:
                pass

        if ptype in (PAY_TYPE_ID['single'], PAY_TYPE_ID['ten_man'], PAY_TYPE_ID['satellite'], PAY_TYPE_ID['ten_man_final_reverse']) and len(winners) == 2:
            try:
                xw = next(int(item) for item in x if x[item] == int(winners[0]))
                yw = next(int(item) for item in y if y[item] == int(winners[1]))
                grid[yw][xw]['winner_type'] = 'final_winner'
                grid[yw][xw]['winner_label'] = 'WINNER'
            except StopIteration:
                pass

        if winners and ptype == PAY_TYPE_ID['four_qtr']:
            quarter = len(winners) // 2
            final_payout = f'{fee * 10} / {fee * 20} / {fee * 10} / {fee * 60}'

            def _find_qw(x_dict, y_dict, xval, yval):
                xw = next((int(i) for i in x_dict if x_dict[i] == int(xval)), None)
                yw = next((int(i) for i in y_dict if y_dict[i] == int(yval)), None)
                return xw, yw

            if quarter >= 1:
                xw, yw = _find_qw(x, y, winners[0], winners[1])
                if xw is not None and yw is not None:
                    is_current = live_quarter <= 1 and status != 'Final'
                    grid[yw][xw]['winner_type'] = 'winning_q1' if is_current else 'q1_winner'
                    grid[yw][xw]['winner_label'] = 'WINNING Q1' if is_current else 'Q1 WINNER'
            if quarter >= 2:
                xw, yw = _find_qw(x, y, winners[2], winners[3])
                if xw is not None and yw is not None:
                    is_current = live_quarter <= 2 and status not in ('Halftime', 'Final')
                    grid[yw][xw]['winner_type'] = 'winning_q2' if is_current else 'q2_winner'
                    grid[yw][xw]['winner_label'] = 'WINNING Q2' if is_current else 'Q2 WINNER'
            if quarter >= 3:
                xw, yw = _find_qw(x, y, winners[4], winners[5])
                if xw is not None and yw is not None:
                    is_current = live_quarter <= 3 and status != 'Final'
                    grid[yw][xw]['winner_type'] = 'winning_q3' if is_current else 'q3_winner'
                    grid[yw][xw]['winner_label'] = 'WINNING Q3' if is_current else 'Q3 WINNER'
            if quarter == 4:
                xw, yw = _find_qw(x, y, winners[6], winners[7])
                if xw is not None and yw is not None:
                    is_current = status != 'Final'
                    grid[yw][xw]['winner_type'] = 'winning_q4' if is_current else 'q4_winner'
                    grid[yw][xw]['winner_label'] = 'WINNING Q4' if is_current else 'Q4 WINNER'

        if ptype == PAY_TYPE_ID['every_score']:
            es_winners = db2("SELECT score_num, winning_box FROM everyscore where boxid = %s;", (int(boxid),))
            max_score_num = 1
            final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10)
            winner_dict = {}
            if len(es_winners) != 0:
                for w in es_winners:
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
                for wb_row in es_winners:
                    wb = wb_row[1]
                    sn = wb_row[0]
                    if sn < 100:
                        winner_dict[wb] = winner_dict.get(wb, 0) + (fee * 3)
                    elif sn == 101:
                        winner_dict[wb] = winner_dict.get(wb, 0) + fee
                    elif sn == 201:
                        winner_dict[wb] = winner_dict.get(wb, 0) + fee
                    elif sn == 100 and max_score_num <= 24:
                        winner_dict[wb] = winner_dict.get(wb, 0) + (fee * 10)
                    elif sn == 100 and max_score_num <= 26:
                        winner_dict[wb] = winner_dict.get(wb, 0) + 1000 - ((max_score_num - 24) * (fee * 3))
                    elif sn == 100 and max_score_num <= 27:
                        winner_dict[wb] = winner_dict.get(wb, 0) + fee
                    elif sn == 200:
                        winner_dict[wb] = winner_dict.get(wb, 0) + final_payout
                for wb, cash in winner_dict.items():
                    if int(wb) > 9:
                        x_win = int(str(wb)[-1:])
                        y_win = int(str(wb)[:1])
                    else:
                        x_win = int(str(wb)[-1:])
                        y_win = 0
                    cell = grid[y_win][x_win]
                    cell['winner_type'] = 'every_score_winner'
                    cell['winner_label'] = f'WINNER {cell["name"][:10]} ${cash}'
                    cell['winner_cash'] = cash
            else:
                final_payout = (fee * 100) - (fee * 10) - (fee * 3)

            score_rows = db2(
                "SELECT e.score_num, e.x_score, e.y_score, e.score_type, u.username, e.winning_box "
                "FROM everyscore e LEFT JOIN users u ON e.winner = u.userid "
                "WHERE e.boxid = %s ORDER BY e.score_num, e.score_id;",
                (int(boxid),)
            )
            scores = [list(r) for r in score_rows]

        if ptype == PAY_TYPE_ID['every_minute']:
            em_winners = get_espn_every_min_scores(espn_id)
            if not em_winners:
                if x.get('0') != '?':
                    try:
                        win_col = next(int(col) for col in x if str(x[col]) == '0')
                        win_row = next(int(r) for r in y if str(y[r]) == '0')
                        winner_boxnum = grid[win_row][win_col]['box_num']
                        winner_userid = grid[win_row][win_col]['userid']
                        winner_username = user_dict.get(winner_userid, '')
                        scores = [[0, 0, 0, f"Pre-Game 0/0 Winner ${int(fee * 1.5)}", winner_username, winner_boxnum]]
                        grid[win_row][win_col]['winner_type'] = 'every_minute_winner'
                        grid[win_row][win_col]['winner_label'] = f'WINNER {winner_username} ${int(fee * 1.5)}'
                    except StopIteration:
                        pass
            else:
                box_winners = {}
                reverse_payout = fee * 5
                final_payout_em = fee * 5
                minute = 0
                scores = []
                for winner in em_winners:
                    away_num = str(winner["away_score"])[-1]
                    home_num = str(winner["home_score"])[-1]
                    winning_minutes = winner["winning_minutes"]
                    win_type = winner["type"]
                    try:
                        win_col = next(int(col) for col in x if str(x[col]) == home_num)
                        win_row = next(int(r) for r in y if str(y[r]) == away_num)
                    except StopIteration:
                        continue
                    winner_boxnum = grid[win_row][win_col]['box_num']
                    winner_userid = grid[win_row][win_col]['userid']
                    winner_username = user_dict.get(winner_userid, '')
                    if win_type == "minute":
                        for i in range(winning_minutes):
                            scores.append([minute + i, str(winner["home_score"]), str(winner["away_score"]), f"MINUTE {minute + i} ${int(fee * 1.5)}", winner_username, winner_boxnum])
                        minute += winning_minutes
                        box_winners[winner_boxnum] = box_winners.get(winner_boxnum, 0) + int(winning_minutes * (fee * 1.5))
                        grid[win_row][win_col]['winner_type'] = 'every_minute_winner'
                        grid[win_row][win_col]['winner_label'] = f'WINNER {winner_username} ${box_winners[winner_boxnum]}'
                    elif win_type in ("final", "OT FINAL"):
                        scores.append([200, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} ${fee * 5}", winner_username, winner_boxnum])
                        box_winners[winner_boxnum] = box_winners.get(winner_boxnum, 0) + final_payout_em
                        grid[win_row][win_col]['winner_type'] = 'every_minute_winner'
                        grid[win_row][win_col]['winner_label'] = f'WINNER FINAL {winner_username} ${box_winners[winner_boxnum]}'
                    elif win_type in ("reverse", "OT FINAL REVERSE"):
                        scores.append([100, str(winner["home_score"]), str(winner["away_score"]), f"{win_type.upper()} ${fee * 5}", winner_username, winner_boxnum])
                        box_winners[winner_boxnum] = box_winners.get(winner_boxnum, 0) + reverse_payout
                        grid[win_row][win_col]['winner_type'] = 'every_minute_winner'
                        grid[win_row][win_col]['winner_label'] = f'WINNER REVERSE {winner_username} ${box_winners[winner_boxnum]}'
                    grid[win_row][win_col]['winner_type'] = grid[win_row][win_col].get('winner_type', 'every_minute_winner')

    if box_type == BOX_TYPE_ID['dailybox']:
        final_payout = ''

    return jsonify({
        'boxid': boxid,
        'box_name': box_name,
        'fee': fee,
        'avail': avail,
        'payout': payout,
        'final_payout': str(final_payout) if final_payout is not None else '',
        'rev_payout': rev_payout,
        'pay_type': pay_type,
        'ptype': ptype,
        'box_type': box_type,
        'kickoff_time': kickoff_time,
        'game_clock': game_clock,
        'num_selection': num_selection,
        'private_game_payment_link': private_game_payment_link,
        'current_user_box_count': current_user_box_count,
        'home': home,
        'away': away,
        'away_team': away_team,
        'team_scores': team_scores_json,
        'x': x,
        'y': y,
        'grid': grid,
        'scores': scores,
        'images': images,
        'current_userid': session.get('userid'),
        'current_username': session.get('username'),
    })


@bp.route("/api/select_box", methods=["POST"])
@login_required
def api_select_box():
    data = request.get_json()
    boxid = data.get('boxid')
    box_num = int(data.get('box_num'))

    box_attr = db2("SELECT box_type, pay_type FROM boxes WHERE boxid = %s;", (int(boxid),))[0]
    box_type = box_attr[0]
    pay_type = box_attr[1]
    boxes = db2("SELECT {} FROM boxes WHERE boxid = %s;".format(box_string()), (int(boxid),))[0]

    rand_list = [i for i, b in enumerate(boxes) if b == 0 or b == 1]
    user_box_count = sum(1 for b in boxes if (box_type == BOX_TYPE_ID['nutcracker'] or pay_type == PAY_TYPE_ID['ten_man'] or pay_type == PAY_TYPE_ID['satellite']) and b == session['userid'])

    if box_num not in rand_list:
        if boxes[box_num] == session['userid']:
            if len(rand_list) == 0:
                return jsonify({"error": "Numbers were drawn — can't undo now"}), 400
            db2("UPDATE boxes SET box{}= 1 WHERE boxid = %s;".format(box_num), (int(boxid),))
            return jsonify({"success": True, "action": "undo"})
        owner = db2("SELECT username FROM users WHERE userid = %s;", (boxes[box_num],))
        owner_name = owner[0][0] if owner else "someone"
        return jsonify({"error": f"{owner_name} already has this box"}), 400

    if (box_type == BOX_TYPE_ID['nutcracker'] or pay_type == PAY_TYPE_ID['ten_man']) and user_box_count >= 10:
        return jsonify({"error": "10 boxes max for this game"}), 400

    if box_type == BOX_TYPE_ID['nutcracker']:
        gobbler_id = db2("SELECT gobbler_id FROM boxes WHERE boxid = %s;", (int(boxid),))[0][0]
        db2("UPDATE boxes SET box{}=%s WHERE gobbler_id = %s;".format(box_num), (session['userid'], gobbler_id))
    else:
        db2("UPDATE boxes SET box{}=%s WHERE boxid = %s;".format(box_num), (session['userid'], int(boxid)))
        logging.info("user {} picked box {} in boxid {}".format(session['username'], box_num, boxid))

    return jsonify({"success": True, "action": "select"})
