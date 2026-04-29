from flask import Blueprint, jsonify, redirect, request, session
from db_accessor.db_accessor import db2
from constants import BOX_TYPE_ID
from utils import login_required, admin_required
from email_helper import send_email
import logging

bp = Blueprint('admin', __name__)


@bp.route("/api/create_alias", methods=["GET"])
@login_required
def api_create_alias():
    boxid = request.args.get('boxid')
    boxnum = request.args.get('boxnum')
    user_dict = dict(db2("SELECT userid, username FROM users;"))
    aliases_result = db2("SELECT userid FROM users WHERE alias_of_userid = %s and active = 1", (session['userid'],))
    user_aliases = []
    if aliases_result:
        for alias in aliases_result:
            user_aliases.append({'username': user_dict[alias[0]], 'userid': alias[0]})
    return jsonify({'boxid': boxid, 'boxnum': boxnum, 'user_aliases': user_aliases})


@bp.route("/api/assign_alias", methods=["POST"])
@login_required
def api_assign_alias():
    data = request.get_json()
    boxid = str(data.get('boxid'))
    boxnum = str(int(data.get('boxnum')) - 1)
    existing_alias = data.get('existing_alias')
    new_alias = data.get('new_alias', '').strip()
    user_aliases = data.get('user_aliases', [])
    user_alias_dict = {u['username']: u['userid'] for u in user_aliases}

    if existing_alias:
        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), existing_alias['userid'], int(boxid)))
    elif new_alias and new_alias in user_alias_dict:
        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), user_alias_dict[new_alias], int(boxid)))
    elif new_alias:
        db2("INSERT INTO users (username, password, first_name, last_name, active, alias_of_userid) values (%s, 'x', 'alias', %s, 1, %s);",
            (new_alias, session['username'], session['userid']))
        new_userid = db2("SELECT userid FROM users WHERE username = %s;", (new_alias,))[0][0]
        db2("UPDATE boxes SET box%s = %s WHERE boxid = %s;", (int(boxnum), int(new_userid), int(boxid)))

    return jsonify({'success': True})


@bp.route("/api/admin", methods=["GET"])
def api_admin():
    if not session.get('userid') or not db2("SELECT is_admin FROM users WHERE userid = %s;", (session['userid'],))[0][0]:
        return jsonify({'error': 'forbidden'}), 403
    payout_types = db2("SELECT pay_type_id, description FROM pay_type;")
    return jsonify({'payout_types': [{'id': r[0], 'description': r[1]} for r in payout_types]})

@bp.route("/create_privategame_code", methods=["POST"])
def create_privategame_code():
    boxid = request.form.get('boxid')
    passcode = request.form.get('passcode')
    admin_id = request.form.get('admin_id')

    db2("INSERT INTO privatepass (boxid, pswd, admin) VALUES (%s, %s, %s);", (boxid, passcode, admin_id))
    db2("UPDATE boxes SET box_type = %s WHERE boxid = %s;", (BOX_TYPE_ID['private'], boxid))

    return redirect('/app/landing_page')


@bp.route("/api/bygzomo", methods=["GET", "POST"])
@login_required
@admin_required
def api_bygzomo():
    if request.method == "GET":
        show_tables = db2("show tables;")
        return jsonify({'tables': [t[0] for t in show_tables]})
    data = request.get_json()
    q = data.get('query', '').strip()
    if not q:
        return jsonify({'result': [], 'error': 'No query provided'})
    try:
        result = db2(q)
        return jsonify({'result': [list(row) for row in (result or [])], 'query': q})
    except Exception as e:
        return jsonify({'result': [], 'error': str(e), 'query': q})


@bp.route("/add_money", methods=["POST"])
def add_money():
    username = request.form.get('username')
    amount = request.form.get('amount')
    balance = db2("SELECT balance FROM users WHERE username = %s", (username,))[0][0]
    if balance is None:
        balance = 0
    balance += int(amount)
    db2("UPDATE users SET balance = %s WHERE username = %s;", (balance, username))

    return redirect('/app/admin_summary')

@bp.route("/add_boxes_for_user", methods=["POST"])
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

    return redirect('/app/admin_summary')

@bp.route("/admin_summary", methods=["POST"])
def admin_summary():
    amt = request.form.get('amt_paid')
    userid = request.form.get('userid')
    db2("UPDATE users SET amt_paid = %s WHERE userid = %s;", (amt, userid))
    return redirect('/app/admin_summary')


@bp.route("/api/admin_summary", methods=["GET"])
def api_admin_summary():
    if not session.get('userid') or not db2("SELECT is_admin FROM users WHERE userid = %s;", (session['userid'],))[0][0]:
        return jsonify({'error': 'forbidden'}), 403
    users = db2("SELECT userid, username, first_name, last_name, last_update, email, mobile, is_admin, alias_of_userid FROM users WHERE active = 1;")
    paid = {u[0]: (u[1] or 0) for u in db2("SELECT userid, amt_paid FROM users;")}
    box_list = ['box' + str(x) + ' ,' for x in range(100)]
    box_string = ''.join(box_list)[:-2]
    all_boxes = db2("SELECT fee, pay_type, {} FROM boxes WHERE active = 1 or boxid between 26 and 36;".format(box_string))
    user_box_count = {}
    user_fees = {}
    for game in all_boxes:
        fee = game[0]
        pay_type = game[1]
        if pay_type in (5, 6, 7):
            fee = fee // 10
        for box in game[2:]:
            if box not in (0, 1):
                user_box_count[box] = user_box_count.get(box, 0) + 1
                user_fees[box] = user_fees.get(box, 0) + fee
    mbd = dict(db2("SELECT * FROM max_boxes;"))
    total_max = sum(mbd.values())
    return jsonify({
        'users': [{'userid': u[0], 'username': u[1], 'first_name': u[2], 'last_name': u[3],
                   'last_update': str(u[4]), 'email': u[5], 'mobile': u[6],
                   'is_admin': u[7], 'alias_of_userid': u[8]} for u in users],
        'box_counts': {str(k): v for k, v in user_box_count.items()},
        'fees': {str(k): v for k, v in user_fees.items()},
        'paid': {str(k): v for k, v in paid.items()},
        'max_boxes': {str(k): v for k, v in mbd.items()},
        'total_max': total_max,
    })

@bp.route("/send_bygemail", methods=["POST"])
@login_required
def send_bygemail():
    userid = request.form.get('userid')
    rcpt = request.form.get('rcpt')
    subject = request.form.get('subject')
    body = request.form.get('body')

    logging.info("sending email for userid: %s to %s", userid, rcpt)

    if userid == 19 or userid == '19':
        send_email(rcpt=rcpt, subj=subject, b_text=body, body_header=subject)

    return redirect('/app/email_users')
