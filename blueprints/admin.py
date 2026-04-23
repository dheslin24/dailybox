from flask import Blueprint, flash, redirect, render_template, request, session, url_for, Markup
from db_accessor.db_accessor import db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required
from email_helper import send_email
import logging

bp = Blueprint('admin', __name__)


@bp.route("/create_alias", methods=["POST", "GET"])
@login_required
def create_alias():
    r = request.form.get('alias_boxnum')
    box_tuple = eval(r)
    boxid = box_tuple[0]
    boxnum = box_tuple[1]

    user_dict = dict(db2("SELECT userid, username FROM users;"))

    aliases_result = db2("SELECT userid FROM users WHERE alias_of_userid = %s and active = 1", (session['userid'],))
    user_aliases = []
    if aliases_result:
        for alias in aliases_result:
            user_aliases.append((user_dict[alias[0]], alias[0]))

    return render_template("create_alias.html", boxid=boxid, boxnum=boxnum, user_aliases=user_aliases)


@bp.route("/assign_alias", methods=["POST", "GET"])
@login_required
def assign_alias():
    boxid = str(request.form.get('boxid'))
    boxnum = str(int(request.form.get('boxnum')) - 1) #boxes displayed start at 1.  boxes in db start at 0.

    user_aliases = eval(request.form.get('user_aliases'))
    user_alias_dict = dict(user_aliases)

    if request.form.get('existingAlias'):
        existing_alias = eval(request.form.get('existingAlias'))
    else:
        existing_alias = None

    new_alias = request.form.get('newAliasName')

    if existing_alias:
        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), existing_alias[1], int(boxid)))

    elif new_alias in user_alias_dict:
        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), user_alias_dict[new_alias], int(boxid)))

    elif new_alias:
        db2("INSERT INTO users (username, password, first_name, last_name, active, alias_of_userid) values (%s, 'x', 'alias', %s, 1, %s);",
            (new_alias, session['username'], session['userid']))

        new_userid = db2("SELECT userid FROM users WHERE username = %s;", (new_alias,))[0][0]
        logging.info("new alias userid: %s", new_userid)

        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), int(new_userid), int(boxid)))

    return redirect(url_for("boxes.my_games"))


@bp.route("/admin", methods=["GET", "POST"])
def admin():
    is_admin = db2("SELECT is_admin FROM users WHERE userid = %s;", (session['userid'],))
    if is_admin and is_admin[0][0] == 1:
        payout_type = db2("SELECT pay_type_id, description FROM pay_type;")
        return render_template("admin.html", payout_type=payout_type)
    else:
        return apology("Sorry, you're not an admin")

@bp.route("/create_privategame_code", methods=["GET", "POST"])
def create_privategame_code():
    boxid = request.form.get('boxid')
    passcode = request.form.get('passcode')
    admin_id = request.form.get('admin_id')

    db2("INSERT INTO privatepass (boxid, pswd, admin) VALUES (%s, %s, %s);", (boxid, passcode, admin_id))
    db2("UPDATE boxes SET box_type = %s WHERE boxid = %s;", (BOX_TYPE_ID['private'], boxid))

    return render_template("landing_page.html")

@bp.route("/bygzomo", methods=["GET", "POST"])
@login_required
@admin_required
def bygzomo():
    show_tables = db2("show tables;")

    if request.method == "POST":
        q = request.form.get('query')
        result = db2(q)
    else:
        q = ''
        result = ''
    return render_template("bygzomo.html", result=result, q=q, show_tables=show_tables)


@bp.route("/add_money", methods=["GET", "POST"])
def add_money():
    username = request.form.get('username')
    amount = request.form.get('amount')
    balance = db2("SELECT balance FROM users WHERE username = %s", (username,))[0][0]
    if balance is None:
        balance = 0
    balance += int(amount)
    db2("UPDATE users SET balance = %s WHERE username = %s;", (balance, username))

    return redirect(url_for("admin.admin_summary"))

@bp.route("/add_boxes_for_user", methods=["GET", "POST"])
def add_boxes_for_user():
    username = request.form.get('username')
    boxes = request.form.get('boxes')
    if request.form.get('userid') is None:
        userid = db2("SELECT userid FROM users WHERE username = %s;", (username,))[0][0]
    else:
        userid = int(request.form.get('userid'))
    max_boxes_dict = db2("SELECT * FROM max_boxes")
    if len(max_boxes_dict) != 0:
        mbd = dict(max_boxes_dict)
        if userid not in mbd:
            db2("INSERT INTO max_boxes (userid, max_boxes) VALUES (%s, %s);", (int(userid), int(boxes)))
        else:
            curr_max = mbd[userid]
            db2("UPDATE max_boxes SET max_boxes = %s WHERE userid = %s;", (int(curr_max) + int(boxes), userid))
    else:
        db2("INSERT INTO max_boxes(userid, max_boxes) VALUES (%s, %s);", (int(userid), int(boxes)))

    return redirect(url_for("admin.admin_summary"))

@bp.route("/admin_summary", methods=["GET", "POST"])
def admin_summary():
    if request.method == "POST":
        amt = request.form.get('amt_paid')
        userid = request.form.get('userid')
        db2("UPDATE users SET amt_paid = %s WHERE userid = %s;", (amt, userid))

    users = db2("SELECT userid, username, first_name, last_name, last_update, email, mobile, is_admin, alias_of_userid FROM users where active = 1;")

    paid = dict(db2("SELECT userid, amt_paid FROM users;"))
    for item in paid:
        if paid[item] is None:
            paid[item] = 0

    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''
    for _ in box_list:
        box_string += _
    box_string = box_string[:-2]
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 or boxid between 26 and 36;".format(box_string)
    all_boxes = db2(box)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10  # these are 10-man pools
        for box in game[2:]:
            if box != 0 and box != 1:
                if box in user_box_count.keys():
                    user_box_count[box] += 1
                    user_fees[box] += fee
                else:
                    user_box_count[box] = 1
                    user_fees[box] = fee

    mbd = dict(db2("SELECT * FROM max_boxes;"))
    logging.debug("max_boxes_dict: %s", mbd)
    total_max = sum(mbd.values())

    return render_template("admin_summary.html", users=users, d=user_box_count, fees=user_fees, paid=paid, mbd=mbd, total_max=total_max)


@bp.route("/email_users", methods=["GET", "POST"])
@login_required
def email_users():
    if request.args['message_response']:
        message_response = request.args['message_response']
    else:
        message_response = ''

    return render_template("email_users.html", message_response=message_response)

@bp.route("/send_bygemail", methods=["GET", "POST"])
@login_required
def send_bygemail():
    userid = request.form.get('userid')
    rcpt = request.form.get('rcpt')
    subject = request.form.get('subject')
    body = request.form.get('body')

    logging.info("sending email for userid: %s to %s", userid, rcpt)

    if userid == 19 or userid == '19':
        message_response = send_email(rcpt=rcpt, subj=subject, b_text=body, body_header=subject)

    return redirect(url_for('admin.email_users', message_response=message_response))
