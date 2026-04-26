from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, Markup
from db_accessor.db_accessor import db2
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
        s = "SELECT username, password, userid, failed_login_count, is_admin FROM users WHERE username = %s and active = 1"
        user = db2(s, (username,))
        if len(user) != 0:
            u = user[0][0]
            p = user[0][1]
            uid = user[0][2]
            failures = user[0][3]
            admin = user[0][4]

            if failures > 9:
                logging.info("%s - %s just keeps trying to login", u, uid)
                return apology("{}x??  man... you really have no clue what your password is..  you're locked out now even if you get it right - good job.  talk to TW (or if you are JZ trying brute force.. just stop - thanks)".format(failures))

            # ensure username exists and password is correct
            if not pwd_context.verify(request.form.get("password"), p):
                failures += 1
                db2("UPDATE users SET failed_login_count = %s WHERE userid = %s;", (failures, uid))
                logging.info("%s - %s just had failed login attempt %s", u, uid, failures)
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

        # reset fail count to 0 - you made it!
        db2("UPDATE users SET failed_login_count = 0 WHERE userid = %s;", (uid,))
        session.permanent = True

        # redirect user to home page
        return redirect(url_for("auth.index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@bp.route('/')
@login_required
def index():
    logging.info("%s just logged in", session["username"])
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

        check_userid = db2("SELECT userid FROM users WHERE username = %s;", (request.form.get("username"),))

        if len(check_userid) > 0:
            return apology("username already exists.  reach out to customer support (aka TW) to have it reset.")

        db2(
            "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile, failed_login_count) VALUES(%s, %s, %s, 1, 0, %s, %s, %s, 0);",
            (request.form.get("username"), hash, request.form.get("email"), request.form.get("first_name"), request.form.get("last_name"), request.form.get("mobile"))
        )

        uid = db2("SELECT userid FROM users WHERE username = %s;", (request.form.get("username"),))[0][0]

        # temporary - add money to new user for testing
        db2("UPDATE users SET balance = 100000 WHERE userid = %s;", (uid,))

        # remember which user has logged in
        session["userid"] = uid
        session["username"] = request.form.get("username")

        logging.info("%s just registered", session["username"])

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

    db2("UPDATE users SET password = %s, failed_login_count = 0 WHERE username = %s;", (hash, username))

    return redirect(url_for("admin.admin_summary"))


@bp.route("/user_details", methods=["GET", "POST"])
@login_required
def user_details():
    #    0         1       2     3     4      5      6       7         8        9        10         11         12        13       14         15
    # (userid, username, pswd, first, last, email, mobile, balance, amt_paid, active, isadmin, ispickem, failedlogin, isbowl, aliasuserid, image)
    user = db2("SELECT * FROM users WHERE userid = %s;", (session['userid'],))[0]
    logging.debug("user_details for userid %s", session['userid'])
    user_dict = {'username':user[1], 'first_name':user[3], 'last_name':user[4], 'email':user[5], 'mobile':user[6], 'balance':user[7]}
    if user[15] != None:
        user_dict['image'] = user[15]

    # get user aliases
    alias_dict = dict(db2("SELECT username, IFNULL(image, '') from users where alias_of_userid = %s;", (session['userid'],)))
    userid_dict = dict(db2("SELECT username, userid FROM users WHERE alias_of_userid = %s", (session['userid'],)))

    return render_template("user_details.html", user_dict = user_dict, alias_dict = alias_dict, userid_dict=userid_dict)

@bp.route("/api/me", methods=["GET"])
def api_me():
    if session.get('userid') is None:
        return jsonify({'logged_in': False}), 200
    return jsonify({
        'logged_in': True,
        'userid': session['userid'],
        'username': session['username'],
        'is_admin': session.get('is_admin', 0),
    })

@bp.route("/api/user_details", methods=["GET"])
@login_required
def api_user_details():
    user = db2("SELECT * FROM users WHERE userid = %s;", (session['userid'],))[0]
    user_dict = {
        'username': user[1],
        'first_name': user[3],
        'last_name': user[4],
        'email': user[5],
        'mobile': user[6],
        'image': user[15],
    }
    aliases = db2(
        "SELECT username, userid, IFNULL(image, '') FROM users WHERE alias_of_userid = %s;",
        (session['userid'],)
    )
    aliases_list = [{'username': a[0], 'userid': a[1], 'image': a[2]} for a in aliases]
    return jsonify({'user': user_dict, 'aliases': aliases_list, 'userid': session['userid']})

@bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        old_pswd = request.form.get('old_password')
        password = request.form.get('password')
        pswd_confirm = request.form.get('password_confirm')
        curr_pswd = db2("SELECT password FROM users WHERE userid = %s;", (session['userid'],))[0][0]
        if pwd_context.verify(old_pswd, curr_pswd):
            if password == pswd_confirm:
                hash = pwd_context.hash(password)
                db2("UPDATE users SET password = %s WHERE userid = %s;", (hash, session['userid']))
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
    db2("UPDATE users SET active = 0 WHERE userid = %s;", (userid,))
    return redirect(url_for("admin.admin_summary"))

# LOGOUT Routine
@bp.route("/logout")
def logout():
    #forget any userid
    session.clear()

    #redirect to login
    return redirect(url_for("auth.login"))
