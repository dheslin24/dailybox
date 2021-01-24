from flask import Flask, flash, redirect, render_template, request, session, url_for, Markup
from flask_session import Session
import logging
#from flask_sslify import SSLify
from passlib.apps import custom_app_context as pwd_context
#from werkzeug.serving import make_ssl_devcert, run_simple
import sys
import random
import json
import config
from operator import itemgetter, attrgetter
import mysql.connector
from mysql.connector import errorcode
from functools import wraps
from sportsreference.nfl.boxscore import Boxscores, Boxscore
from sportsreference.nfl.schedule import Schedule

logging.basicConfig(filename="byg.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG, datefmt="%Y-%m-%d %H:%M:%S")

app = Flask(__name__)

# ensure responses aren't caches
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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

# imported config
db_config = {'user':config.user, 'password':config.password, 'host':config.host, 'database':config.database}
# print(db_config)

def db(s, db_config=db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
        #print("try succeeded")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Invalid Username or Password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    #else:
        #print("try failed")
        #cnx.close()

    cursor = cnx.cursor()
    print(s)
    cursor.execute(s)
    rv = ()
    if s[:6] == "SELECT":
        rv = cursor.fetchall()
        cursor.close()
        cnx.close()
        return rv
    else:
        cnx.commit()
        cursor.close()
        cnx.close()

def db2(s, params=(), db_config=db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
        #print("try succeeded")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Invalid Username or Password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    #else:
        #print("try failed")
        #cnx.close()

    if len(params) == 0:
        cursor = cnx.cursor()
        print(s)
        cursor.execute(s)
    else:
        cursor = cnx.cursor()
        print("db2 executing")
        print(s, params)
        cursor.execute(s, params)

    rv = ()
    if s[:6] == "SELECT":
        rv = cursor.fetchall()
        cursor.close()
        cnx.close()
        return rv
    else:
        cnx.commit()
        cursor.close()
        cnx.close()


def init_grid():
    grid = []
    for x in range(10):
        l = []
        for y in range(10):
            l.append((x,y))
        grid.append(l)

    grid[0][5] = 'DH'
    grid[2][3] = 'TW'
    grid[1][7] = 'GG'
    grid[1][4] = 'THIS'
    grid[2][4] = 'COULD'
    grid[3][4] = 'BE'
    grid[4][4] = 'YOU!'
    print(grid)
    return(grid)

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

x_nums = ['x{}'.format(x) for x in range(10)]
x_nums.insert(0,'')
y_nums = ['y{}'.format(x) for x in range(10)]

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
    +-------------+--------------------------+
    '''
    if pay_type == 1:
        a = fee * 10
        b = fee * 30
        c = fee * 50
        s = '1st {} / 2nd {} / 3rd {} / Final {}'.format(a, b, a, c)
    elif pay_type == 2:
        s = 'Single Winner: {}'.format(fee * 100)
    elif pay_type == 5:
        s = 'Single Winner 10 Man: {}'.format(fee * 10)
    elif pay_type == 6:
        s = 'Satellite'
    elif pay_type == 7:
        s = 'Final: {}  /  Reverse Final: {}'.format(int((fee * 10) *.75), int((fee * 10) *.25))
    elif pay_type == 3:
        s = Markup('Every Score Wins {} up to 28 scores.  Reverse Final Wins {}.  <br>Anything touching reverse or final wins {}.  Final gets the remainder.'.format(fee * 3, fee * 10, fee))
    else:
        s = 'Payouts for Game Type not yet supported' # will add later date

    return s

def calc_winner(boxid):  # all this does is strip all beginning digits from the scores
    # find pay_type
    pt = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
    pay_type = db(pt)[0][0]
    print(pay_type)

    winner_list = []
    if pay_type == 2 or pay_type == 5 or pay_type == 6 or pay_type == 7:  # final only
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

    elif pay_type == 1: # all 4 qtrs
        s = "SELECT x1, y1, x2, y2, x3, y3, x4, y4 FROM scores WHERE boxid = {};".format(boxid)
        scores = db(s)
        if len(scores) == 0:
            return winner_list
        else:
            for score in scores[-1:][0]:
                if score > 9:
                    winner_list.append(str(score)[-1:])
                else:
                    winner_list.append(str(score))

    # pay_type == 3:  #  will do this elsewhere

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

def create_new_game(box_type, pay_type, fee, box_name=None, home=None, away=None):
    if box_name == None:
        s = "SELECT max(boxid) from boxes;"
        max_box = db(s)[0][0]
        box_name = "db" + str(max_box + 1)

    c = ''
    for x in range(100):
        c += 'box' + str(x) + ", "
    c = c[:-2]  # chop last space and ,

    # create string of v = values to add
    v = "{}, 1, {}, '{}', '{}', ".format(fee, box_type, box_name, pay_type) # sets column active to Y
    for x in range(100):
        v += str(1) + ", "  # 1 is place holder value for box entry
    v = v[:-2] # chop last space and ,

    s = "INSERT INTO boxes(fee, active, box_type, box_name, pay_type, {}) VALUES({});".format(c,v)
    db(s)
    
    b = "SELECT max(boxid) FROM boxes;"
    boxid = db(b)[0][0]

    t = "INSERT INTO teams(boxid, home, away) VALUES('{}', '{}', '{}');".format(boxid, home, away)
    db(t)

#@app.route("/start_game", methods=["POST", "GET"])
def start_game(boxid):
    avail = count_avail(boxid)
    s = "SELECT box_type, pay_type from boxes WHERE boxid = {};".format(boxid)
    box = db(s)        
    box_type = box[0][0]
    pay_type = box[0][1]
    
    print("boxtype in start game {}".format(box_type))
    if avail == 0:
        assign_numbers(boxid) # this assigns the row/col numbers
        if box_type == 1:  # this is a dailybox, so generate the winning numbers as well
            winning_col = random.randint(0,9)
            winning_row = random.randint(0,9)
            scores = "INSERT INTO scores(boxid, x4, y4) VALUES('{}', '{}', '{}');".format(boxid, winning_col, winning_row)
            db(scores)
            # and... mark the game inactive in database
            inactivate = "UPDATE boxes SET active = 0 WHERE boxid = {};".format(boxid)
            db(inactivate)
            # and... update the db with winner - in scores
            w = "UPDATE scores SET winner = {} WHERE boxid = {};".format(find_winning_user(boxid)[0], boxid)
            db(w)
        if pay_type == 3:  # this is everyscore pool, so set 0, 0 as initial winning score
            winner = find_winning_box(boxid, 0, 0)
            win_box = winner[0]
            win_uid = winner[1]
            
            s = "INSERT INTO everyscore(score_num, score_type, boxid, x_score, y_score, winner, winning_box) VALUES('1', '0/0 Start Game', {}, '0', '0', '{}', '{}');".format(boxid, win_uid, win_box)
            db(s)

    else:
        print("tried to start game, but boxes still available")
        return apology("Cannot start game - still boxes available")
    

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

@app.route("/init_box_db")
@login_required
def init_box_db():
    b = ['box' + str(x) + " INT," for x in range(100)]
    s = "CREATE TABLE IF NOT EXISTS boxes(boxid INT AUTO_INCREMENT PRIMARY KEY, active, box_type, box_name, fee int, "
    for _ in b:
        s += _
    s = s[:-1]
    s += ")"
    db(s)

    return redirect(url_for("index"))

@app.route("/create_game", methods=["POST", "GET"])
def create_game():
    fee = request.form.get('fee')
    if not request.form.get('box_name'):
        s = "SELECT max(boxid) from boxes;"
        max_box = db(s)[0][0]
        box_name = "db" + str(max_box + 1)
    else:
        box_name = request.form.get('box_name')
    
    box_type = request.form.get('box_type')
    pay_type = request.form.get('pay_type')
    # create string of c = columns to update
    home = request.form.get('home')
    away = request.form.get('away')
    create_new_game(box_type, pay_type, fee, box_name, home, away)

    return redirect(url_for("index"))

@app.route("/gobble_games", methods=["POST", "GET"])
def gobble_games():
    boxid_1 = request.form.get('boxid_1')
    boxid_2 = request.form.get('boxid_2')
    boxid_3 = request.form.get('boxid_3')
    print(boxid_1, boxid_2, boxid_3)
    g = "SELECT max(gobbler_id) from boxes;"
    max_g = db(g)[0][0]
    g_id = max_g + 1
    s = "UPDATE boxes SET gobbler_id = {} WHERE boxid IN ({}, {}, {});".format(g_id, int(boxid_1), int(boxid_2), int(boxid_3))
    db(s)

    return redirect(url_for("admin_summary"))

@app.route("/my_games", methods=["POST", "GET"])
def my_games():
    show_active = request.form.get("active")
    print("activeactive")
    print(show_active)
    s = "SELECT * FROM boxes;"
    games = db(s)
    g_list = [list(game) for game in games]
    pt = "SELECT pay_type_id, description from pay_type;"
    payout_types = dict(db(pt))
    
    game_list = []
    completed_game_list = []
    available = {}
    user_nums = []

    #### dict of boxid:winner ####
    bw = "SELECT boxid, winner FROM scores ORDER BY score_id ASC;"
    win_dict = dict(db(bw))

    #### dict of box x,y if box is full ####
    bn = "SELECT * FROM boxnums;"
    boxnums = db(bn)
    #print(boxnums)

    u = "SELECT userid, username FROM users;"
    user_dict = dict(db2(u))

    # create dict of boxid:{x:{json}, y:{json}}
    boxnum_x = {}
    boxnum_y = {}
    for b_id in boxnums:
        boxnum_x[b_id[0]] = json.loads(b_id[1])
        boxnum_y[b_id[0]] = json.loads(b_id[2]) 

    for game in g_list:
        count = 0
        gameid = game[0]
        active = game[1]
        box_type = ''
        b_type = game[2]
        if b_type == 1:
            box_type = 'Daily Box'
        elif b_type == 2:
            box_type = 'Custom Box'
        elif b_type == 3:
            box_type = 'Nutcracker'
        elif b_type == None:
            box_type = 'Daily Box'
        box_name = game[3]
        fee = game[4]
        pay_type = payout_types[game[5]]
        gobbler_id = game[6]
        box_index = 0
        if active == 0:
            # find who won
            #w = "SELECT username FROM users WHERE userid = {};".format(find_winning_user(gameid)[0])
            #winner = db(w)[0][0]
            if gameid not in win_dict:
                winner = "multi" # these are cxl'd or every score
            else:
                # total hack, check if string is json format, then it's multi
                if win_dict[gameid][:1] == "{":
                    winner = "multi" # will parse this later...
                else:
                    #w = "SELECT username FROM users WHERE userid = {};".format(win_dict[gameid])
                    #winner = db(w)[0][0]
                    winner = user_dict[int(win_dict[gameid])]
        for box in game[7:]:
            if box == session['userid'] and active == 1:
                if gameid in boxnum_x:
                    h_num = boxnum_x[gameid][str(box_index % 10)]
                    a_num = boxnum_y[gameid][str(box_index // 10)]
                else:
                    h_num = "TBD"
                    a_num = "TBD"
                game_list.append((gameid,box_name,box_index,fee,pay_type,h_num,a_num))

            elif box == session['userid'] and active == 0:
                completed_game_list.append((gameid,box_type,box_name,box_index,fee,pay_type,winner))

            if box == 1 or box == 0:
                count += 1
            box_index += 1
        
        available[game[0]] = count
    
    print(type(show_active))
    total = len(game_list)
    print("total total {}".format(total))
    if show_active == 'True' or show_active == None:
        return render_template("my_games.html", game_list = game_list, available = available, total=total)
    else:
        print("got to my completed list")
        return render_template("my_completed_games.html", game_list = completed_game_list)


@app.route("/completed_games")
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

@app.route("/game_list")
def game_list():
    game_list = get_games([1])

    return render_template("game_list.html", game_list = game_list)

@app.route("/custom_game_list")
@login_required
def custom_game_list():
    game_list = get_games([2,3])

    # sorted(game_list, key=itemgetter(0))
    game_list.sort(key=lambda x: x[0])

    return render_template("custom_game_list.html", game_list = game_list)

@app.route("/display_box", methods=["GET", "POST"])
@login_required
def display_box():
    if request.method == "POST":
        boxid = request.form.get('boxid')
    else:
        boxid = request.args['boxid']
        
    s = "SELECT * FROM boxes where boxid = {};".format(boxid)
    box = list(db(s))[0]
    box_type = box[2]
    box_name = box[3]
    fee = box[4]
    ptype = box[5]
    gobbler_id = box[6]
    payout = payout_calc(ptype, fee)
    #current_user = Session['userid']
    if ptype != 2 and ptype != 5:
        final_payout = fee * 100
    elif ptype == 5:
        final_payout = fee * 10
    elif ptype == 6:
        final_payout = "Satellite"
    else:
        final_payout = None

    if box_type != 1:
        t = "SELECT home, away FROM teams WHERE boxid = {};".format(boxid)
        teams = db(t)
        home = teams[0][0]
        away = teams[0][1]
    else:
        home = 'XXX'
        away = 'YYY'

    away_team = {}
    for i in range(10):
        away_team[str(i)] = ''
    if len(away) == 3:
        away_team['3'] = away[0]
        away_team['4'] = away[1]
        away_team['5'] = away[2]
    else:
        away_team['4'] = away[0]
        away_team['5'] = away[1]


    # create a dict of userid:username
    u = "SELECT userid, username FROM users;"
    user_dict = dict(db(u))

    grid = []
    box_num = 0
    row = 0 
    avail = 0
    # create a list (grid) of 10 lists (rows) of 10 tuples (boxes)
    for _ in range(10):
        l = []
        for x in box[7 + row : 17 + row]:
            if x == 1 or x == 0:
                x = ' '
                avail += 1
            else:
                #s = "SELECT username FROM users where userid = {};".format(x)
                #x = db(s)[0][0]
                x = user_dict[x]
            l.append((box_num, x))
            box_num += 1
        grid.append(l)
        row += 10

    print(grid)

    # get num boxes avail and create list for randomizer
    '''
    avail = 0
    for row in grid:
        for box in row:
            if box[1] == 'Open':
                avail += 1
    '''
    
    xy_string = "SELECT x, y FROM boxnums WHERE boxid = {};".format(boxid)
    if avail != 0 or len(db(xy_string)) == 0:
        num_selection = "Row/Column numbers will be randomly generated once the last box is selected."
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
        xy = db(xy_string)[0]
        x = json.loads(xy[0])
        y = json.loads(xy[1])
            
        winners = calc_winner(boxid)
        if len(winners) == 0 and ptype != 3:
            return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection)
            # return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y, home=home, away=away)

        if (ptype == 2 or ptype == 5 or ptype == 6 or ptype == 7) and len(winners) == 2:
            if ptype == 2:
                final_payment = fee * 100
            elif ptype == 6:
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
            winning_boxnum = int(str(y_winner) + str(x_winner))
            winner = Markup('WINNER</br>')
            grid[y_winner][x_winner] = (winning_boxnum, winner + winning_username)
        
        elif (ptype == 2 or ptype == 5 or ptype == 6) and len(winners) != 2:
            return apology("something went wrong with winner calculations")

        if ptype == 7:
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

        if ptype == 1 and len(winners) == 8:
            final_payment = '' +  str(fee * 10) + ' / ' + str(fee * 30) + ' / ' + str(fee * 10) + ' / ' + str(fee * 50)
            for item in x: 
                if x[item] == int(winners[0]):
                    q1_x_winner = int(item)
                if x[item] == int(winners[2]):
                    q2_x_winner = int(item)
                if x[item] == int(winners[4]):
                    q3_x_winner = int(item)
                if x[item] == int(winners[6]):
                    q4_x_winner = int(item)
            for item in y:
                if y[item] == int(winners[1]):
                    q1_y_winner = int(item)
                if y[item] == int(winners[3]):
                    q2_y_winner = int(item)
                if y[item] == int(winners[5]):
                    q3_y_winner = int(item)
                if y[item] == int(winners[7]):
                    q4_y_winner = int(item)
            q1_winning_username = grid[q1_y_winner][q1_x_winner][1]
            q1_winning_boxnum = int(str(q1_y_winner) + str(q1_x_winner))
            q1_winner = Markup('Q1 WINNER</br>')
            grid[q1_y_winner][q1_x_winner] = (q1_winning_boxnum, q1_winner + q1_winning_username)

            q2_winning_username = grid[q2_y_winner][q2_x_winner][1]
            q2_winning_boxnum = int(str(q2_y_winner) + str(q2_x_winner))
            q2_winner = Markup('Q2 WINNER</br>')
            grid[q2_y_winner][q2_x_winner] = (q2_winning_boxnum, q2_winner + q2_winning_username)

            q3_winning_username = grid[q3_y_winner][q3_x_winner][1]
            q3_winning_boxnum = int(str(q3_y_winner) + str(q3_x_winner))
            q3_winner = Markup('Q3 WINNER</br>')
            grid[q3_y_winner][q3_x_winner] = (q3_winning_boxnum, q3_winner + q3_winning_username)

            q4_winning_username = grid[q4_y_winner][q4_x_winner][1]
            q4_winning_boxnum = int(str(q4_y_winner) + str(q4_x_winner))
            q4_winner = Markup('Q4 WINNER</br>')
            grid[q4_y_winner][q4_x_winner] = (q4_winning_boxnum, q4_winner + q4_winning_username)

        elif ptype == 1 and len(winners) != 8:
            return apology("something went wrong with winner calculations")

        if ptype == 3:
            print("paytype == 3 i'm here")
            s = "SELECT score_num, winning_box FROM everyscore where boxid = {};".format(boxid) ## finish
            winners = db(s)
            max_score_num = 1
            final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10)
            winner_dict = {}
            
            if len(winners) != 0:
                for w in winners:
                    if w[0] >= max_score_num and w[0] < 100:
                        max_score_num = w[0]
                final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10)
    
                for winning_box in winners:
                    print(winning_box)
                    if winning_box[0] < 100:  # regular winners
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += (fee * 3)
                        else:
                            winner_dict[winning_box[1]] = (fee * 3)
                    elif winning_box[0] == 100:  # reverse final winner
                        if winning_box[1] in winner_dict:
                            winner_dict[winning_box[1]] += (fee * 10)
                        else:
                            winner_dict[winning_box[1]] = (fee * 10)
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
                    winner_markup = Markup('</br>{}'.format(cash))
                    grid[int(y_win)][int(x_win)] = (winner_username + winner_markup)
            else:
                final_payout = (fee * 100) - (fee * 10) - (fee * 3)  # total pool - reverse - 0/0 

        winner_dict = {}

        return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, winner_dict=winner_dict)


    if box_type == 1:
        sf = ['' for x in range(10)]
        final_payout = ''
        return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, sf=sf, home=home, away=away, away_team=away_team)
    else:
        print("xy {} {}".format(x,y))
        print("home/away: {} {}".format(home,away))
        final_payout = 'Current Final Payout: ' + str(final_payout)
        return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, away_team=away_team, num_selection=num_selection)


@app.route("/select_box", methods=["GET", "POST"])
@login_required
def select_box():
    boxid = request.form.get('boxid')
    bt = "SELECT box_type, pay_type FROM boxes WHERE boxid = {};".format(boxid)
    box_attr = db(bt)[0]
    box_type = box_attr[0]
    pay_type = box_attr[1]
    box_list = [] # the list of eventual boxes to get this user id
    a = "SELECT {} FROM boxes WHERE boxid = {};".format(box_string(), boxid)
    boxes = db(a)[0]
    rand_list = []
    index = 0
    user_box_count = 0

    # create a list of available boxes by index
    for box in boxes:
        if box == 0 or box == 1:
            rand_list.append(index)
        if (box_type == 3 or pay_type == 5 or pay_type == 6) and box == session['userid']:
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
            if (box_type == 3 or pay_type == 5) and user_box_count >= 10:
                return apology("Really??  This is a 10-man.  10 boxes max.  100/10 = 10")
            elif pay_type == 6 and check_box_limit(session['userid']):
                return apology("Really??  You lost count - you're out of boxes.  Double check with TW to make sure he set you up correctly.")

            elif pay_type == 7 and check_box_limit(session['userid']):
                return apology("Really??  Clearly you lost count.  You didn't win that many satellite boxes.")

            else:
                box_list.append(box_num)
        elif boxes[box_num] == session['userid']:
            # code to undo pick
            # first - if rand_list len == 0, game has started, can't undo
            if len(rand_list) == 0:
                return apology("Really??  numbers were drawn - can't undo now - too late!!")
            if box_type != 3:
                s = "UPDATE boxes SET box{}= 1 WHERE boxid = {};".format(box_num, boxid)
                db(s)
            else:
                box_list.append(box_num) #still append, to eventually set back to 1 on all gobble boxes

        else:
            s = "SELECT username FROM users WHERE userid = {};".format(boxes[box_num])
            box_owner = db(s)[0][0]
            return apology("Really??  Did you not see {} already has this box?".format(box_owner))


    # check balance of user first - then subtract fee
    f = "SELECT fee, box_type FROM boxes WHERE boxid = {};".format(boxid)
    bal = "SELECT balance FROM users WHERE userid = {};".format(session['userid'])
    check = db(f)
    fee = check[0][0]
    # box_type = check[0][1]
    balance = db(bal)[0][0]
    print(fee, balance)

    #if balance < fee * len(box_list) and box_type != 3:
        #return apology("Insufficient Funds")

    if user_box_count + len(box_list) > 10 and (box_type == 3 or pay_type == 5):
        return apology("Really?  This is a 10-man.  10 boxes max.  100/10=10")
    
    elif box_type == 3:
        g = "SELECT gobbler_id FROM boxes WHERE boxid = {};".format(boxid)
        gobbler_id = db(g)[0][0]
        for b in box_list:
            print("boxlist:")
            print(box_list)
            if boxes[b] == session['userid']:
                s = "UPDATE boxes SET box{}={} WHERE gobbler_id = {};".format(b, 1, gobbler_id)
            else:
                s = "UPDATE boxes SET box{}={} WHERE gobbler_id = {};".format(b, session['userid'], gobbler_id)
            db(s)

        # are these the last available boxes?  start the game.
        if len(box_list) == len(rand_list):
            gobs = "SELECT boxid FROM boxes WHERE gobbler_id = {};".format(gobbler_id)
            boxids = db(gobs)
            boxid_list = []
            for box in boxids:
                start_game(box[0])

        return redirect(url_for("display_box", boxid=boxid))


    else:
        for b in box_list:
            # assign box to user
            s = "UPDATE boxes SET box{}={} WHERE boxid = {};".format(b, session['userid'], boxid)
            db(s)

        # update balance
        # new_bal = balance - (fee * len(box_list))
        # bal = "UPDATE users SET balance = {} WHERE userid = {};".format(new_bal, session['userid'])
        # db(bal)

        # are these the last available boxes?  start the game.
        if len(box_list) == len(rand_list):
            start_game(boxid)
            # also, if it's a DB, create a new one
            if box_type == 1:
                create_new_game(box_type, 2, fee)

        return redirect(url_for("display_box", boxid=boxid))

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

@app.route("/enter_every_score", methods=["GET", "POST"])
@login_required
def enter_every_score():
    if request.method == "POST":
        # first check if used buttons, most common
        if request.form.get("HOME_BUTTON"):
            home_button = int(request.form.get("HOME_BUTTON"))
            s = "SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;"
            score_list = db(s)[0]
            score_num = score_list[0] + 1
            home_score = home_button + score_list[1]
            away_score = score_list[2]
        elif request.form.get("AWAY_BUTTON"):
            away_button = int(request.form.get("AWAY_BUTTON"))
            s = "SELECT score_num, x_score, y_score FROM everyscore ORDER BY score_id DESC limit 1;"
            score_list = db(s)[0]
            score_num = score_list[0] + 1
            home_score = score_list[1]
            away_score = away_button + score_list[2]
        else:
            if not request.form.get("home") or not request.form.get("away"):
                return apology("need 2 scores")
            score_num = int(request.form.get("score_num"))
            home_score = int(request.form.get("home"))
            away_score = int(request.form.get("away"))

        b = "SELECT boxid FROM boxes WHERE pay_type = 3 and active = 1;"
        boxid_list = db(b)
        if len(boxid_list) == 0:
            return apology("there are no active every score games")

        '''
        score_num = int(request.form.get("score_num"))
        home_score = int(request.form.get("home"))
        away_score = int(request.form.get("away"))
        '''

        box_list = []
        for entry in boxid_list:
            boxid = entry[0] 
            box_list.append(boxid)
            win_box = find_winning_box(boxid, home_score, away_score)
            boxnum = win_box[0]
            winner = win_box[1]
            f = "SELECT fee FROM boxes WHERE boxid = {};".format(boxid)
            fee = db(f)[0][0]

            s = "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES('{}', '{}', 'Score Change {}', '{}', '{}', '{}', '{}');".format(str(boxid), str(score_num), (fee * 3), str(home_score), str(away_score), str(winner), str(boxnum))
            db(s)

        ### run sanity checks ###
        check_result_list = sanity_checks(box_list)

        s = "SELECT e.boxid, e.score_id, e.score_num, e.x_score, e.y_score, e.score_type, e.winning_box, u.username, u.first_name, u.last_name FROM everyscore e LEFT JOIN users u ON e.winner = u.userid INNER JOIN boxes b ON b.boxid = e.boxid where b.active = 1 and b.pay_type = 3 order by e.boxid, e.score_num, e.score_id;".format(boxid)
        scores = db(s)
        print(scores)

        return render_template("enter_every_score.html", scores=scores, box_list=box_list, check_result_list=check_result_list)

    
    else:
        s = "SELECT e.boxid, e.score_id, e.score_num, e.x_score, e.y_score, e.score_type, e.winning_box, u.username, u.first_name, u.last_name FROM everyscore e LEFT JOIN users u ON e.winner = u.userid INNER JOIN boxes b ON b.boxid = e.boxid where b.active = 1 and b.pay_type = 3 order by e.boxid, e.score_num, e.score_id;"
        scores = db(s)
        print(scores)
        b = "SELECT boxid FROM boxes WHERE pay_type = 3 and active = 1;"
        boxid_list = db(b)
        print("boxid list {}".format(boxid_list))
        if len(boxid_list) == 0:
            return apology("there are no active every score games")
        box_list = []
        for boxid in boxid_list:
            box_list.append(boxid[0])
        check_result_list = sanity_checks(box_list)

        return render_template("enter_every_score.html", scores=scores, box_list=box_list, check_result_list=check_result_list)

@app.route("/delete_score", methods=["POST", "GET"])
@login_required
def delete_score():
    score_id = request.form.get('score_id')
    d = "DELETE FROM everyscore WHERE score_id = {};".format(score_id)
    db(d)
    return redirect(url_for('enter_every_score'))

@app.route("/current_winners/<boxid>", methods=["POST", "GET"])
@login_required
def current_winners(boxid):
    if request.method == "POST":
        return redirect(url_for("display_box", boxid))
    else:
        s = "SELECT e.score_type, e.x_score, e.y_score, e.winning_box, u.username FROM everyscore e LEFT JOIN users u ON e.winner = u.userid WHERE boxid = {} order by e.score_num;".format(boxid)
        scores = db(s)

        return render_template("current_winners.html", scores=scores, boxid=boxid)

@app.route("/end_game", methods=["POST", "GET"])
@login_required
def end_game():
    if request.method == "POST":
        boxid = request.form.get('boxid')
        home_score = request.form.get('home')
        away_score = request.form.get('away')
        
        # find the reverse winner - running function with home/away backward
        rev_box = find_winning_box(boxid, away_score, home_score)
        rev_boxnum = rev_box[0]
        rev_winner = rev_box[1]
        # all reverse score_num are 100
        s = "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES('{}', '100', 'Reverse Final', '{}', '{}', '{}', '{}');".format(str(boxid), str(away_score), str(home_score), str(rev_winner), str(rev_boxnum))
        db(s)

        # find final winner
        final_box = find_winning_box(boxid, home_score, away_score)
        final_boxnum = final_box[0]
        final_winner = final_box[1]
        # all final score_num are 200
        s = "INSERT INTO everyscore(boxid, score_num, score_type, x_score, y_score, winner, winning_box) VALUES('{}', '200', 'Final Score', '{}', '{}', '{}', '{}');".format(str(boxid), str(home_score), str(away_score), str(final_winner), str(final_boxnum)) 
        db(s)

        return redirect(url_for("enter_every_score"))
    else:
        return render_template("end_game.html")
        

@app.route("/enter_custom_scores", methods=["GET", "POST"])
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
            
            s = "INSERT INTO scores({}) VALUES({});".format(c, v)
            db(s)
            # and... make game inactive in db
            inactivate = "UPDATE boxes SET active = 0 WHERE boxid = {};".format(boxid)
            db(inactivate)
            # and... update the winner in db
            p = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
            pay_type = db(p)[0][0]
            if pay_type == 2 or pay_type == 5 or pay_type == 6:
                w = "UPDATE scores SET winner = {} WHERE boxid = {};".format(find_winning_user(boxid)[0], boxid)
                db(w)
            elif pay_type == 1:
                # will save in db as json string of quarter:winner
                wl = find_winning_user(boxid)
                print("wl {}".format(wl))
                j = '{'
                qtr = 1
                for q in wl:
                    j += '"q{}":{}, '.format(qtr,q)
                    qtr += 1
                j = j[:-2] # chop last ", "
                j += '}'
                print(j)
                w = "UPDATE scores SET winner = '{}' WHERE boxid = {};".format(j, boxid)
                db(w)

            elif pay_type == 7:
                wl = find_winning_user(boxid)[0]
                w = "UPDATE scores SET winner = '{}' WHERE boxid = {};".format(wl, boxid)
                db(w)

            return redirect(url_for("admin_summary"))

    else:
        return render_template("enter_custom_scores.html")

# 'threes' dice game
@app.route("/threes", methods=["GET", "POST"])
def threes():
    return render_template("threes.html")

#pickem game stuff below
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

@app.route("/select_pickem_games", methods=["GET", "POST"])
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
 
    return redirect(url_for('pickem_all_picks'))

@app.route("/pickem_game_list", methods=["GET", "POST"])
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

@app.route("/pickem_all_picks", methods=["GET", "POST"])
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

    u = "SELECT userid, username FROM users WHERE active = 1;"
    usernames = dict(db2(u))

    for pick in all_picks:
        username = usernames[pick[1]]
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

    print("eliminated list: {}".format(eliminated_list))
    
    return render_template("pickem_all_picks.html", game_details=game_details, user_picks=user_picks_dict, game_dict=game_dict, current_username=session['username'], tb_dict=tb_dict, winning_user=winning_user, tie_break_log=tie_break_log, winner=winner, crown=crown, eliminated_list=eliminated_list)

@app.route("/enter_pickem_scores", methods=["GET", "POST"])
def enter_pickem_scores():

    if request.method == "POST":
        fav_score = request.form.get('fav')
        dog_score = request.form.get('dog')
        gameid = request.form.get('gameid')

        s = "INSERT INTO pickem.pickem_scores (gameid, fav_score, dog_score) values (%s, %s, %s);"
        db2(s, (int(gameid), int(fav_score), int(dog_score)))
    
    return render_template("enter_pickem_scores.html")

@app.route("/pickem_admin", methods=["GET", "POST"])
def pickem_admin():
    season = 2021

    game_name_list = ["WC 1", "WC 2", "WC 3", "WC 4", "WC 5", "WC 6", "DIV 7", "DIV 8", "DIV 9", "DIV 10", "CONF 11", "CONF 12", "Super Bowl"]
    game_group_list = ["WC-Sat", "WC-Sun", "DIV-Sat", "DIV-Sun", "CONF-NFC", "CONF-AFC", "Super Bowl"]
    return render_template("pickem_admin.html", game_name_list=game_name_list, game_group_list=game_group_list, season=season)

@app.route("/lock_pickem_game", methods=["GET", "POST"])
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

    return redirect(url_for('pickem_admin'))
    

@app.route("/create_pickem_game", methods=["GET", "POST"])
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

    return redirect(url_for('pickem_all_picks'))
    

@app.route("/pickem_payment_status", methods=["GET", "POST"])
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

@app.route("/pickem_mark_paid", methods=["GET", "POST"])
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

    return redirect(url_for('pickem_payment_status')) 

@app.route("/pickem_enable_user", methods=["GET", "POST"])
def pickem_enable_user():
    userid = int(request.form.get("userid"))

    s = "UPDATE users SET is_pickem_user = 1 WHERE userid = %s"
    db2(s, (userid,))

    return redirect(url_for('pickem_admin'))

@app.route("/pickem_rules", methods=["GET", "POST"])
def pickem_rules():
    return render_template("pickem_rules.html")

## test stuff for auto download of scores
@app.route("/get_scores", methods=["GET", "POST"])
def get_scores():
    week = 17
    year = 2020

    team_dict = sref_to_pickem()

    # get list of game ids
    game_list = []
    game_data = Boxscores(week, year)
    for game in game_data.games[str(week) + '-' + str(year)]:
        game_list.append(game['boxscore'])

    # get boxscore objects for each game id
    game_dict = {}
    for game in game_list:
        b = Boxscore(game)
        print(b.home_abbreviation, b.home_points, b.away_abbreviation, b.away_points, b.summary)
        game_dict[game] = b

        gameid = game
        # hometeam = game_data.games[str(week) + '-' + str(year)][gameid]['home_name']
        home_abbr = b.home_abbreviation
        home_score = b.home_points
        # awayteam = game_data.games[str(week) + '-' + str(year)][gameid]['away_name']
        away_abbr = b.away_abbreviation
        away_score = b.away_points
        if len(b.summary['home']) > 0:
            home_q1 = b.summary['home'][0] 
            home_q2 = b.summary['home'][1]
            home_q3 = b.summary['home'][2]
            home_q4 = b.summary['home'][3]
            away_q1 = b.summary['away'][0]
            away_q2 = b.summary['away'][1]
            away_q3 = b.summary['away'][2]
            away_q4 = b.summary['away'][3]
        else:
            home_q1 = 0 
            home_q2 = 0 
            home_q3 = 0
            home_q4 = 0
            away_q1 = 0
            away_q2 = 0
            away_q3 = 0
            away_q4 = 0

    s = "INSERT INTO pickem.pickem_scores_sref (gameid, home_abbr, home_score, away_abbr, away_score, home_q1, home_q2, home_q3, home_q4, away_q1, away_q2, away_q3, away_q4) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"

    db2(s, (gameid, team_dict[home_abbr], home_score, team_dict[away_abbr], away_score, home_q1, home_q2, home_q3, home_q4, away_q1, away_q2, away_q3, away_q4))

    return render_template('get_scores.html', game_list=game_list, game_dict=game_dict, team_dict=team_dict)


# LOGIN routine
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST) 
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        else:
            username = request.form.get("username")
        # query database for username
        # s = "SELECT username, password, userid FROM users WHERE username = '{}'".format(request.form.get("username"))
        s2 = "SELECT username, password, userid, failed_login_count FROM users WHERE username = %s and active = 1"
        # user = db(s)
        user = db2(s2, (username,))
        if len(user) != 0:
            u = user[0][0]
            p = user[0][1]
            uid = user[0][2]
            failures = user[0][3]
            print(u, uid, failures, len(u))

            if failures > 9:
                logging.info("{} - {} just keeps trying to login".format(u, uid))
                return apology("{}x??  man... you really have no clue what your password is..  you're locked out now even if you get it right - good job.  talk to TW (or if you are JZ trying brute force.. just stop - thanks)".format(failures))

            # ensure username exists and password is correct
            if not pwd_context.verify(request.form.get("password"), p):
                failures += 1
                s = "UPDATE users SET failed_login_count = %s WHERE userid = %s;"
                db2(s, (failures, uid))
                logging.info("{} - {} just had failed login attempt {}".format(u, uid, failures))
                print('return invalid username or pwd here')
                if failures == 10:
                    return apology("That's it - you're done.  No more.. talk to TW.. BYE")
                else:
                    return apology(Markup("Failed login attempt {} of 10. <br><br>You're a portly fellow.. a bit long in the waistband?  So what's your pleasure; is it the salty snacks you crave?<br>No, no, no, no... yours is a sweet-tooth.  Oh, you may stray, but you'll always return to your dark master:  the cocoa-bean!<br><br><br>Try BOSCO... or reach out to customer support (TW) to reset.".format(failures)))
        else:
            return apology("username does not exist")

        # remember which user has logged in
        session["userid"] = uid
        session["username"] = u
        print("userid is: {}".format(uid))

        # reset fail count to 0 - you made it!
        s = "UPDATE users SET failed_login_count = 0 WHERE userid = %s;"
        db2(s, (uid,))

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route('/')
@login_required
def index():
    
    grid = init_grid()

    print("*******************")
    print("***")
    print("***")
    print("***    {}".format(session["username"]))
    print("***  just logged in")
    print("***")
    print("***")
    print("*******************")

    logging.info("{} logged in".format(session["username"]))

    return render_template("landing_page.html", grid=grid, x=x_nums, y=y_nums)

# new landing page - redirect btwn pickem & boxes
@app.route("/landing_page", methods=["GET", "POST"])
@login_required
def landing_page():
    return render_template("landing_page.html")

# REGISTER new user
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    return(apology("sorry, closed to new entries.  where were you on tuesday when we could've used you??  too bad."))

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # ensure password was confirmed
        elif not request.form.get("password_confirm"):
            return apology("must confirm password")

        # ensure email was submitted
        elif not request.form.get("email"):
            return apology("must enter email")

        # ensure email was submitted
        elif not request.form.get("first_name"):
            return apology("must enter first name")

        # ensure email was submitted
        elif not request.form.get("last_name"):
            return apology("must enter last name")

        # ensure email was submitted
        elif not request.form.get("mobile"):
            return apology("must enter mobile number")

        # encrypt password
        if request.form.get("password") == request.form.get("password_confirm"):
            hash = pwd_context.hash(request.form.get("password"))
        else:
            return apology("password confirmation does not match")
        print("got here insert user")

        s = "SELECT userid FROM users WHERE username = %s;"
        check_userid = db2(s, (request.form.get("username"),))
        print("check userid found {}".format(check_userid))
        if len(check_userid) > 0:
            return apology("username already exists.  reach out to customer support (aka TW) to have it reset.")

        #insert username & hash into table
        # s = "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile) VALUES('{}', '{}', '{}', 1, 0, '{}', '{}', '{}');".format(request.form.get("username"), hash, request.form.get("email"), request.form.get("first_name"), request.form.get("last_name"), request.form.get("mobile"))
        # db(s)

        s2 = "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile) VALUES(%s, %s, %s, 1, 0, %s, %s, %s);"
        values = (request.form.get("username"), hash, request.form.get("email"), request.form.get("first_name"), request.form.get("last_name"), request.form.get("mobile"))
        db2(s2, values)


        # query database for username
        uid_string = "SELECT userid FROM users WHERE username = '{}'".format(request.form.get("username"))
        #rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        uid = db(uid_string)[0][0]

        # temporary - add money to new user for testing
        bal_update = "UPDATE users SET balance = 100000 WHERE userid = {};".format(uid)
        db(bal_update)
        

        # remember which user has logged in
        session["userid"] = uid
        session["username"] = request.form.get("username")
        print("************")
        print(session["userid"])
        print(session["username"])

        logging.info("{} just registered".format(session["username"]))

        # redirect user to home page
        return redirect(url_for("index"))

    else:
        return render_template("register.html")

@app.route("/user_reset", methods=["GET", "POST"])
def user_reset():
    if request.method == "POST":
        username = request.form.get("username")
    else:
        username = request.args("username")
        
    if not request.form.get("password"):
        return apology("must provide password")

    elif not request.form.get("password_confirm"):
        return apology("must confirm password")

    if request.form.get("password") == request.form.get("password_confirm"):
        hash = pwd_context.hash(request.form.get("password"))
    else:
        return apology("password confirmation does not match")

    s = "UPDATE users SET password = '{}', failed_login_count = 0 WHERE username = '{}';".format(hash, username)
    db(s)

    return redirect(url_for("admin_summary"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # will add in check for admin priv later
    s = "SELECT is_admin FROM users WHERE userid = {};".format(session['userid'])
    print(db(s))
    if db(s)[0][0] == 1:
        pt = "SELECT pay_type_id, description FROM pay_type;"
        payout_type = db(pt)
        return render_template("admin.html", payout_type=payout_type)
    else:
        return apology("Sorry, you're not an admin")

@app.route("/add_money", methods=["GET", "POST"])
def add_money():
    # uid = session.userid # for now, admin adds for user only
    username = request.form.get('username')
    amount = request.form.get('amount')
    # find out current balance
    #b = "SELECT balance FROM users WHERE username = '{}';".format(username)
    b2 = "SELECT balance FROM users WHERE username = %s"
    # balance = db(b)[0][0]
    balance = db2(b2, (username,))[0][0]
    if balance == None:
        balance = 0
    print(balance, type(balance))
    balance += int(amount)
    #s = "UPDATE users SET balance = {} WHERE username = '{}';".format(balance, username)
    s2 = "UPDATE users SET balance = %s WHERE username = %s;"
    #db(s)
    db2(s2, (balance, username))

    return redirect(url_for("admin_summary"))

@app.route("/add_boxes_for_user", methods=["GET", "POST"])
def add_boxes_for_user():
    username = request.form.get('username')
    boxes = request.form.get('boxes')
    if request.form.get('userid') == None:
        u = 'SELECT userid FROM users WHERE username = "{}";'.format(username)
        userid = db(u)[0][0]
    else:
        userid = int(request.form.get('userid'))
    bd = "SELECT * FROM max_boxes"
    max_boxes_dict = db(bd)
    print(max_boxes_dict)
    if len(max_boxes_dict) != 0:
        mbd = dict(max_boxes_dict)
        if userid not in mbd:
            s = 'INSERT INTO max_boxes (userid, max_boxes) VALUES ({}, {});'.format(int(userid), int(boxes))
            db(s)
        else:
            curr_max = mbd[userid]
            s = "UPDATE max_boxes SET max_boxes = {} WHERE userid = {};".format(int(curr_max) + int(boxes), userid)
            db(s)
    else:
        s = "INSERT INTO max_boxes(userid, max_boxes) VALUES ({}, {});".format(int(userid), int(boxes))
        print(s)
        db(s)

    return redirect(url_for("admin_summary"))

@app.route("/payment_status", methods=["GET", "POST"])
def payment_status():
    s = "SELECT userid, username FROM users WHERE active = 1;"
    users_list = db(s)

    p = "SELECT userid, amt_paid FROM users;"
    paid = dict(db(p))
    for item in paid:
        if paid[item] == None:
            paid[item] = 0
    
    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''
    for _ in box_list:
        box_string += _
    box_string = box_string[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1;".format(box_string)
    all_boxes = db(box)
    #print(all_boxes)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10
        for box in game[1:]:
            if box != 0 and box != 1:
                if box in user_box_count.keys():
                    user_box_count[box] += 1
                    user_fees[box] += fee
                else:
                    user_box_count[box] = 1
                    user_fees[box] = fee

    users = []
    print("before {}".format(users_list))
    for user in users_list:
        if user[0] in user_fees:
            users.append(user)
            
    print("after {}".format(users))


    return render_template("payment_status.html", users=users, d=user_box_count, fees=user_fees, paid=paid)

@app.route("/admin_summary", methods=["GET", "POST"])
def admin_summary():
    if request.method == "POST":
        amt = request.form.get('amt_paid')
        userid = request.form.get('userid')
        s = "UPDATE users SET amt_paid = {} WHERE userid = {};".format(amt, userid)
        db(s)

    s = "SELECT userid, username, first_name, last_name, email, mobile, is_admin FROM users where active = 1;"
    users = db(s)

    p = "SELECT userid, amt_paid FROM users;"
    paid = dict(db(p))
    for item in paid:
        if paid[item] == None:
            paid[item] = 0
    print(paid)

    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''
    for _ in box_list:
        box_string += _
    box_string = box_string[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 or boxid between 26 and 36;".format(box_string)
    all_boxes = db(box)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10
            print("fee {}".format(fee))
        for box in game[2:]:
            if box != 0 and box != 1:
                if box in user_box_count.keys():
                    user_box_count[box] += 1
                    user_fees[box] += fee
                else:
                    user_box_count[box] = 1
                    user_fees[box] = fee

    s = "SELECT * FROM max_boxes;"
    mbd = dict(db(s))
    print("mbd")
    print(mbd)
    total_max = 0
    for u in mbd:
        total_max += mbd[u]
              
    return render_template("admin_summary.html", users=users, d=user_box_count, fees=user_fees, paid=paid, mbd=mbd, total_max=total_max)
    

@app.route("/user_details", methods=["GET", "POST"])
def user_details():
    s = "SELECT * FROM users WHERE userid = {};".format(session['userid'])
    
    #    0         1       2     3     4      5      6       7         8        9
    # (userid, username, pswd, first, last, email, mobile, balance, active, isadmin)
    user = db(s)[0]
    user_dict = {'username':user[1], 'first_name':user[3], 'last_name':user[4], 'email':user[5], 'mobile':user[6], 'balance':user[7]}

    return render_template("user_details.html", user_dict = user_dict) 

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        old_pswd = request.form.get('old_password')
        password = request.form.get('password')
        pswd_confirm = request.form.get('password_confirm')
        s = "SELECT password FROM users WHERE userid = {};".format(session['userid'])
        s2 = "SELECT password FROM users WHERE userid = %s;"
        # curr_pswd = db(s)[0][0]
        curr_pswd = db2(s2, (session['userid'],))[0][0]
        print(pwd_context.verify(old_pswd, curr_pswd))
        if pwd_context.verify(old_pswd, curr_pswd):
            if password == pswd_confirm:
                hash = pwd_context.hash(password)
                s = "UPDATE users SET password = '{}' WHERE userid = {};".format(hash, session['userid'])
                s2 = "UPDATE users SET password = %s WHERE userid = %s;"
                # db(s)
                db2(s2, (hash, session['userid']))
                return redirect(url_for('user_details'))
            else:
                return apology("password confirmation does not match")
        else:
            return apology("old password is incorrect")
    else:
        return render_template("reset_password.html")

@app.route("/deactivate_user", methods=["GET", "POST"])
def deactivate_user():
    userid = request.form.get('userid')
    s = "UPDATE users SET active = 0 WHERE userid = {};".format(userid)
    db(s)

    return redirect(url_for("admin_summary"))

# LOGOUT Routine
@app.route("/logout")
def logout():
    #forget any userid
    session.clear()

    #redirect to login
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run()

