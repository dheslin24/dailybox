import json
import random

from flask import Markup, session
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID


def box_string():
    s = ''
    for x in range(100):
        s += 'box' + str(x) + ", "
    s = s[:-2]  # chop last space and ,
    return s

def assign_xy():
    n = [x for x in range(10)]
    random.shuffle(n)
    return(n)

def assign_numbers(boxid):
    x_nums = assign_xy()
    y_nums = assign_xy()
    x_string = '{'
    y_string = '{'
    for i in range(10):
        x_string += '"' + str(i) + '"' + ':' + str(x_nums[i]) + ','
        y_string += '"' + str(i) + '"' + ':' + str(y_nums[i]) + ','
    x_string = x_string[:-1] # chop off last ,
    y_string = y_string[:-1]
    x_string += '}'
    y_string += '}'
    s = "INSERT INTO boxnums(boxid, x, y) VALUES({}, '{}', '{}');".format(boxid, x_string, y_string)
    db(s)

def count_avail(boxid):
    s = "SELECT * FROM boxes WHERE boxid = {};".format(boxid)
    boxes = db(s)[0]
    count = 0
    for x in boxes[:len(boxes)-101:-1]:
        if x == 1 or x == 0:
            count += 1
    return count

def payout_calc(pay_type, fee):
    if pay_type == PAY_TYPE_ID['four_qtr']:
        a = fee * 10
        b = fee * 20
        c = fee * 60
        s = '1st {} / 2nd {} / 3rd {} / Final {}'.format(a, b, a, c)
    elif pay_type == PAY_TYPE_ID['single']:
        s = 'Single Winner: {}'.format(fee * 100)
    elif pay_type == PAY_TYPE_ID['ten_man']:
        s = 'Single Winner 10 Man: {}'.format(fee * 10)
    elif pay_type == PAY_TYPE_ID['satellite']:
        s = 'Satellite'
    elif pay_type == PAY_TYPE_ID['ten_man_final_reverse']:
        s = 'Final: {}  /  Reverse Final: {}'.format(int((fee * 10) *.75), int((fee * 10) *.25))
    elif pay_type == PAY_TYPE_ID['ten_man_final_half']:
        s = 'Final: {}  / Half: {}'.format(int((fee * 10) *.75), int((fee * 10) *.25))
    elif pay_type == PAY_TYPE_ID['every_score']:
        s = Markup('Every score wins {} up to 27 scores.  Final gets remainder after all payouts, min {}.  <br>Reverse final wins min {} / max {} (see TW email).  Anything touching reverse or final wins {}.'.format(fee * 3, fee * 10, fee, fee * 10, fee))
    elif pay_type == PAY_TYPE_ID['every_minute']:
        s = Markup(f'Every minute you are winning {int(fee*1.5)} - Final and Reverse Final {int(fee*5)}')
    else:
        s = 'Payouts for Game Type not yet supported'
    return s

def calc_winner(boxid):
    pt = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
    pay_type = db(pt)[0][0]
    print(pay_type)

    winner_list = []
    if pay_type == PAY_TYPE_ID['single'] or pay_type == PAY_TYPE_ID['ten_man'] or pay_type == PAY_TYPE_ID['satellite'] or pay_type == PAY_TYPE_ID['ten_man_final_reverse']:  # final only
        s = "SELECT x4, y4 FROM scores WHERE boxid = {};".format(boxid)
        scores = db(s)
        if len(scores) == 0:
            return winner_list
        print(scores[-1:][0])
        score = scores[-1:][0]
        if score[0] > 9:
            winner_list.append(str(score[0])[-1:])
        else:
            winner_list.append(str(score[0]))
        if score[1] > 9:
            winner_list.append(str(score[1])[-1:])
        else:
            winner_list.append(str(score[1]))

    elif pay_type == PAY_TYPE_ID['four_qtr']: # all 4 qtrs
        s = "SELECT x1, y1, x2, y2, x3, y3, x4, y4 FROM scores WHERE boxid = {};".format(boxid)
        scores = db(s)
        if len(scores) == 0:
            return winner_list
        else:
            for score in scores[-1:][0]:
                print(f"score in calc {score}")
                if score is not None:
                    if score > 9:
                        winner_list.append(str(score)[-1:])
                    else:
                        winner_list.append(str(score))

    print(winner_list)
    return winner_list

def find_winning_user(boxid):
    s = "SELECT * FROM scores WHERE boxid = {} ORDER BY score_id DESC LIMIT 1;".format(boxid)
    print(s)
    scores = db(s)[0]
    score_list = []
    for score in scores[3:]:
        if score != None:
            score_list.append(str(score)[-1:])
        else:
            score_list.append(None)
    print(score_list)

    xy = "SELECT x, y FROM boxnums WHERE boxid = {};".format(boxid)
    xy_list = db(xy)
    x = json.loads(xy_list[0][0])
    y = json.loads(xy_list[0][1])

    box_x = []
    box_y = []
    for score in score_list[::2]: # only look at the x's
        if score != None:
            for n in x:
                if x[n] == int(score):
                    box_x.append(n)

    for score in score_list[1::2]: # look at y's
        if score != None:
            for n in y:
                if y[n] == int(score):
                    box_y.append(n)
    print(box_x, box_y)

    winner_list = []
    for n in range(len(box_x)):
        boxnum = "box"
        if box_y[n] != '0':
            boxnum += box_y[n]
        boxnum += box_x[n]
        w = "SELECT {} FROM boxes WHERE boxid = {};".format(boxnum, boxid)
        winner = db(w)[0][0]
        winner_list.append(winner)
        print(winner)

    print(winner_list)
    return(winner_list)

def check_box_limit(userid):
    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''
    for _ in box_list:
        box_string += _
    box_string = box_string[:-2]
    box = "SELECT {} FROM boxes WHERE active = 1 or boxid between 26 and 36;".format(box_string)
    all_boxes = db(box)
    count = 0
    for game in all_boxes:
        for b in game:
            if b == session['userid']:
                count += 1
    s = "SELECT max_boxes FROM max_boxes WHERE userid = {};".format(session['userid'])
    mb = db(s)

    if len(mb) == 0:
        return True
    elif count < mb[0][0]:
        return False
    else:
        return True

def create_new_game(box_type, pay_type, fee, box_name=None, home=None, away=None, espn_id=None):
    if box_name == None:
        s = "SELECT max(boxid) from boxes;"
        max_box = db(s)[0][0]
        box_name = "db" + str(max_box + 1)

    c = ''
    for x in range(100):
        c += 'box' + str(x) + ", "
    c = c[:-2]

    v = "{}, 1, {}, '{}', '{}', '{}', ".format(fee, box_type, box_name, pay_type, espn_id)
    for x in range(100):
        v += str(1) + ", "
    v = v[:-2]

    s = "INSERT INTO boxes(fee, active, box_type, box_name, pay_type, espn_id, {}) VALUES({});".format(c, v)
    db(s)

    b = "SELECT max(boxid) FROM boxes;"
    boxid = db(b)[0][0]

    t = "INSERT INTO teams(boxid, home, away) VALUES('{}', '{}', '{}');".format(boxid, home, away)
    db(t)

def get_games(box_type, active=1):
    box_string = ''
    for b in box_type:
        box_string += str(b) + ', '
    box_string = box_string[:-2]

    if active == 0:
        s = "SELECT b.boxid, b.box_name, b.fee, pt.description, s.winner FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id LEFT JOIN scores s ON s.boxid = b.boxid WHERE b.active = {} and b.box_type in ({});".format(active, box_string)
        games = db(s)
        game_list = [list(game) for game in games]
        u = "SELECT userid, username FROM users;"
        user_dict = dict(db2(u))
        print(user_dict)
        for game in game_list:
            if game[4] is not None:
                game[4] = user_dict[int(game[4])]
            else:
                game[4] = "N/A"

    elif box_type[0] == 4:
        priv_boxid_string = "SELECT boxid FROM privategames WHERE userid = %s;"
        priv_boxes = db2(priv_boxid_string, (session['userid'], ))
        if priv_boxes:
            priv_boxids = []
            for b in priv_boxes:
                priv_boxids.append(b[0])
            print(f"private boxids {priv_boxids}")
            boxid_string = ""
            for bs in priv_boxids:
                boxid_string += str(bs) + ", "
            boxid_string = boxid_string[:-2]
            s = f"SELECT b.boxid, b.box_name, b.fee, pt.description FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id WHERE b.active = {active} and b.boxid in ({boxid_string}) and b.box_type in ({box_type[0]});"
            games = db2(s)
            game_list = [list(game) for game in games]
        else:
            return []

    else:
        s = "SELECT b.boxid, b.box_name, b.fee, pt.description FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id WHERE b.active = {} and b.box_type in ({});".format(active, box_string)
        games = db(s)
        game_list = [list(game) for game in games]

    print(game_list)
    if active == 1:
        a = "SELECT * FROM boxes WHERE active = {};".format(active)
        avail = db(a)

        available = {}
        for game in avail:
            count = 0
            for x in game[:len(game)-101:-1]:
                if x == 1 or x == 0:
                    count += 1
            available[game[0]] = count

        for game in game_list:
            game.append(available[game[0]])
        print(game_list)

    return game_list

def auto_check_lines():
    print("checking espn lines automatically")
    pass


def activate_game(boxid):
    check_sql_string = "SELECT boxid FROM boxnums WHERE boxid = %s"
    if db2(check_sql_string, (boxid,)):
        return "Escalate with tech support, this game has already drawn numbers"

    avail = count_avail(boxid)
    s = "SELECT box_type, pay_type from boxes WHERE boxid = {};".format(boxid)
    box = db(s)
    box_type = box[0][0]
    pay_type = box[0][1]

    print("boxtype in start game {}".format(box_type))
    if avail != 0:
        return "Cannot start game - still boxes available"

    assign_numbers(boxid)
    if box_type == BOX_TYPE_ID['dailybox']:
        winning_col = random.randint(0, 9)
        winning_row = random.randint(0, 9)
        scores = "INSERT INTO scores(boxid, x4, y4) VALUES('{}', '{}', '{}');".format(boxid, winning_col, winning_row)
        db(scores)
        inactivate = "UPDATE boxes SET active = 0 WHERE boxid = {};".format(boxid)
        db(inactivate)
        w = "UPDATE scores SET winner = {} WHERE boxid = {};".format(find_winning_user(boxid)[0], boxid)
        db(w)
    if pay_type == PAY_TYPE_ID['every_score'] or PAY_TYPE_ID['every_minute']:
        winner = find_winning_box(boxid, 0, 0)
        win_box = winner[0]
        win_uid = winner[1]
        s = "INSERT INTO everyscore(score_num, score_type, boxid, x_score, y_score, winner, winning_box) VALUES('1', '0/0 Start Game', {}, '0', '0', '{}', '{}');".format(boxid, win_uid, win_box)
        db(s)

    return None  # success


def get_user_games(userid):
    s = "SELECT * FROM boxes;"
    games = db(s)
    g_list = [list(game) for game in games]

    pt = "SELECT pay_type_id, description from pay_type;"
    payout_types = dict(db(pt))

    bw = "SELECT boxid, winner FROM scores ORDER BY score_id ASC;"
    win_dict = dict(db(bw))

    bn = "SELECT * FROM boxnums;"
    boxnums = db(bn)

    u = "SELECT userid, username FROM users;"
    user_dict = dict(db2(u))

    alias_string = "SELECT userid, alias_of_userid FROM users WHERE alias_of_userid IS NOT NULL;"
    aliases = dict(db2(alias_string))

    t = "SELECT boxid, home, away from teams;"
    teams_list = db2(t)
    teams_dict = {}
    for t_boxid, t_home, t_away in teams_list:
        teams_dict[t_boxid] = {"home": t_home, "away": t_away}

    boxnum_x = {}
    boxnum_y = {}
    for b_id in boxnums:
        boxnum_x[b_id[0]] = json.loads(b_id[1])
        boxnum_y[b_id[0]] = json.loads(b_id[2])

    game_list = []
    completed_game_list = []
    available = {}

    for game in g_list:
        count = 0
        gameid = game[0]
        active = game[1]
        b_type = game[2]
        if b_type == 1:
            box_type = 'Daily Box'
        elif b_type == 2:
            box_type = 'Custom Box'
        elif b_type == 3:
            box_type = 'Nutcracker'
        else:
            box_type = 'Daily Box'
        box_name = game[3]
        fee = game[4]
        pay_type = payout_types[game[5]]
        box_index = 0

        if active == 0:
            if gameid not in win_dict:
                winner = "multi"
            else:
                if not win_dict[gameid]:
                    winner = "none - game canceled"
                elif win_dict[gameid][:1] == "{":
                    winner = "multi"
                else:
                    winner = user_dict[int(win_dict[gameid])]

        for b in game[8:]:  # BOX DB Change if schema change here
            if b in aliases:
                box = aliases[b]
                alias = user_dict[b]
            else:
                box = b
                alias = ''

            if box == userid and active == 1:
                if gameid in boxnum_x:
                    h_num = teams_dict.get(gameid).get("home") + " " + str(boxnum_x[gameid][str(box_index % 10)])
                    a_num = teams_dict.get(gameid).get("away") + " " + str(boxnum_y[gameid][str(box_index // 10)])
                else:
                    h_num = "TBD"
                    a_num = "TBD"
                game_list.append((gameid, box_name, box_index + 1, alias, fee, pay_type, h_num, a_num))

            elif box == userid and active == 0:
                completed_game_list.append((gameid, box_type, box_name, box_index + 1, alias, fee, pay_type, winner))

            if box == 1 or box == 0:
                count += 1
            box_index += 1

        available[game[0]] = count

    return game_list, completed_game_list, available

def find_winning_box(boxid, home_score, away_score):
    if int(home_score) > 9:
        h = str(home_score)[-1:]
    else:
        h = str(home_score)
    if int(away_score) > 9:
        a = str(away_score)[-1:]
    else:
        a = str(away_score)

    xy = "SELECT x, y from boxnums WHERE boxid = {};".format(boxid)
    xy_list = db(xy)
    x = json.loads(xy_list[0][0])
    y = json.loads(xy_list[0][1])
    print(h, a)
    print(x, y)

    boxnum = ''
    for item in y:
        if y[item] == int(a):
            if item != '0':
                boxnum += item
    for item in x:
        if x[item] == int(h):
            boxnum += item
    print("boxnum for ES is {}".format(boxnum))

    w = "SELECT box{} FROM boxes WHERE boxid = {};".format(boxnum, boxid)
    winner = db(w)[0][0]
    print("winner {}".format(winner))
    return (boxnum, winner)

def sanity_checks(boxid_list):
    check_result_list = []
    if len(boxid_list) > 1:
        for item in boxid_list:
            max_list = []
            m = "SELECT max(score_num) FROM everyscore WHERE boxid = {};".format(item)
            max_list.append(db(m)[0][0])
        if len(set(max_list)) == 1:
            check_result_list.append('SUCCESS - all games have equal max score')
        else:
            check_result_list.append('WARNING - not all games have equal max score')

    m = "SELECT e.boxid, e.score_num FROM everyscore e INNER JOIN boxes b ON e.boxid = b.boxid WHERE b.active = 1 ORDER BY boxid, score_num;"
    max_check = db(m)
    d = {}
    for x in max_check:
        if x[0] not in d:
            d[x[0]] = [x[1]]
        else:
            d[x[0]].append(x[1])
    print(d)
    seq_list = []
    for key in d:
        if max(d[key]) != len(d[key]) and max(d[key]) != 200:
            check_result_list.append('WARNING - check score numbers for boxid {}, it may not be sequential'.format(key))
        if d[key][0] != 1:
            print("first score check {}".format(d[key][0]))
            check_result_list.append('WARNING - your first score number should be 1.  it is not for boxid {}'.format(key))
        else:
            last = 1
            good = True
            for sn in d[key][1:]:
                if sn - last != 1 and (sn != 100 and sn != 200):
                    good = False
                    check_result_list.append('WARNING - score numbers are not sequential.  check boxid {} between {} and {}'.format(key, last, sn))
                last = sn
            if good == True:
                seq_list.append(str(key))
    print("seq list")
    print(len(seq_list), len(d))
    if len(seq_list) == len(d):
        check_result_list.append('SUCCESS - score nums are sequential for boxid(s) {}.'.format(", ".join(seq_list)))
    return check_result_list

def find_touching_boxes(boxnum):
    touch_list = ()
    corner = [0, 9, 90, 99]
    if boxnum == 0:
        touch_list = (1, 9, 10, 90)
    elif boxnum == 9:
        touch_list = (0, 8, 19, 99)
    elif boxnum == 90:
        touch_list = (0, 80, 91, 99)
    elif boxnum == 99:
        touch_list = (9, 89, 90, 98)
    elif boxnum % 10 == 0 and boxnum not in corner:
        touch_list = (boxnum + 9, boxnum - 10, boxnum + 10, boxnum + 1)
    elif boxnum % 10 == 9 and boxnum not in corner:
        touch_list = (boxnum - 9, boxnum - 10, boxnum + 10, boxnum - 1)
    elif boxnum <= 9 and boxnum not in corner:
        touch_list = (boxnum + 90, boxnum + 10, boxnum + 1, boxnum - 1)
    elif boxnum >= 90 and boxnum not in corner:
        touch_list = (boxnum - 90, boxnum - 10, boxnum + 1, boxnum - 1)
    else:
        touch_list = (boxnum + 10, boxnum - 10, boxnum + 1, boxnum - 1)

    print("{} are touching winner {}".format(touch_list, boxnum))
    return touch_list
