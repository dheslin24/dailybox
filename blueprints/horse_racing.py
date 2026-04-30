from flask import Blueprint, jsonify, request, session
from db_accessor.db_accessor import db2
from utils import login_required
import logging

bp = Blueprint('horse_racing', __name__)


# ── DB INIT ───────────────────────────────────────────────────────────────────

@bp.route('/api/hr_init_db', methods=['POST'])
def api_hr_init_db():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    db2("""CREATE TABLE IF NOT EXISTS hr_races (
            race_id  INT AUTO_INCREMENT PRIMARY KEY,
            name     VARCHAR(100) NOT NULL,
            race_date DATE,
            status   VARCHAR(20) DEFAULT 'setup'
        )""")
    db2("""CREATE TABLE IF NOT EXISTS hr_entries (
            entry_id      INT AUTO_INCREMENT PRIMARY KEY,
            race_id       INT NOT NULL,
            post_position INT,
            horse_name    VARCHAR(100) NOT NULL,
            is_winner     TINYINT DEFAULT 0
        )""")
    db2("""CREATE TABLE IF NOT EXISTS hr_draft_order (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            race_id    INT NOT NULL,
            user_id    INT NOT NULL,
            pick_order INT NOT NULL,
            UNIQUE KEY uq_race_user  (race_id, user_id),
            UNIQUE KEY uq_race_order (race_id, pick_order)
        )""")
    db2("""CREATE TABLE IF NOT EXISTS hr_picks (
            pick_id  INT AUTO_INCREMENT PRIMARY KEY,
            race_id  INT NOT NULL,
            user_id  INT NOT NULL,
            entry_id INT NOT NULL,
            UNIQUE KEY uq_race_user  (race_id, user_id),
            UNIQUE KEY uq_race_entry (race_id, entry_id)
        )""")
    logging.info("hr_ tables initialised")
    return jsonify({'success': True})


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────────

@bp.route('/api/hr_create_race', methods=['POST'])
def api_hr_create_race():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    name = data.get('name', '').strip()
    race_date = data.get('race_date', '').strip() or None
    if not name:
        return jsonify({'error': 'Race name required'}), 400
    db2("INSERT INTO hr_races (name, race_date, status) VALUES (%s, %s, 'setup')", (name, race_date))
    race_id = db2("SELECT LAST_INSERT_ID()")[0][0]
    logging.info("Created race %s: %s", race_id, name)
    return jsonify({'success': True, 'race_id': race_id})


@bp.route('/api/hr_add_horse', methods=['POST'])
def api_hr_add_horse():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    race_id = data.get('race_id')
    post_position = data.get('post_position')
    horse_name = data.get('horse_name', '').strip()
    if not race_id or not horse_name:
        return jsonify({'error': 'race_id and horse_name required'}), 400
    db2("INSERT INTO hr_entries (race_id, post_position, horse_name) VALUES (%s, %s, %s)",
        (race_id, post_position or None, horse_name))
    return jsonify({'success': True})


@bp.route('/api/hr_delete_horse', methods=['POST'])
def api_hr_delete_horse():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    entry_id = data.get('entry_id')
    db2("DELETE FROM hr_picks  WHERE entry_id = %s", (entry_id,))
    db2("DELETE FROM hr_entries WHERE entry_id = %s", (entry_id,))
    return jsonify({'success': True})


@bp.route('/api/hr_set_draft_order', methods=['POST'])
def api_hr_set_draft_order():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    race_id = data.get('race_id')
    order = data.get('order', [])   # ordered list of user_ids
    if not race_id or not order:
        return jsonify({'error': 'race_id and order required'}), 400
    db2("DELETE FROM hr_draft_order WHERE race_id = %s", (race_id,))
    for slot in order:
        db2("INSERT INTO hr_draft_order (race_id, user_id, pick_order) VALUES (%s, %s, %s)",
            (race_id, slot['user_id'], slot['pick_order']))
    return jsonify({'success': True})


@bp.route('/api/hr_set_race_status', methods=['POST'])
def api_hr_set_race_status():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    race_id = data.get('race_id')
    status = data.get('status')
    if status not in ('setup', 'open', 'locked', 'final'):
        return jsonify({'error': 'invalid status'}), 400
    db2("UPDATE hr_races SET status = %s WHERE race_id = %s", (status, race_id))
    return jsonify({'success': True})


@bp.route('/api/hr_mark_winner', methods=['POST'])
def api_hr_mark_winner():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    race_id = data.get('race_id')
    entry_id = data.get('entry_id')
    if not race_id or not entry_id:
        return jsonify({'error': 'race_id and entry_id required'}), 400
    db2("UPDATE hr_entries SET is_winner = 0 WHERE race_id = %s", (race_id,))
    db2("UPDATE hr_entries SET is_winner = 1 WHERE entry_id = %s AND race_id = %s", (entry_id, race_id))
    db2("UPDATE hr_races SET status = 'final' WHERE race_id = %s", (race_id,))
    return jsonify({'success': True})


@bp.route('/api/hr_users', methods=['GET'])
def api_hr_users():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    rows = db2("""SELECT userid, username, first_name, last_name
                  FROM users WHERE active = 1 AND alias_of_userid IS NULL
                  ORDER BY username""")
    return jsonify({'users': [{'userid': r[0], 'username': r[1],
                               'first_name': r[2], 'last_name': r[3]} for r in rows]})


@bp.route('/api/hr_admin_set_pick', methods=['POST'])
def api_hr_admin_set_pick():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    race_id = data.get('race_id')
    user_id = data.get('user_id')
    entry_id = data.get('entry_id')
    if not race_id or not user_id or not entry_id:
        return jsonify({'error': 'race_id, user_id, and entry_id required'}), 400

    race = db2("SELECT status FROM hr_races WHERE race_id = %s", (race_id,))
    if not race:
        return jsonify({'error': 'Race not found'}), 404
    if race[0][0] != 'open':
        return jsonify({'error': 'Race is not open'}), 400

    if not db2("SELECT 1 FROM hr_draft_order WHERE race_id = %s AND user_id = %s", (race_id, user_id)):
        return jsonify({'error': 'User is not in this draft'}), 400

    if not db2("SELECT 1 FROM hr_entries WHERE entry_id = %s AND race_id = %s", (entry_id, race_id)):
        return jsonify({'error': 'Horse not found in this race'}), 400

    taken = db2("SELECT user_id FROM hr_picks WHERE race_id = %s AND entry_id = %s", (race_id, entry_id))
    if taken and taken[0][0] != user_id:
        return jsonify({'error': 'That horse is already picked by another user'}), 400

    db2("DELETE FROM hr_picks WHERE race_id = %s AND user_id = %s", (race_id, user_id))
    db2("INSERT INTO hr_picks (race_id, user_id, entry_id) VALUES (%s, %s, %s)", (race_id, user_id, entry_id))
    logging.info("Admin set pick: user %s → entry %s in race %s", user_id, entry_id, race_id)
    return jsonify({'success': True})


# ── POOL DATA ─────────────────────────────────────────────────────────────────

@bp.route('/api/hr_races', methods=['GET'])
@login_required
def api_hr_races():
    user_id = session.get('userid')
    is_admin = session.get('is_admin') == 1
    if is_admin:
        rows = db2("SELECT race_id, name, race_date, status FROM hr_races ORDER BY race_id DESC")
    else:
        rows = db2("""SELECT r.race_id, r.name, r.race_date, r.status
                      FROM hr_races r
                      JOIN hr_draft_order d ON d.race_id = r.race_id AND d.user_id = %s
                      ORDER BY r.race_id DESC""", (user_id,))
    return jsonify({'races': [{'race_id': r[0], 'name': r[1],
                               'race_date': str(r[2]) if r[2] else '',
                               'status': r[3]} for r in rows]})


@bp.route('/api/hr_pool', methods=['GET'])
@login_required
def api_hr_pool():
    race_id = request.args.get('race_id', type=int)
    user_id = session.get('userid')
    is_admin = session.get('is_admin') == 1

    if not race_id:
        return jsonify({'error': 'race_id required'}), 400

    in_pool = is_admin or bool(db2(
        "SELECT 1 FROM hr_draft_order WHERE race_id = %s AND user_id = %s", (race_id, user_id)
    ))
    if not in_pool:
        return jsonify({'error': 'You are not in this pool'}), 403

    race_row = db2("SELECT race_id, name, race_date, status FROM hr_races WHERE race_id = %s", (race_id,))
    if not race_row:
        return jsonify({'error': 'Race not found'}), 404
    race = {'race_id': race_row[0][0], 'name': race_row[0][1],
            'race_date': str(race_row[0][2]) if race_row[0][2] else '',
            'status': race_row[0][3]}

    # Horses with pick info
    entry_rows = db2("""SELECT e.entry_id, e.post_position, e.horse_name, e.is_winner,
               p.user_id, u.username
        FROM hr_entries e
        LEFT JOIN hr_picks p ON p.entry_id = e.entry_id AND p.race_id = %s
        LEFT JOIN users u ON u.userid = p.user_id
        WHERE e.race_id = %s
        ORDER BY e.post_position ASC, e.entry_id ASC""", (race_id, race_id))
    entries = [{'entry_id': r[0], 'post_position': r[1], 'horse_name': r[2],
                'is_winner': bool(r[3]), 'picked_by': r[4], 'picked_by_name': r[5]}
               for r in entry_rows]

    # Draft order with pick info
    draft_rows = db2("""SELECT d.pick_order, d.user_id, u.username, p.entry_id, e.horse_name
        FROM hr_draft_order d
        JOIN  users u ON u.userid = d.user_id
        LEFT JOIN hr_picks p ON p.user_id = d.user_id AND p.race_id = %s
        LEFT JOIN hr_entries e ON e.entry_id = p.entry_id
        WHERE d.race_id = %s
        ORDER BY d.pick_order ASC""", (race_id, race_id))
    draft_order = [{'pick_order': r[0], 'user_id': r[1], 'username': r[2],
                    'has_picked': r[3] is not None, 'entry_id': r[3], 'horse_name': r[4]}
                   for r in draft_rows]

    on_clock = next((d for d in draft_order if not d['has_picked']), None)

    user_pick_row = db2("""SELECT p.entry_id, e.horse_name
                           FROM hr_picks p JOIN hr_entries e ON e.entry_id = p.entry_id
                           WHERE p.race_id = %s AND p.user_id = %s""", (race_id, user_id))
    current_user_pick = {'entry_id': user_pick_row[0][0], 'horse_name': user_pick_row[0][1]} \
                        if user_pick_row else None

    winner_entry = next((e for e in entries if e['is_winner']), None)
    winner = None
    if winner_entry:
        winner_picker = next((d for d in draft_order if d['entry_id'] == winner_entry['entry_id']), None)
        winner = {'horse_name': winner_entry['horse_name'],
                  'username': winner_picker['username'] if winner_picker else '(unclaimed)'}

    return jsonify({
        'race': race,
        'entries': entries,
        'draft_order': draft_order,
        'on_clock': on_clock,
        'is_on_clock': on_clock is not None and on_clock['user_id'] == user_id,
        'current_user_pick': current_user_pick,
        'winner': winner,
        'is_admin': is_admin,
    })


@bp.route('/api/hr_pick', methods=['POST'])
@login_required
def api_hr_pick():
    user_id = session.get('userid')
    data = request.get_json()
    race_id = data.get('race_id')
    entry_id = data.get('entry_id')
    if not race_id or not entry_id:
        return jsonify({'error': 'race_id and entry_id required'}), 400

    race = db2("SELECT status FROM hr_races WHERE race_id = %s", (race_id,))
    if not race or race[0][0] != 'open':
        return jsonify({'error': 'Race is not open for picks'}), 400

    if not db2("SELECT 1 FROM hr_draft_order WHERE race_id = %s AND user_id = %s", (race_id, user_id)):
        return jsonify({'error': 'You are not in this draft'}), 403

    on_clock = db2("""SELECT d.user_id FROM hr_draft_order d
                      WHERE d.race_id = %s
                        AND d.user_id NOT IN (SELECT user_id FROM hr_picks WHERE race_id = %s)
                      ORDER BY d.pick_order ASC LIMIT 1""", (race_id, race_id))
    if not on_clock or on_clock[0][0] != user_id:
        return jsonify({'error': "It's not your turn yet"}), 400

    if not db2("SELECT 1 FROM hr_entries WHERE entry_id = %s AND race_id = %s", (entry_id, race_id)):
        return jsonify({'error': 'Horse not found in this race'}), 400

    try:
        db2("INSERT INTO hr_picks (race_id, user_id, entry_id) VALUES (%s, %s, %s)",
            (race_id, user_id, entry_id))
    except Exception:
        return jsonify({'error': 'That horse was just taken — please pick another'}), 400

    logging.info("User %s picked entry %s in race %s", user_id, entry_id, race_id)
    return jsonify({'success': True})
