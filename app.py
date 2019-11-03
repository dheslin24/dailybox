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
    '''
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    '''
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
        s = 'Single Winner - {}'.format(fee * 100)
    else:
        s = 'Payouts for Game Type not yet supported' # will add later date

    return s

def calc_winner(boxid):
    # find pay_type
    pt = "SELECT pay_type FROM boxes WHERE boxid = {};".format(boxid)
    pay_type = db(pt)[0][0]
    print(pay_type)

    winner_list = []
    if pay_type == 2:  # final only
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
    print(winner_list)
    return winner_list
        

#@app.route("/start_game", methods=["POST", "GET"])
def start_game(boxid):
    avail = count_avail(boxid)
    s = "SELECT box_type from boxes WHERE boxid = {};".format(boxid)
    box_type = db(s)[0][0]
    print("boxtype in start game {}".format(box_type))
    if avail == 0:
        assign_numbers(boxid) # this assigns the row/col numbers
        if box_type == 1:  # this is a dailybox, so generate the winning numbers as well
            print("got here dailybox start game")
            winning_col = random.randint(0,9)
            winning_row = random.randint(0,9)
            scores = "INSERT INTO scores(boxid, x4, y4) VALUES('{}', '{}', '{}');".format(boxid, winning_col, winning_row)
            db(scores)
    else:
        print("tried to start game, but boxes still available")
        return apology("Cannot start game - still boxes available")
    

def get_games(box_type):
    s = "SELECT b.boxid, b.box_name, b.fee, pt.description FROM boxes b LEFT JOIN pay_type pt ON b.pay_type = pt.pay_type_id WHERE b.active = 1 and b.box_type = {};".format(box_type)
    games = db(s)
    game_list = [list(game) for game in games]
    print(game_list)
    a = "SELECT * FROM boxes WHERE active = 1;"
    avail = db(a)

    available = {}
    for game in avail:
        count = 0
        for x in game[:len(game)-101:-1]:
            if x == 1 or x == 0:
                count += 1
        available[game[0]] = count

    # add the avail spots to the list that is passed to display game list
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
        print("yoyoyoyyo")
        print(max_box)
        box_name = "db" + str(max_box + 1)
        print("boxnameboxname {}".format(box_name))
    else:
        box_name = request.form.get('box_name')
    
    box_type = request.form.get('box_type')
    pay_type = request.form.get('pay_type')
    # create string of c = columns to update
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
    return redirect(url_for("index"))

@app.route("/my_games")
def my_games():
    s = "SELECT * FROM boxes;"
    games = db(s)
    g_list = [list(game) for game in games]
    pt = "SELECT pay_type_id, description from pay_type;"
    payout_types = dict(db(pt))
    
    game_list = []
    available = {}
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
        elif b_type == None:
            box_type = 'Daily Box'
        box_name = game[3]
        fee = game[4]
        pay_type = payout_types[game[5]]
        box_index = 0
        for box in game[6:]:
            if box == session['userid'] and active == 1:
                game_list.append((gameid,box_type,box_name,box_index,fee,pay_type))
            if box == 1 or box == 0:
                count += 1
            box_index += 1
        available[game[0]] = count
    
    return render_template("my_games.html", game_list = game_list, available = available)
    

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
    if request.method == "POST":
        boxid = request.form.get('boxid')
    else:
        boxid = request.args['boxid']
        
    s = "SELECT * FROM boxes where boxid = {};".format(boxid)
    box = list(db(s))[0]
    box_name = box[3]
    fee = box[4]
    ptype = box[5]
    payout = payout_calc(ptype, fee)

    grid = []
    box_num = 0
    row = 0 
    # create a list (grid) of 10 lists (rows) of 10 tuples (boxes)
    for _ in range(10):
        l = []
        for x in box[6 + row : 16 + row]:
            if x == 1 or x == 0:
                x = 'Open'
            else:
                s = "SELECT username FROM users where userid = {};".format(x)
                x = db(s)[0][0]
            l.append((box_num, x))
            box_num += 1
        grid.append(l)
        row += 10

    print(grid)

    # get num boxes avail and create list for randomizer
    avail = 0
    for row in grid:
        for box in row:
            if box[1] == 'Open':
                avail += 1
    
    xy_string = "SELECT x, y FROM boxnums WHERE boxid = {};".format(boxid)
    if avail != 0 or len(db(xy_string)) == 0:
        x = ['x' for x in range(10)]
        x.insert(0,' ')
        y = ['y' for y in range(10)]

    # gets row/column numbers and finds winner
    else:
        xy = db(xy_string)[0]
        x = json.loads(xy[0])
        y = json.loads(xy[1])
            
        winners = calc_winner(boxid)
        if len(winners) == 0:
            return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y)

        if ptype == 2 and len(winners) == 2:
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

    return render_template("display_box.html", grid=grid, boxid=boxid, box_name = box_name, fee=fee, avail=avail, payout=payout, x=x, y=y)

@app.route("/select_box", methods=["GET", "POST"])
def select_box():
    boxid = request.form.get('boxid')
    box_list = []
    a = "SELECT {} FROM boxes WHERE boxid = {};".format(box_string(), boxid)
    boxes = db(a)[0]
    rand_list = []
    index = 0

    # create a list of available boxes by index
    for box in boxes:
        if box == 0 or box == 1:
            rand_list.append(index)
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
            box_list.append(box_num)
        else:
            return apology("Umm.. box already taken")


    # check balance of user first - then subtract fee
    f = "SELECT fee FROM boxes WHERE boxid = {};".format(boxid)
    b = "SELECT balance FROM users WHERE userid = {};".format(session['userid'])
    fee = db(f)[0][0]
    balance = db(b)[0][0]
    print(fee, balance)

    if balance < fee * len(box_list):
        return apology("Insufficient Funds")
    else:
        for b in box_list:
            # assign box to user
            s = "UPDATE boxes SET box{}={} WHERE boxid = {};".format(b, session['userid'], boxid)
            db(s)

        # update balance
        new_bal = balance - (fee * len(box_list))
        bal = "UPDATE users SET balance = {} WHERE userid = {};".format(new_bal, session['userid'])
        db(bal)

        # are these the last available boxes?  start the game.
        if len(box_list) == len(rand_list):
            start_game(boxid)

        return redirect(url_for("display_box", boxid=boxid))

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
            return redirect(url_for("admin_summary"))

    else:
        return render_template("enter_custom_scores.html")
    

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

        # encrypt password
        if request.form.get("password") == request.form.get("password_confirm"):
            hash = pwd_context.hash(request.form.get("password"))
        else:
            return apology("password confirmation does not match")
        print("got here insert user")

        #insert username & hash into table
        s = "INSERT INTO users(username, password, email) VALUES('{}', '{}', '{}');".format(request.form.get("username"), hash, request.form.get("email"))
        db(s)

        # query database for username
        uid_string = "SELECT userid FROM users WHERE username = '{}'".format(request.form.get("username"))
        #rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        uid = db(uid_string)[0][0]

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
    print(balance, type(balance))
    balance += int(amount)
    s = "UPDATE users SET balance = {} WHERE username = '{}';".format(balance, username)
    db(s)

    return redirect(url_for("admin_summary"))

@app.route("/admin_summary", methods=["GET", "POST"])
def admin_summary():
    s = "SELECT userid, username, first_name, last_name, email, mobile, balance, active, is_admin FROM users;"
    users = db(s)

    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''
    for _ in box_list:
        box_string += _
    box_string = box_string[:-2]
    box = "SELECT {} FROM boxes WHERE active = 1;".format(box_string)
    all_boxes = db(box)
    d = {}
    for game in all_boxes:
        for box in game:
            if box != 0 and box != 1:
                if box in d.keys():
                    d[box] += 1
                else:
                    d[box] = 1
    print(d)
              
    return render_template("admin_summary.html", users=users, d=d)
    

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

