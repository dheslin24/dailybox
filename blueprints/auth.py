from flask import Blueprint, jsonify, redirect, request, session
from db_accessor.db_accessor import db2
from utils import apology, login_required
from passlib.apps import custom_app_context as pwd_context
from email_validator import validate_email, EmailNotValidError
from email_helper import send_email
import config
import requests
import logging

bp = Blueprint('auth', __name__)



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

    return redirect('/app/admin_summary')



@bp.route("/api/login", methods=["POST"])
def api_login():
    session.clear()
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username:
        return jsonify({"error": "Must provide username"}), 400
    if not password:
        return jsonify({"error": "Must provide password"}), 400

    s = "SELECT username, password, userid, failed_login_count, is_admin FROM users WHERE username = %s and active = 1"
    user = db2(s, (username,))
    if not user:
        return jsonify({"error": "Username does not exist"}), 401

    u, p, uid, failures, admin = user[0]
    if failures > 9:
        return jsonify({"error": "Too many failed attempts — contact TW to unlock"}), 403

    if not pwd_context.verify(password, p):
        failures += 1
        db2("UPDATE users SET failed_login_count = %s WHERE userid = %s;", (failures, uid))
        if failures >= 10:
            return jsonify({"error": "Too many failed attempts — you're locked out, contact TW"}), 403
        return jsonify({"error": f"Incorrect password — attempt {failures} of 10"}), 401

    session["userid"] = uid
    session["username"] = u
    session["is_admin"] = admin
    session.permanent = True
    db2("UPDATE users SET failed_login_count = 0 WHERE userid = %s;", (uid,))
    logging.info("%s just logged in via API", u)
    return jsonify({"success": True, "username": u})


@bp.route("/api/register", methods=["POST"])
def api_register():
    secret = config.captchasecret
    data = request.get_json()

    captcha_token = data.get("captcha_token", "")
    r = requests.post('https://hcaptcha.com/siteverify', data={'secret': secret, 'response': captcha_token})
    captcha_result = r.json()
    if not captcha_result.get("success"):
        return jsonify({"error": "Captcha verification failed — are you a robot?"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    password_confirm = data.get("password_confirm", "")
    email = data.get("email", "").strip()
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    mobile = data.get("mobile", "").strip()

    if not username: return jsonify({"error": "Must provide username"}), 400
    if not password: return jsonify({"error": "Must provide password"}), 400
    if not password_confirm: return jsonify({"error": "Must confirm password"}), 400
    if not email: return jsonify({"error": "Must provide email"}), 400
    if not first_name: return jsonify({"error": "Must provide first name"}), 400
    if not last_name: return jsonify({"error": "Must provide last name"}), 400
    if not mobile: return jsonify({"error": "Must provide mobile number"}), 400
    if password != password_confirm: return jsonify({"error": "Passwords do not match"}), 400

    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError:
        return jsonify({"error": "Must use a valid email address"}), 400

    if db2("SELECT userid FROM users WHERE username = %s;", (username,)):
        return jsonify({"error": "Username already exists — contact TW to reset"}), 400

    hash = pwd_context.hash(password)
    db2(
        "INSERT INTO users(username, password, email, active, is_admin, first_name, last_name, mobile, failed_login_count) VALUES(%s, %s, %s, 1, 0, %s, %s, %s, 0);",
        (username, hash, email, first_name, last_name, mobile)
    )
    uid = db2("SELECT userid FROM users WHERE username = %s;", (username,))[0][0]
    db2("UPDATE users SET balance = 100000 WHERE userid = %s;", (uid,))

    session["userid"] = uid
    session["username"] = username
    session.permanent = True
    logging.info("%s just registered via API", username)
    return jsonify({"success": True, "username": username})


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
                return redirect('/app/user_details')
            else:
                return apology("password confirmation does not match")
        else:
            return apology("old password is incorrect")
    else:
        return redirect('/app/reset_password')

@bp.route("/deactivate_user", methods=["GET", "POST"])
def deactivate_user():
    userid = request.form.get('userid')
    db2("UPDATE users SET active = 0 WHERE userid = %s;", (userid,))
    return redirect('/app/admin_summary')

# LOGOUT Routine
@bp.route("/logout")
def logout():
    #forget any userid
    session.clear()

    #redirect to login
    return redirect('/app/login')
