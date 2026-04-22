from flask import Blueprint, flash, redirect, render_template, request, session, url_for, Markup
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required
from email_helper import send_email
import logging

bp = Blueprint('admin', __name__)


@bp.route("/create_alias", methods=["POST", "GET"])
@login_required
def create_alias():
    r = request.form.get('alias_boxnum')
    print(f"alias boxnum: {r}")
    box_tuple = eval(r)
    boxid = box_tuple[0]
    boxnum = box_tuple[1]

    ud_string = "SELECT userid, username FROM users;"
    user_dict = dict(db2(ud_string))

    alias_string = "SELECT userid FROM users WHERE alias_of_userid = {} and active = 1".format(session['userid'])
    aliases_result = db2(alias_string)
    user_aliases = []
    if aliases_result:
        for alias in aliases_result:
            user_aliases.append((user_dict[alias[0]], alias[0]))
    print(f"user_aliases: {user_aliases}")

    return render_template("create_alias.html", boxid=boxid, boxnum=boxnum, user_aliases=user_aliases)


@bp.route("/assign_alias", methods=["POST", "GET"])
@login_required
def assign_alias():
    boxid = str(request.form.get('boxid'))
    boxnum = str(int(request.form.get('boxnum')) - 1) #boxes displayed start at 1.  boxes in db start at 0.

    user_aliases = eval(request.form.get('user_aliases'))
    user_alias_dict = dict(user_aliases)
    print(f"user_alias_dict: {user_alias_dict}")

    if request.form.get('existingAlias'):
        existing_alias = eval(request.form.get('existingAlias'))
    else:
        existing_alias = None

    new_alias = request.form.get('newAliasName')
    print(f"box info: {boxid} {boxnum} {new_alias} {type(existing_alias)} {existing_alias}")

    if existing_alias:
        query = "UPDATE boxes SET box%s = %s WHERE boxid = %s;"
        db2(query, (int(boxnum), existing_alias[1], int(boxid)))

    elif new_alias in user_alias_dict:
        query = "UPDATE boxes SET box%s = %s WHERE boxid = %s;"
        db2(query, (int(boxnum), user_alias_dict[new_alias], int(boxid)))

    elif new_alias:
        new_user_q = "INSERT INTO users (username, password, first_name, last_name, active, alias_of_userid) values (%s, 'x', 'alias', %s, 1, %s);"
        db2(new_user_q, (new_alias, session['username'], session['userid']))

        get_new_user_q = "SELECT userid FROM users WHERE username = %s;"
        new_userid = db2(get_new_user_q, (new_alias,))[0][0]
        print(f"new userid for alias: {new_userid}")

        assign_alias_q = "UPDATE boxes SET box%s = %s WHERE boxid = %s;"
        db2(assign_alias_q, (int(boxnum), int(new_userid), int(boxid)))

    return redirect(url_for("boxes.my_games"))


@bp.route("/admin", methods=["GET", "POST"])
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

@bp.route("/create_privategame_code", methods=["GET", "POST"])
def create_privategame_code():
    boxid = request.form.get('boxid')
    passcode = request.form.get('passcode')
    admin_id = request.form.get('admin_id')

    s = "INSERT INTO privatepass (boxid, pswd, admin) VALUES (%s, %s, %s);"
    db2(s, (boxid, passcode, admin_id))

    # privatize the pool now that there's a code
    s2 = "UPDATE boxes SET box_type = %s WHERE boxid = %s;"
    db2(s2, (BOX_TYPE_ID['private'], boxid))

    # return redirect(url_for(""))
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

    return redirect(url_for("admin.admin_summary"))

@bp.route("/add_boxes_for_user", methods=["GET", "POST"])
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

    return redirect(url_for("admin.admin_summary"))

@bp.route("/admin_summary", methods=["GET", "POST"])
def admin_summary():
    if request.method == "POST":
        amt = request.form.get('amt_paid')
        userid = request.form.get('userid')
        s = "UPDATE users SET amt_paid = {} WHERE userid = {};".format(amt, userid)
        db(s)

    s = "SELECT userid, username, first_name, last_name, last_update, email, mobile, is_admin, alias_of_userid FROM users where active = 1;"
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
    box = "SELECT fee, pay_type, {} FROM boxes WHERE active = 1 or boxid between 26 and 36;".format(box_string) # TODO no way this is still valid
    all_boxes = db(box)
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type == 5 or pay_type == 6 or pay_type == 7:
            fee = fee // 10  # these are 10-man pools
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

    print(f"sending email for userid: {userid}")
    print(rcpt)
    print(subject)
    print(body)

    if userid == 19 or userid == '19':
        message_response = send_email(rcpt=rcpt, subj=subject, b_text=body, body_header=subject)

    return redirect(url_for('admin.email_users', message_response=message_response))
