from flask import Flask, flash, redirect, render_template, request, session, url_for, Markup
from flask_session import Session
#from flask_sslify import SSLify
from passlib.apps import custom_app_context as pwd_context
#from werkzeug.serving import make_ssl_devcert, run_simple
import sys
import random
import json
import config
import mysql.connector
from mysql.connector import errorcode
from functools import wraps

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
print(db_config)

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
    #print(s)
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
    elif pay_type == 3:
        s = 'Every Score Wins {}.  \nReverse Final Wins {}.  \nFinal gets the remainder.'.format(fee * 3, fee * 10)
    else:
        s = 'Payouts for Game Type not yet supported' # will add later date

    return s

def calc_winner(boxid):  # all this does is strip all beginning digits from the scores
    # find pay_type
    pt = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
    pay_type = db(pt)[0][0]
    print(pay_type)

    winner_list = []
    if pay_type == 2 or pay_type == 5:  # final only
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
    # TODO - go thru each score, find in grid
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
    if active == 0:
        s = "SELECT b.boxid, b.box_name, b.fee, pt.description, s.winner FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id LEFT JOIN scores s ON s.boxid = b.boxid WHERE b.active = {} and b.box_type = {};".format(active, box_type)
        games = db(s)
        game_list = [list(game) for game in games]
        for game in game_list:
            w = "SELECT username FROM users WHERE userid = {};".format(game[4])
            username = db(w)[0][0]
            game[4] = username
            
    else:
        s = "SELECT b.boxid, b.box_name, b.fee, pt.description FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id WHERE b.active = {} and b.box_type = {};".format(active, box_type)
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
            w = "SELECT username FROM users WHERE userid = {};".format(find_winning_user(gameid)[0])
            winner = db(w)[0][0]
        for box in game[7:]:
            if box == session['userid'] and active == 1:
                game_list.append((gameid,box_type,box_name,box_index,fee,pay_type))
                '''
                n = "SELECT x, y FROM boxnums WHERE boxid = {};".format(gameid)
                nums = db(n)[0]
                if len(nums) != 0:
                    if box_index < 10:
                        col_index = '0'
                    else:
                        col_index = str(box_index)[-1:]
                    row_index = str(box_index)[:1]
                    x = json.loads(nums[0])
                    y = json.loads(nums[1])
                    h = x[col_index]  # if box 25, you want the value for column 5
                    a = y[row_index]  # if box 25, you want the value for row 2
                    game_list.append((gameid,box_type,box_name,box_index,fee,pay_type,(h,a)))
                else:
                    game_list.append((gameid,box_type,box_name,box_index,fee,pay_type))
                '''
            elif box == session['userid'] and active == 0:
                completed_game_list.append((gameid,box_type,box_name,box_index,fee,pay_type,winner))
                '''
                n = "SELECT x, y FROM boxnums WHERE boxid = {};".format(gameid)
                nums = db(n)[0]
                if len(nums) != 0:
                    if box_index < 10:
                        col_index = '0'                   
                    else:
                        col_index = str(box_index)[-1:]
                    row_index = str(box_index)[:1]
                    x = json.loads(nums[0])
                    y = json.loads(nums[1])
                    print(x,y)
                    h = x[col_index]
                    a = y[row_index]
                    completed_game_list.append((gameid,box_type,box_name,box_index,fee,pay_type,winner,(h,a)))
                else:
                    completed_game_list.append((gameid,box_type,box_name,box_index,fee,pay_type,winner))
                '''
            if box == 1 or box == 0:
                count += 1
            box_index += 1
        available[game[0]] = count
    
    print(type(show_active))
    if show_active == 'True' or show_active == None:
        return render_template("my_games.html", game_list = game_list, available = available)
    else:
        print("got to my completed list")
        return render_template("my_completed_games.html", game_list = completed_game_list)


@app.route("/completed_games")
def completed_games():
    #game_list_d = get_games(1, 0)
    game_list_c = get_games(2, 0)
    #game_list = game_list_d + game_list_c
    game_list = game_list_c
    
    return render_template("completed_games.html", game_list = game_list)

@app.route("/game_list")
def game_list():
    game_list = get_games(1)

    return render_template("game_list.html", game_list = game_list)

@app.route("/custom_game_list")
def custom_game_list():
    game_list = get_games(2)

    return render_template("custom_game_list.html", game_list = game_list)

@app.route("/display_box", methods=["GET", "POST"])
def display_box():
    sf = {'0':'', '1':'', '2':'', '3':'', '4':'S', '5':'F', '6':'', '7':'', '8':'', '9':''}
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
    else:
        final_payment = None

    if box_type != 1:
        t = "SELECT home, away FROM teams WHERE boxid = {};".format(boxid)
        teams = db(t)
        home = teams[0][0]
        away = teams[0][1]

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
                x = 'Open'
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
        num_selection = "Row/Column numbers will be randomly generated once the last box is selected"
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
            return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y, home=home, away=away, sf=sf)

        if (ptype == 2 or ptype == 5) and len(winners) == 2:
            if ptype == 2:
                final_payment = fee * 100
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
        
        elif ptype == 2 and len(winners) != 2:
            return apology("something went wrong with winner calculations")

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
            s = "SELECT score_num, winning_box FROM everyscore where boxid = {};".format(boxid) ## finish
            winners = db(s)
            max_score_num = 1
            final_payout = (int(fee) * 100) - (max_score_num * (fee * 3)) - (fee * 10)
            
            if len(winners) != 0:
                winner_dict = {}
                
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
                    winner_markup = Markup('</br>WINNER</br>{}'.format(cash))
                    grid[int(y_win)][int(x_win)] = (winning_box, winner_username + winner_markup)
            else:
                final_payout = (fee * 100) - (fee * 10) - (fee * 3)  # total pool - reverse - 0/0 

    if box_type == 1:
        sf = ['' for x in range(10)]
        final_payout = ''
        return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, sf=sf)
    else:
        print("xy {} {}".format(x,y))
        final_payout = 'Current Final Payout: ' + str(final_payout)
        return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, final_payout=final_payout, x=x, y=y, home=home, away=away, sf=sf, num_selection=num_selection)


@app.route("/select_box", methods=["GET", "POST"])
def select_box():
    boxid = request.form.get('boxid')
    bt = "SELECT box_type, pay_type FROM boxes WHERE boxid = {};".format(boxid)
    box_attr = db(bt)[0]
    box_type = box_attr[0]
    pay_type = box_attr[1]
    box_list = []
    a = "SELECT {} FROM boxes WHERE boxid = {};".format(box_string(), boxid)
    boxes = db(a)[0]
    rand_list = []
    index = 0
    user_box_count = 0

    # create a list of available boxes by index
    for box in boxes:
        if box == 0 or box == 1:
            rand_list.append(index)
        if (box_type == 3 or pay_type == 5) and box == session['userid']:
            user_box_count += 1
        index += 1

    # randomly pick n boxes from available list above
    if request.form.get('rand') != None:
        rand = request.form.get('rand')
        if int(rand) > len(rand_list):
            return apology("You have requested {} boxes, but only {} available.".format(int(rand), len(rand_list)))
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
                return apology("This is a 10-man.  10 boxes max.")
            else:
                box_list.append(box_num)
        else:
            return apology("Umm.. box already taken")


    # check balance of user first - then subtract fee
    f = "SELECT fee, box_type FROM boxes WHERE boxid = {};".format(boxid)
    b = "SELECT balance FROM users WHERE userid = {};".format(session['userid'])
    check = db(f)
    fee = check[0][0]
    # box_type = check[0][1]
    balance = db(b)[0][0]
    print(fee, balance)

    #if balance < fee * len(box_list) and box_type != 3:
        #return apology("Insufficient Funds")

    if user_box_count + len(box_list) > 10 and (box_type == 3 or pay_type == 5):
        return apology("This is a 10-man.  10 boxes max.")
    
    elif box_type == 3:
        g = "SELECT gobbler_id FROM boxes WHERE boxid = {};".format(boxid)
        gobbler_id = db(g)[0][0]
        for b in box_list:
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
def delete_score():
    score_id = request.form.get('score_id')
    d = "DELETE FROM everyscore WHERE score_id = {};".format(score_id)
    db(d)
    return redirect(url_for('enter_every_score'))

@app.route("/current_winners/<boxid>", methods=["POST", "GET"])
def current_winners(boxid):
    if request.method == "POST":
        return redirect(url_for("display_box", boxid))
    else:
        s = "SELECT e.score_type, e.x_score, e.y_score, e.winning_box, u.username FROM everyscore e LEFT JOIN users u ON e.winner = u.userid WHERE boxid = {} order by e.score_num;".format(boxid)
        scores = db(s)

        return render_template("current_winners.html", scores=scores, boxid=boxid)

@app.route("/end_game", methods=["POST", "GET"])
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
            if pay_type == 2 or pay_type == 5:
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

            return redirect(url_for("admin_summary"))

    else:
        return render_template("enter_custom_scores.html")

# 'threes' dice game
@app.route("/threes", methods=["GET", "POST"])
def threes():
    return render_template("threes.html")
    

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

        # query database for username
        s = "SELECT username, password, userid FROM users WHERE username = '{}'".format(request.form.get("username"))
        user = db(s)
        if len(user) != 0:
            u = user[0][0]
            p = user[0][1]
            uid = user[0][2]
            print(u, uid, len(u))

            # ensure username exists and password is correct
            if not pwd_context.verify(request.form.get("password"), p):
                print('return invalid username or pwd here')
                return apology("Invalid username and/or password. \nReach out to Daily Box customer support to reset.")
        else:
            return apology("username does not exist")

        # remember which user has logged in
        session["userid"] = uid
        session["username"] = u
        print("userid is: {}".format(uid))

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route('/')
@login_required
def index():
    grid = init_grid()

    return render_template("index.html", grid=grid, x=x_nums, y=y_nums)

# REGISTER new user
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

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

        #insert username & hash into table
        s = "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile) VALUES('{}', '{}', '{}', 1, 0, '{}', '{}', '{}');".format(request.form.get("username"), hash, request.form.get("email"), request.form.get("first_name"), request.form.get("last_name"), request.form.get("mobile"))
        db(s)

        # query database for username
        uid_string = "SELECT userid FROM users WHERE username = '{}'".format(request.form.get("username"))
        #rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        uid = db(uid_string)[0][0]

        # temporary - add money to new user for testing
        bal_update = "UPDATE users SET balance = 100000 WHERE userid = {};".format(uid)
        db(bal_update)
        

        # remember which user has logged in
        session["userid"] = uid
        print("************")
        print(session["userid"])

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

    s = "UPDATE users SET password = '{}' WHERE username = '{}';".format(hash, username)
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
    b = "SELECT balance FROM users WHERE username = '{}';".format(username)
    balance = db(b)[0][0]
    if balance == None:
        balance = 0
    print(balance, type(balance))
    balance += int(amount)
    s = "UPDATE users SET balance = {} WHERE username = '{}';".format(balance, username)
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
    box = "SELECT fee, {} FROM boxes WHERE active = 1;".format(box_string)
    all_boxes = db(box)
    #print(all_boxes)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
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
    box = "SELECT fee, {} FROM boxes WHERE active = 1;".format(box_string)
    all_boxes = db(box)
    print(all_boxes)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        for box in game[1:]:
            if box != 0 and box != 1:
                if box in user_box_count.keys():
                    user_box_count[box] += 1
                    user_fees[box] += fee
                else:
                    user_box_count[box] = 1
                    user_fees[box] = fee
    print(user_box_count)
    print(user_fees)
              
    return render_template("admin_summary.html", users=users, d=user_box_count, fees=user_fees, paid=paid)
    

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
        curr_pswd = db(s)[0][0]
        print(pwd_context.verify(old_pswd, curr_pswd))
        if pwd_context.verify(old_pswd, curr_pswd):
            if password == pswd_confirm:
                hash = pwd_context.hash(password)
                s = "UPDATE users SET password = '{}' WHERE userid = {};".format(hash, session['userid'])
                db(s)
                return redirect(url_for('user_details'))
            else:
                return apology("password confirmation does not match")
        else:
            return apology("old password is incorrect")
    else:
        return render_template("reset_password.html")


# LOGOUT Routine
@app.route("/logout")
def logout():
    #forget any userid
    session.clear()

    #redirect to login
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run()

