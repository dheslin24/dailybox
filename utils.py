from flask import flash, redirect, render_template, session, Markup
from functools import wraps
import json
import random
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID


def apology(message, code=400):
    """Renders message as an apology to user."""
    return render_template("apology.html", top=code, bottom=message, code=code)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("userid") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("is_admin") == 0:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    from constants import ALLOWED_EXTENSIONS
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# create json string of assigned x/y numbers
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
    '''
    mysql> select * from pay_type;
    +-------------+--------------------------+
    | pay_type_id | description              |
    +-------------+--------------------------+
    |           1 | 4 Qtr Payout 10/30/10/50 |
    |           2 | Single Payout            |
    |           3 | Every Score              |
    |           4 | Touch Box                |
    |           5 | 10-Man                   |
    |           6 | Satellite
    |           7 | 10-Man Final/Reverse 75/25
    |           8 | Every Minute             |
    |           9 | 10-man Final/Half 75/25  |
    +-------------+--------------------------+
    '''
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
        s = 'Payouts for Game Type not yet supported' # will add later date

    return s

def calc_winner(boxid):  # all this does is strip all beginning digits from the scores
    # find pay_type
    pt = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
    pay_type = db(pt)[0][0]
    print(pay_type)

    winner_list = []
    if pay_type == PAY_TYPE_ID['single'] or pay_type == PAY_TYPE_ID['ten_man'] or pay_type == PAY_TYPE_ID['satellite'] or pay_type == PAY_TYPE_ID['ten_man_final_reverse']:  # final only
        s = "SELECT x4, y4 FROM scores WHERE boxid = {};".format(boxid)
        scores = db(s)# [-1:][0]  # always take the last in list
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

    # pay_type == 3 or 8:  #  will do this elsewhere

    print(winner_list)
    return winner_list

# returns a list of winning userids for a given boxid.
# if each quarter has winner, will be [q1, q2, q3, f]
# if single winner, [f]
# if final/reverse final [TODO NUTX]
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
    # go thru each score, find in grid
    for score in score_list[::2]: # only look at the x's
        if score != None:
            # box_x = [n for n in x if x[n] == int(score)]
            for n in x:
                if x[n] == int(score):
                    box_x.append(n)

    for score in score_list[1::2]: # look at y's
        if score != None:
            #box_y = [n for n in y if y[n] == int(score)]
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
        for box in game:
            if box == session['userid']:
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

    # builds the string of box## to create
    c = ''
    for x in range(100):
        c += 'box' + str(x) + ", "
    c = c[:-2]  # chop last space and ,

    # create string of v = values to add
    v = "{}, 1, {}, '{}', '{}', '{}', ".format(fee, box_type, box_name, pay_type, espn_id) # sets column active to Y
    for x in range(100):
        v += str(1) + ", "  # 1 is place holder value for box entry
    v = v[:-2] # chop last space and ,

    s = "INSERT INTO boxes(fee, active, box_type, box_name, pay_type, espn_id, {}) VALUES({});".format(c,v)
    db(s)

    b = "SELECT max(boxid) FROM boxes;"
    boxid = db(b)[0][0]

    t = "INSERT INTO teams(boxid, home, away) VALUES('{}', '{}', '{}');".format(boxid, home, away)
    db(t)


# takes [box_type, box_type, ...]
def get_games(box_type, active = 1):

    box_string = ''
    for b in box_type:
        box_string += str(b) + ', '
    box_string = box_string[:-2] # chop last ', '

    if active == 0:
        s = "SELECT b.boxid, b.box_name, b.fee, pt.description, s.winner FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id LEFT JOIN scores s ON s.boxid = b.boxid WHERE b.active = {} and b.box_type in ({});".format(active, box_string)
        games = db(s)
        game_list = [list(game) for game in games]
        u = "SELECT userid, username FROM users;"
        user_dict = dict(db2(u))
        print(user_dict)
        for game in game_list:
            if game[4] is not None:
                #w = "SELECT username FROM users WHERE userid = {};".format(game[4])
                #username = db(w)[0][0]
                # game[4] = username
                game[4] = user_dict[int(game[4])]
            else:
                game[4] = "N/A"

    elif box_type[0] == 4:
        priv_boxid_string = "SELECT boxid FROM privategames WHERE userid = %s;"
        priv_boxes = db2(priv_boxid_string, (session['userid'], ))
        if priv_boxes:
            priv_boxids = []
            for box in priv_boxes:
                priv_boxids.append(box[0])
            #priv_boxids = priv_boxes[0][0]
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

        # add the avail spots to the list that is passed to display game list
        #if active == 1:
        for game in game_list:
            game.append(available[game[0]])
        print(game_list)

    return game_list


def auto_check_lines():
    print("checking espn lines automatically")
    pass

def find_winning_box(boxid, home_score, away_score):
    # returns tuple of boxnumber in grid, and the winning UID who owns that box

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
    print(h,a)
    print(x,y)

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
    ### sanity checks ###
    check_result_list = []
    # 1. if multiple games for everyscore, do they all have the same max score_num?
    if len(boxid_list) > 1:  # if equal to 1, don't bother checking or alerting on this
        for item in boxid_list:
            max_list = []
            m = "SELECT max(score_num) FROM everyscore WHERE boxid = {};".format(item)
            max_list.append(db(m)[0][0])
        if len(set(max_list)) == 1:
            check_result_list.append('SUCCESS - all games have equal max score')
        else:
            check_result_list.append('WARNING - not all games have equal max score')

    # 2. check there are no gaps in max scores
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
        if max(d[key]) != len(d[key]) and max(d[key]) != 200:  # don't check if game over.  200 means final.
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
    ### END sanity checks ###

def find_touching_boxes(boxnum):
    # corners first - just hard code
    # edges next:
    #   boxnum % 10 == 0 is left column - wrap to right column
    #   boxnum % 10 == 9 is right column - wrap to left column
    #   boxnum <= 9 is top row - wrap to bottom
    #   boxnum >= 90 is bottom row - wrap to top
    # then middle
    touch_list = ()
    corner = [0,9,90,99]
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

# get games function
# if detailed == False, returns list of gameids.  If True, returns dict of game objects.
def get_pickem_games(season, detailed=False):

    # only retrieves the latest game with highest id, incase of changes (i.e. spread change)
    g = "SELECT DISTINCT g.gameid, g.game_name, g.fav, g.spread, g.dog, g.locked FROM pickem.games g INNER JOIN (SELECT gameid, MAX(id) as maxid FROM pickem.games GROUP BY gameid) gg ON g.gameid = gg.gameid AND g.id = gg.maxid WHERE season = %s ORDER BY g.gameid ASC"
    games = db2(g, (season,))

    class Game:
        def __init__(self, game_name, fav, spread, dog, locked, winner="TBD"):
            self.game_name = game_name
            self.fav = fav
            self.spread = spread
            self.dog = dog
            self.locked = locked
            self.winner = winner

    # check for winner
    s = "SELECT gameid, fav_score, dog_score FROM pickem.pickem_scores ORDER BY score_id DESC;"
    scores = db2(s)
    score_dict = {}
    for score in scores:
        if score[0] not in score_dict:
            score_dict[score[0]] = {'fav':score[1], 'dog':score[2]}

    game_list = [x for x in range(1,14)]
    game_dict = {}
    index = 0
    for g in games:
        game_dict[g[0]] = Game(g[1], g[2], g[3], g[4], g[5])
        if g[0] in score_dict:
            if (score_dict[g[0]]['fav'] + game_dict[g[0]].spread) - score_dict[g[0]]['dog'] > 0:  # fav won
                game_dict[g[0]].winner = game_dict[g[0]].fav.upper()
            else:
                game_dict[g[0]].winner = game_dict[g[0]].dog.upper()

    # create game objects for games that don't exist yet
    for n in range(len(game_dict) + 1, 14):
        game_dict[n] = Game('TBD', 'TBD', 0, 'TBD', False)

    if detailed == False:
        return game_list
    else:
        return game_dict

def sref_to_pickem(convention='p'):
    # p == return pickem value
    # s == return sportsreference value
    p = { \
        "nor" : "NO",  "min" : "MIN", \
        "det" : "DET", "tam" : "TPA", \
        "crd" : "ARI", "sfo" : "SF",  \
        "rai" : "LV",  "mia" : "MIA", \
        "rav" : "BAL", "nyg" : "NYG", \
        "pit" : "PIT", "clt" : "IND", \
        "nyj" : "NYJ", "cle" : "CLE", \
        "kan" : "KC",  "atl" : "ATL", \
        "jax" : "JAX", "chi" : "CHI", \
        "htx" : "HOU", "cin" : "CIN", \
        "was" : "WAS", "car" : "CAR", \
        "sdg" : "LAC", "den" : "DEN", \
        "sea" : "SEA", "ram" : "LAR", \
        "dal" : "DAL", "phi" : "PHI", \
        "gnb" : "GB",  "oti" : "TEN", \
        "nwe" : "NE",  "buf" : "BUF" \
        }

    # provide reverse lookup if requested
    if convention == 's':
        s = dict([(value, key) for key, value in p.items()])
        return s
    else:
        return p
