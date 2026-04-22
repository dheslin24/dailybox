from flask import Blueprint, flash, redirect, render_template, request, session, url_for, Markup
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required
from passlib.apps import custom_app_context as pwd_context
from email_validator import validate_email, EmailNotValidError
from email_helper import send_email
import config
import json
import requests
import logging

bp = Blueprint('auth', __name__)


# LOGIN routine
@bp.route("/login", methods=["GET", "POST"])
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
        s2 = "SELECT username, password, userid, failed_login_count, is_admin FROM users WHERE username = %s and active = 1"
        # user = db(s)
        user = db2(s2, (username,))
        if len(user) != 0:
            u = user[0][0]
            p = user[0][1]
            uid = user[0][2]
            failures = user[0][3]
            admin = user[0][4]
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
                    return apology(Markup("<img src='https://y.yarn.co/a7d5df02-3cfb-4327-b2fe-d1bc2287187d_text.gif'/><br>Failed login attempt {} of 10. <br><br>You're a portly fellow.. a bit long in the waistband?  So what's your pleasure; is it the salty snacks you crave?<br>No, no, no, no... yours is a sweet-tooth.  Oh, you may stray, but you'll always return to your dark master:  the cocoa-bean!<br><br><br>Try BOSCO... or reach out to customer support (TW) to reset.".format(failures)))
        else:
            return apology("username does not exist")

        # remember which user has logged in
        session["userid"] = uid
        session["username"] = u
        session["is_admin"] = admin
        print("userid is: {}".format(uid))

        # reset fail count to 0 - you made it!
        s = "UPDATE users SET failed_login_count = 0 WHERE userid = %s;"
        db2(s, (uid,))
        session.permanent = True

        # redirect user to home page
        return redirect(url_for("auth.index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@bp.route('/')
@login_required
def index():

    print("*******************")
    print("***")
    print("***")
    print("***    {}".format(session["username"]))
    print("***  just logged in")
    print("***")
    print("***")
    print("*******************")

    logging.info("{} just logged in".format(session["username"]))

    return render_template("landing_page.html")

# new landing page - redirect btwn pickem & boxes
@bp.route("/landing_page", methods=["GET", "POST"])
@login_required
def landing_page():
    return render_template("landing_page.html")

# REGISTER new user
@bp.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    secret = config.captchasecret
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        r = requests.post('https://hcaptcha.com/siteverify', data = {'secret' : secret, 'response' : request.form['h-captcha-response']})
        google_response = json.loads(r.text)


        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        #Makes sure the user ticked the captcha
        elif google_response['success'] == False:
            return apology("so - you're a robot then?  did you not see the click here I'm not a robot thing??")
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

        email = request.form.get("email")
        try:
            # Validate.
            valid = validate_email(email)

            # Update with the normalized form.
            email = valid.email

        except EmailNotValidError as e:
            # email is not valid, exception message is human-readable
            return apology("must use valid email")

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

        s2 = "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile, failed_login_count) VALUES(%s, %s, %s, 1, 0, %s, %s, %s, 0);"
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
        return redirect(url_for("auth.index"))

    else:
        return render_template("register.html")

@bp.route("/user_reset", methods=["GET", "POST"])
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

    return redirect(url_for("admin.admin_summary"))


@bp.route("/user_details", methods=["GET", "POST"])
@login_required
def user_details():
    s = "SELECT * FROM users WHERE userid = {};".format(session['userid'])

    #    0         1       2     3     4      5      6       7         8        9        10         11         12        13       14         15
    # (userid, username, pswd, first, last, email, mobile, balance, amt_paid, active, isadmin, ispickem, failedlogin, isbowl, aliasuserid, image)
    user = db(s)[0]
    print(f"USER! {user}")
    user_dict = {'username':user[1], 'first_name':user[3], 'last_name':user[4], 'email':user[5], 'mobile':user[6], 'balance':user[7]}
    if user[15] != None:
        user_dict['image'] = user[15]
        print(f"userdict image: {user[15]}")

    # get user aliases
    a = "SELECT username, IFNULL(image, '') from users where alias_of_userid = %s;"
    alias_dict = dict(db2(a, (session['userid'], )))

    u = "SELECT username, userid FROM users WHERE alias_of_userid = %s"
    userid_dict = dict(db2(u, (session['userid'], )))

    print(f"userid_dict:  {userid_dict}")
    return render_template("user_details.html", user_dict = user_dict, alias_dict = alias_dict, userid_dict=userid_dict)

@bp.route("/reset_password", methods=["GET", "POST"])
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
                return redirect(url_for('auth.user_details'))
            else:
                return apology("password confirmation does not match")
        else:
            return apology("old password is incorrect")
    else:
        return render_template("reset_password.html")

@bp.route("/deactivate_user", methods=["GET", "POST"])
def deactivate_user():
    userid = request.form.get('userid')
    s = "UPDATE users SET active = 0 WHERE userid = {};".format(userid)
    db(s)

    return redirect(url_for("admin.admin_summary"))

# LOGOUT Routine
@bp.route("/logout")
def logout():
    #forget any userid
    session.clear()

    #redirect to login
    return redirect(url_for("auth.login"))
