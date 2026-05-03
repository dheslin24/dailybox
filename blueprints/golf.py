from flask import Blueprint, jsonify, request, session
from db_accessor.db_accessor import db2
from utils import login_required, api_admin_required
from services.espn_client import get_golf_tournaments, get_golf_event_detail
import logging
import random

bp = Blueprint('golf', __name__)


def _compute_snake_sequence(base_order, picks_per_user):
    """Return a list of user_ids for each overall draft position (snake order).
    base_order: list of user_ids ordered by pick_order 1..N."""
    n = len(base_order)
    sequence = []
    for pick_num in range(1, n * picks_per_user + 1):
        round_idx = (pick_num - 1) // n       # 0-indexed round
        pos_in_round = (pick_num - 1) % n     # 0-indexed position within round
        if round_idx % 2 == 0:                # even rounds: forward
            sequence.append(base_order[pos_in_round])
        else:                                  # odd rounds: reverse
            sequence.append(base_order[n - 1 - pos_in_round])
    return sequence


# ── DB INIT ───────────────────────────────────────────────────────────────────

@bp.route('/api/golf_init_db', methods=['POST'])
@api_admin_required
def api_golf_init_db():
    db2("""CREATE TABLE IF NOT EXISTS golf_events (
            event_id       INT AUTO_INCREMENT PRIMARY KEY,
            name           VARCHAR(100) NOT NULL,
            espn_event_id  VARCHAR(50)  NOT NULL,
            course         VARCHAR(100),
            event_date     DATE,
            status         VARCHAR(20)  DEFAULT 'setup'
        )""")
    db2("""CREATE TABLE IF NOT EXISTS golf_pools (
            pool_id        INT AUTO_INCREMENT PRIMARY KEY,
            event_id       INT NOT NULL,
            name           VARCHAR(100) NOT NULL,
            fee            VARCHAR(50)  DEFAULT '',
            status         VARCHAR(20)  DEFAULT 'setup',
            pool_format    VARCHAR(20)  DEFAULT 'draft',
            picks_per_user INT          DEFAULT 4,
            draft_type     VARCHAR(20)  DEFAULT 'manual'
        )""")
    db2("""CREATE TABLE IF NOT EXISTS golf_draft_order (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            pool_id    INT NOT NULL,
            user_id    INT NOT NULL,
            pick_order INT NOT NULL,
            paid       TINYINT DEFAULT 0,
            UNIQUE KEY uq_pool_user  (pool_id, user_id),
            UNIQUE KEY uq_pool_order (pool_id, pick_order)
        )""")
    db2("""CREATE TABLE IF NOT EXISTS golf_picks (
            pick_id         INT AUTO_INCREMENT PRIMARY KEY,
            pool_id         INT          NOT NULL,
            user_id         INT          NOT NULL,
            player_espn_id  VARCHAR(50)  NOT NULL,
            player_name     VARCHAR(100) NOT NULL,
            draft_position  INT          NOT NULL,
            is_tiebreaker   TINYINT      DEFAULT 0,
            pick_type       VARCHAR(20)  DEFAULT 'primary',
            UNIQUE KEY uq_pool_user_player (pool_id, user_id, player_espn_id)
        )""")
    logging.info("golf_ tables initialised")
    return jsonify({'success': True})


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────────

@bp.route('/api/golf_espn_events', methods=['GET'])
@api_admin_required
def api_golf_espn_events():
    events = get_golf_tournaments()
    return jsonify({'events': events})


@bp.route('/api/golf_users', methods=['GET'])
@api_admin_required
def api_golf_users():
    rows = db2("""SELECT userid, username, first_name, last_name
                  FROM users WHERE active = 1 AND alias_of_userid IS NULL
                  ORDER BY username""")
    return jsonify({'users': [{'userid': r[0], 'username': r[1],
                               'first_name': r[2], 'last_name': r[3]} for r in rows]})


@bp.route('/api/golf_create_pool', methods=['POST'])
@api_admin_required
def api_golf_create_pool():
    data = request.get_json()
    espn_event_id = str(data.get('espn_event_id', '')).strip()
    event_name    = data.get('event_name', '').strip()
    course        = data.get('course', '').strip() or None
    event_date    = data.get('event_date', '').strip() or None
    pool_name     = data.get('pool_name', '').strip()
    fee           = data.get('fee', '').strip()
    pool_format   = data.get('pool_format', 'draft')
    draft_type    = data.get('draft_type', 'manual')
    picks_per_user = int(data.get('picks_per_user', 4))

    if not espn_event_id or not event_name or not pool_name:
        return jsonify({'error': 'espn_event_id, event_name, and pool_name required'}), 400
    if pool_format not in ('draft', 'async'):
        return jsonify({'error': 'invalid pool_format'}), 400

    existing = db2("SELECT event_id FROM golf_events WHERE espn_event_id = %s", (espn_event_id,))
    if existing:
        event_id = existing[0][0]
        db2("UPDATE golf_events SET name=%s, course=%s, event_date=%s WHERE event_id=%s",
            (event_name, course, event_date, event_id))
    else:
        db2("INSERT INTO golf_events (name, espn_event_id, course, event_date, status) VALUES (%s,%s,%s,%s,'setup')",
            (event_name, espn_event_id, course, event_date))
        event_id = db2("SELECT LAST_INSERT_ID()")[0][0]

    db2("""INSERT INTO golf_pools (event_id, name, fee, status, pool_format, picks_per_user, draft_type)
           VALUES (%s,%s,%s,'setup',%s,%s,%s)""",
        (event_id, pool_name, fee, pool_format, picks_per_user, draft_type))
    pool_id = db2("SELECT LAST_INSERT_ID()")[0][0]

    logging.info("Created golf pool %s (%s) for event %s", pool_id, pool_name, event_id)
    return jsonify({'success': True, 'pool_id': pool_id, 'event_id': event_id})


@bp.route('/api/golf_admin_pools', methods=['GET'])
@api_admin_required
def api_golf_admin_pools():
    rows = db2("""SELECT p.pool_id, p.name, p.fee, p.status, p.pool_format,
                         p.picks_per_user, p.draft_type,
                         e.event_id, e.name, e.espn_event_id, e.course, e.event_date
                  FROM golf_pools p
                  JOIN golf_events e ON e.event_id = p.event_id
                  ORDER BY p.pool_id DESC""")
    return jsonify({'pools': [
        {'pool_id': r[0], 'name': r[1], 'fee': r[2], 'status': r[3],
         'pool_format': r[4], 'picks_per_user': r[5], 'draft_type': r[6],
         'event_id': r[7], 'event_name': r[8], 'espn_event_id': r[9],
         'course': r[10] or '', 'event_date': str(r[11]) if r[11] else ''}
        for r in rows]})


@bp.route('/api/golf_set_draft_order', methods=['POST'])
@api_admin_required
def api_golf_set_draft_order():
    data = request.get_json()
    pool_id = data.get('pool_id')
    order   = data.get('order', [])  # [{user_id, pick_order}]
    if not pool_id or not order:
        return jsonify({'error': 'pool_id and order required'}), 400
    db2("DELETE FROM golf_draft_order WHERE pool_id = %s", (pool_id,))
    for slot in order:
        db2("INSERT INTO golf_draft_order (pool_id, user_id, pick_order) VALUES (%s,%s,%s)",
            (pool_id, slot['user_id'], slot['pick_order']))
    return jsonify({'success': True})


@bp.route('/api/golf_randomize_draft', methods=['POST'])
@api_admin_required
def api_golf_randomize_draft():
    data = request.get_json()
    pool_id  = data.get('pool_id')
    user_ids = data.get('user_ids', [])
    if not pool_id or not user_ids:
        return jsonify({'error': 'pool_id and user_ids required'}), 400
    shuffled = list(user_ids)
    random.shuffle(shuffled)
    db2("DELETE FROM golf_draft_order WHERE pool_id = %s", (pool_id,))
    for i, uid in enumerate(shuffled, 1):
        db2("INSERT INTO golf_draft_order (pool_id, user_id, pick_order) VALUES (%s,%s,%s)",
            (pool_id, uid, i))
    rows = db2("""SELECT d.pick_order, u.username
                  FROM golf_draft_order d JOIN users u ON u.userid = d.user_id
                  WHERE d.pool_id = %s ORDER BY d.pick_order""", (pool_id,))
    return jsonify({'success': True,
                    'order': [{'pick_order': r[0], 'username': r[1]} for r in rows]})


@bp.route('/api/golf_set_pool_status', methods=['POST'])
@api_admin_required
def api_golf_set_pool_status():
    data   = request.get_json()
    pool_id = data.get('pool_id')
    status  = data.get('status')
    if status not in ('setup', 'open', 'active', 'complete'):
        return jsonify({'error': 'invalid status'}), 400
    db2("UPDATE golf_pools SET status = %s WHERE pool_id = %s", (status, pool_id))
    return jsonify({'success': True})


@bp.route('/api/golf_set_paid', methods=['POST'])
@api_admin_required
def api_golf_set_paid():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    paid    = data.get('paid')
    if pool_id is None or user_id is None or paid is None:
        return jsonify({'error': 'pool_id, user_id, and paid required'}), 400
    db2("UPDATE golf_draft_order SET paid = %s WHERE pool_id = %s AND user_id = %s",
        (1 if paid else 0, pool_id, user_id))
    return jsonify({'success': True})


@bp.route('/api/golf_admin_pick', methods=['POST'])
@api_admin_required
def api_golf_admin_pick():
    data           = request.get_json()
    pool_id        = data.get('pool_id')
    user_id        = data.get('user_id')
    player_espn_id = str(data.get('player_espn_id', '')).strip()
    player_name    = data.get('player_name', '').strip()

    if not pool_id or not user_id or not player_espn_id or not player_name:
        return jsonify({'error': 'pool_id, user_id, player_espn_id, player_name required'}), 400

    pool_row = db2("SELECT status, pool_format, picks_per_user FROM golf_pools WHERE pool_id = %s", (pool_id,))
    if not pool_row:
        return jsonify({'error': 'Pool not found'}), 404
    pool_status, pool_format, picks_per_user = pool_row[0]
    if pool_status != 'open':
        return jsonify({'error': 'Pool is not open'}), 400

    existing_count = db2("SELECT COUNT(*) FROM golf_picks WHERE pool_id=%s AND user_id=%s",
                         (pool_id, user_id))[0][0]
    if existing_count >= picks_per_user:
        return jsonify({'error': f'User already has {picks_per_user} picks'}), 400

    if pool_format == 'draft':
        taken = db2("SELECT 1 FROM golf_picks WHERE pool_id=%s AND player_espn_id=%s",
                    (pool_id, player_espn_id))
        if taken:
            return jsonify({'error': 'That player is already picked in this pool'}), 400

        draft_rows = db2("SELECT user_id FROM golf_draft_order WHERE pool_id=%s ORDER BY pick_order",
                         (pool_id,))
        base_order = [r[0] for r in draft_rows]
        sequence   = _compute_snake_sequence(base_order, picks_per_user)
        picked_pos = {r[0] for r in db2("SELECT draft_position FROM golf_picks WHERE pool_id=%s", (pool_id,))}
        user_next  = next((i + 1 for i, uid in enumerate(sequence)
                           if uid == user_id and (i + 1) not in picked_pos), None)
        if user_next is None:
            return jsonify({'error': 'No remaining draft positions for this user'}), 400
        draft_position = user_next
    else:
        draft_position = existing_count + 1

    try:
        db2("""INSERT INTO golf_picks (pool_id, user_id, player_espn_id, player_name, draft_position)
               VALUES (%s,%s,%s,%s,%s)""",
            (pool_id, user_id, player_espn_id, player_name, draft_position))
    except Exception:
        return jsonify({'error': 'Could not add pick (duplicate?)'}), 400

    logging.info("Admin golf pick: pool %s user %s → %s pos %s", pool_id, user_id, player_name, draft_position)
    return jsonify({'success': True})


# ── USER ENDPOINTS ────────────────────────────────────────────────────────────

@bp.route('/api/golf_pools', methods=['GET'])
@login_required
def api_golf_pools():
    user_id  = session.get('userid')
    is_admin = session.get('is_admin') == 1
    if is_admin:
        rows = db2("""SELECT p.pool_id, p.name, p.status, p.pool_format,
                             e.name, e.event_date
                      FROM golf_pools p JOIN golf_events e ON e.event_id = p.event_id
                      ORDER BY p.pool_id DESC""")
    else:
        rows = db2("""SELECT p.pool_id, p.name, p.status, p.pool_format,
                             e.name, e.event_date
                      FROM golf_pools p
                      JOIN golf_events e ON e.event_id = p.event_id
                      JOIN golf_draft_order d ON d.pool_id = p.pool_id AND d.user_id = %s
                      ORDER BY p.pool_id DESC""", (user_id,))
    return jsonify({'pools': [
        {'pool_id': r[0], 'name': r[1], 'status': r[2], 'pool_format': r[3],
         'event_name': r[4], 'event_date': str(r[5]) if r[5] else ''}
        for r in rows]})


@bp.route('/api/golf_pool', methods=['GET'])
@login_required
def api_golf_pool():
    pool_id  = request.args.get('pool_id', type=int)
    user_id  = session.get('userid')
    is_admin = session.get('is_admin') == 1

    if not pool_id:
        return jsonify({'error': 'pool_id required'}), 400

    pool_row = db2("""SELECT p.pool_id, p.name, p.fee, p.status, p.pool_format,
                             p.picks_per_user, p.draft_type,
                             e.event_id, e.name, e.espn_event_id, e.course, e.event_date
                      FROM golf_pools p JOIN golf_events e ON e.event_id = p.event_id
                      WHERE p.pool_id = %s""", (pool_id,))
    if not pool_row:
        return jsonify({'error': 'Pool not found'}), 404

    r = pool_row[0]
    pool  = {'pool_id': r[0], 'name': r[1], 'fee': r[2], 'status': r[3],
             'pool_format': r[4], 'picks_per_user': r[5], 'draft_type': r[6]}
    event = {'event_id': r[7], 'name': r[8], 'espn_event_id': r[9],
             'course': r[10] or '', 'event_date': str(r[11]) if r[11] else ''}

    in_pool = is_admin or bool(db2(
        "SELECT 1 FROM golf_draft_order WHERE pool_id=%s AND user_id=%s", (pool_id, user_id)
    ))
    if not in_pool:
        return jsonify({'error': 'You are not in this pool'}), 403

    # Participants (base draft order)
    p_rows = db2("""SELECT d.pick_order, d.user_id, u.username, d.paid
                    FROM golf_draft_order d JOIN users u ON u.userid = d.user_id
                    WHERE d.pool_id = %s ORDER BY d.pick_order""", (pool_id,))
    participants = [{'pick_order': r[0], 'user_id': r[1], 'username': r[2], 'paid': bool(r[3])}
                    for r in p_rows]

    # All picks
    pick_rows = db2("""SELECT gp.pick_id, gp.user_id, u.username, gp.player_espn_id,
                              gp.player_name, gp.draft_position, gp.is_tiebreaker, gp.pick_type
                       FROM golf_picks gp JOIN users u ON u.userid = gp.user_id
                       WHERE gp.pool_id = %s ORDER BY gp.draft_position""", (pool_id,))
    picks = [{'pick_id': r[0], 'user_id': r[1], 'username': r[2],
              'player_espn_id': r[3], 'player_name': r[4],
              'draft_position': r[5], 'is_tiebreaker': bool(r[6]), 'pick_type': r[7]}
             for r in pick_rows]

    current_user_picks = [p for p in picks if p['user_id'] == user_id]

    # Snake sequence + on-clock (draft format only)
    snake_sequence = []
    on_clock       = None
    is_on_clock    = False
    if pool['pool_format'] == 'draft' and participants:
        base_order   = [p['user_id'] for p in participants]
        username_map = {p['user_id']: p['username'] for p in participants}
        seq_uids     = _compute_snake_sequence(base_order, pool['picks_per_user'])
        picked_pos   = {p['draft_position'] for p in picks}
        picks_by_pos = {p['draft_position']: p for p in picks}

        for pick_num, uid in enumerate(seq_uids, 1):
            round_num = (pick_num - 1) // len(base_order) + 1
            has_pick  = pick_num in picked_pos
            entry = {'pick_num': pick_num, 'round': round_num,
                     'user_id': uid, 'username': username_map.get(uid, ''),
                     'has_pick': has_pick,
                     'player_name': picks_by_pos[pick_num]['player_name'] if has_pick else ''}
            snake_sequence.append(entry)

        next_slot = next((s for s in snake_sequence if not s['has_pick']), None)
        if next_slot and pool['status'] == 'open':
            on_clock    = next_slot
            is_on_clock = next_slot['user_id'] == user_id

    # ESPN data
    espn_field         = []
    espn_scores_by_id  = {}
    standings          = []
    espn_event_id      = event['espn_event_id']

    if espn_event_id and pool['status'] in ('open', 'active', 'complete'):
        event_info, players = get_golf_event_detail(espn_event_id)
        event['espn_status'] = event_info.get('status_desc', '')
        espn_field        = players
        espn_scores_by_id = {p['espn_id']: p for p in players}

    if pool['status'] in ('active', 'complete') and participants:
        picks_by_user = {}
        for p in picks:
            picks_by_user.setdefault(p['user_id'], []).append(p)

        for participant in participants:
            uid        = participant['user_id']
            user_picks = picks_by_user.get(uid, [])
            is_eliminated = False
            total_value   = 0
            tiebreaker_value = None
            detailed_picks   = []

            for pick in user_picks:
                espn = espn_scores_by_id.get(pick['player_espn_id'], {})
                if espn.get('is_eliminated'):
                    is_eliminated = True
                tv = espn.get('total_value') or 0
                total_value += tv
                if pick['is_tiebreaker']:
                    tiebreaker_value = tv
                detailed_picks.append({
                    **pick,
                    'is_eliminated':    espn.get('is_eliminated', False),
                    'display_position': espn.get('display_position', '-'),
                    'total_display':    espn.get('total_display', 'E'),
                    'total_value':      tv,
                    'total_strokes':    espn.get('total_strokes', '-'),
                    'rounds':           espn.get('rounds', {}),
                })

            standings.append({
                'user_id':          uid,
                'username':         participant['username'],
                'paid':             participant['paid'],
                'is_eliminated':    is_eliminated,
                'total_value':      total_value,
                'tiebreaker_value': tiebreaker_value,
                'picks':            detailed_picks,
            })

        active    = [s for s in standings if not s['is_eliminated']]
        eliminated = [s for s in standings if s['is_eliminated']]
        active.sort(key=lambda s: (
            s['total_value'],
            s['tiebreaker_value'] if s['tiebreaker_value'] is not None else 0
        ))
        standings = active + eliminated

    return jsonify({
        'pool':              pool,
        'event':             event,
        'participants':      participants,
        'picks':             picks,
        'current_user_picks': current_user_picks,
        'snake_sequence':    snake_sequence,
        'on_clock':          on_clock,
        'is_on_clock':       is_on_clock,
        'espn_field':        espn_field,
        'standings':         standings,
        'is_admin':          is_admin,
    })


@bp.route('/api/golf_pick', methods=['POST'])
@login_required
def api_golf_pick():
    user_id = session.get('userid')
    data    = request.get_json()
    pool_id        = data.get('pool_id')
    player_espn_id = str(data.get('player_espn_id', '')).strip()
    player_name    = data.get('player_name', '').strip()

    if not pool_id or not player_espn_id or not player_name:
        return jsonify({'error': 'pool_id, player_espn_id, player_name required'}), 400

    pool_row = db2("SELECT status, pool_format, picks_per_user FROM golf_pools WHERE pool_id=%s", (pool_id,))
    if not pool_row or pool_row[0][0] != 'open':
        return jsonify({'error': 'Pool is not open for picks'}), 400
    _, pool_format, picks_per_user = pool_row[0]

    if not db2("SELECT 1 FROM golf_draft_order WHERE pool_id=%s AND user_id=%s", (pool_id, user_id)):
        return jsonify({'error': 'You are not in this pool'}), 403

    existing_count = db2("SELECT COUNT(*) FROM golf_picks WHERE pool_id=%s AND user_id=%s",
                         (pool_id, user_id))[0][0]
    if existing_count >= picks_per_user:
        return jsonify({'error': f'You already have all {picks_per_user} picks'}), 400

    if pool_format == 'draft':
        draft_rows = db2("SELECT user_id FROM golf_draft_order WHERE pool_id=%s ORDER BY pick_order",
                         (pool_id,))
        base_order = [r[0] for r in draft_rows]
        sequence   = _compute_snake_sequence(base_order, picks_per_user)
        picked_pos = {r[0] for r in db2("SELECT draft_position FROM golf_picks WHERE pool_id=%s", (pool_id,))}

        next_pos = next((i + 1 for i, _ in enumerate(sequence) if (i + 1) not in picked_pos), None)
        if next_pos is None or sequence[next_pos - 1] != user_id:
            return jsonify({'error': "It's not your turn"}), 400

        if db2("SELECT 1 FROM golf_picks WHERE pool_id=%s AND player_espn_id=%s", (pool_id, player_espn_id)):
            return jsonify({'error': 'That golfer is already picked in this pool'}), 400

        draft_position = next_pos
    else:
        draft_position = existing_count + 1

    try:
        db2("""INSERT INTO golf_picks (pool_id, user_id, player_espn_id, player_name, draft_position)
               VALUES (%s,%s,%s,%s,%s)""",
            (pool_id, user_id, player_espn_id, player_name, draft_position))
    except Exception:
        return jsonify({'error': 'That golfer was just taken — please pick another'}), 400

    logging.info("Golf pick: pool %s user %s → %s pos %s", pool_id, user_id, player_name, draft_position)
    return jsonify({'success': True})


@bp.route('/api/golf_set_tiebreaker', methods=['POST'])
@login_required
def api_golf_set_tiebreaker():
    user_id = session.get('userid')
    data    = request.get_json()
    pool_id = data.get('pool_id')
    pick_id = data.get('pick_id')

    if not pool_id or not pick_id:
        return jsonify({'error': 'pool_id and pick_id required'}), 400

    pick_row = db2("SELECT user_id FROM golf_picks WHERE pick_id=%s AND pool_id=%s", (pick_id, pool_id))
    if not pick_row or pick_row[0][0] != user_id:
        return jsonify({'error': 'Pick not found'}), 404

    pool_row = db2("SELECT status FROM golf_pools WHERE pool_id=%s", (pool_id,))
    if not pool_row or pool_row[0][0] == 'complete':
        return jsonify({'error': 'Cannot change tiebreaker after pool is complete'}), 400

    db2("UPDATE golf_picks SET is_tiebreaker=0 WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    db2("UPDATE golf_picks SET is_tiebreaker=1 WHERE pick_id=%s", (pick_id,))
    return jsonify({'success': True})
