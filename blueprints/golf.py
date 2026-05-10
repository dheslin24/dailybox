from flask import Blueprint, jsonify, request, session
from db_accessor.db_accessor import db2
from utils import login_required, api_admin_required, golf_admin_required
from services.espn_client import get_golf_tournaments, get_golf_event_detail, get_golf_event_venue, get_golf_tee_times
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


def _can_manage_pool(pool_id):
    """True if current user is a super admin or created this pool via a grant."""
    if session.get('is_admin') == 1:
        return True
    uid = session.get('userid')
    if not uid:
        return False
    return bool(db2("SELECT 1 FROM golf_pools WHERE pool_id=%s AND created_by=%s", (pool_id, uid)))


def _resolve_tier_from_data(tiers, manual_players, espn_id, world_rank):
    """Return (tier_id, tier_name) for a player given pre-loaded tier data, or (None, None)."""
    espn_id_str = str(espn_id)
    for t in tiers:
        if t['tier_type'] == 'ranking' and world_rank is not None:
            rmin, rmax = t['rank_min'], t['rank_max']
            if (rmin is None or world_rank >= rmin) and (rmax is None or world_rank <= rmax):
                return t['tier_id'], t['name']
        elif t['tier_type'] == 'manual':
            if espn_id_str in manual_players.get(t['tier_id'], set()):
                return t['tier_id'], t['name']
    return None, None


def _load_pool_tiers(pool_id):
    """Return (tiers_list, manual_players_dict) for a pool."""
    from services.espn_client import get_golf_world_rankings as _rankings  # noqa: local import fine
    rows = db2("""SELECT tier_id, name, tier_order, tier_type, rank_min, rank_max, min_picks, max_picks
                  FROM golf_pool_tiers WHERE pool_id=%s ORDER BY tier_order, tier_id""", (pool_id,))
    tiers = [{'tier_id': r[0], 'name': r[1], 'tier_order': r[2], 'tier_type': r[3],
               'rank_min': r[4], 'rank_max': r[5], 'min_picks': r[6], 'max_picks': r[7]}
             for r in (rows or [])]
    manual_players = {}
    for t in tiers:
        if t['tier_type'] == 'manual':
            tp = db2("SELECT player_espn_id FROM golf_pool_tier_players WHERE tier_id=%s", (t['tier_id'],))
            manual_players[t['tier_id']] = {r[0] for r in (tp or [])}
    return tiers, manual_players


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
    db2("""CREATE TABLE IF NOT EXISTS golf_pool_grants (
            grant_id      INT AUTO_INCREMENT PRIMARY KEY,
            user_id       INT NOT NULL,
            granted_by    INT NOT NULL,
            pools_allowed INT NOT NULL DEFAULT 1,
            pools_used    INT NOT NULL DEFAULT 0,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_user (user_id)
        )""")
    try:
        db2("ALTER TABLE golf_pools ADD COLUMN created_by INT DEFAULT NULL")
    except Exception:
        pass
    try:
        db2("ALTER TABLE golf_pools ADD COLUMN invite_code VARCHAR(8) DEFAULT NULL")
    except Exception:
        pass
    try:
        db2("ALTER TABLE golf_pools ADD COLUMN tiebreaker_type VARCHAR(20) NOT NULL DEFAULT 'player'")
    except Exception:
        pass
    try:
        db2("ALTER TABLE golf_draft_order ADD COLUMN tiebreaker_prediction INT DEFAULT NULL")
    except Exception:
        pass
    db2("""CREATE TABLE IF NOT EXISTS golf_pool_tiers (
            tier_id    INT AUTO_INCREMENT PRIMARY KEY,
            pool_id    INT NOT NULL,
            name       VARCHAR(100) NOT NULL,
            tier_order INT NOT NULL DEFAULT 0,
            tier_type  VARCHAR(20) NOT NULL DEFAULT 'ranking',
            rank_min   INT DEFAULT NULL,
            rank_max   INT DEFAULT NULL,
            min_picks  INT NOT NULL DEFAULT 0,
            max_picks  INT DEFAULT NULL,
            INDEX idx_pool (pool_id)
        )""")
    db2("""CREATE TABLE IF NOT EXISTS golf_pool_tier_players (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            tier_id        INT NOT NULL,
            pool_id        INT NOT NULL,
            player_espn_id VARCHAR(50) NOT NULL,
            player_name    VARCHAR(100) NOT NULL,
            UNIQUE KEY uq_tier_player (tier_id, player_espn_id),
            INDEX idx_pool (pool_id)
        )""")
    try:
        db2("ALTER TABLE golf_picks ADD COLUMN tier_id INT DEFAULT NULL")
    except Exception:
        pass
    try:
        db2("ALTER TABLE golf_pools ADD COLUMN scoring_players INT DEFAULT NULL")
    except Exception:
        pass
    # Backfill invite codes for pools that don't have one
    pools_without_code = db2("SELECT pool_id FROM golf_pools WHERE invite_code IS NULL OR invite_code = ''")
    for (pid,) in (pools_without_code or []):
        code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
        db2("UPDATE golf_pools SET invite_code=%s WHERE pool_id=%s", (code, pid))
    logging.info("golf_ tables initialised")
    return jsonify({'success': True})


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────────

@bp.route('/api/golf_espn_events', methods=['GET'])
@golf_admin_required
def api_golf_espn_events():
    events = get_golf_tournaments()
    return jsonify({'events': events})


@bp.route('/api/golf_event_venue', methods=['GET'])
@golf_admin_required
def api_golf_event_venue():
    event_id = request.args.get('event_id', '')
    if not event_id:
        return jsonify({'error': 'event_id required'}), 400
    venue = get_golf_event_venue(event_id)
    return jsonify({'venue': venue})


@bp.route('/api/golf_tee_times', methods=['GET'])
@login_required
def api_golf_tee_times():
    pool_id = request.args.get('pool_id', type=int)
    if not pool_id:
        return jsonify({'error': 'pool_id required'}), 400
    row = db2("SELECT e.espn_event_id FROM golf_pools p JOIN golf_events e ON e.event_id = p.event_id WHERE p.pool_id = %s", (pool_id,))
    if not row:
        return jsonify({'error': 'Pool not found'}), 404
    espn_event_id = row[0][0]
    tee_times = get_golf_tee_times(espn_event_id)
    return jsonify({'tee_times': tee_times})


@bp.route('/api/golf_users', methods=['GET'])
@golf_admin_required
def api_golf_users():
    rows = db2("""SELECT userid, username, first_name, last_name, email
                  FROM users WHERE active = 1 AND alias_of_userid IS NULL
                  ORDER BY username""")
    prev = db2("""SELECT DISTINCT d.user_id
                  FROM golf_draft_order d
                  JOIN golf_pools p ON p.pool_id = d.pool_id
                  WHERE p.created_by = %s""", (session.get('userid'),))
    return jsonify({
        'users': [{'userid': r[0], 'username': r[1],
                   'first_name': r[2], 'last_name': r[3], 'email': r[4] or ''} for r in rows],
        'previous_user_ids': [r[0] for r in (prev or [])],
    })


@bp.route('/api/golf_create_pool', methods=['POST'])
@golf_admin_required
def api_golf_create_pool():
    uid        = session.get('userid')
    is_super   = session.get('is_admin') == 1
    created_by = None

    if not is_super:
        grant = db2("SELECT pools_allowed, pools_used FROM golf_pool_grants WHERE user_id=%s", (uid,))
        if not grant:
            return jsonify({'error': 'forbidden'}), 403
        allowed, used = grant[0]
        if used >= allowed:
            return jsonify({'error': f'Pool quota reached ({used}/{allowed})'}), 403
        created_by = uid

    data = request.get_json()
    espn_event_id = str(data.get('espn_event_id', '')).strip()
    event_name    = data.get('event_name', '').strip()
    course        = data.get('course', '').strip() or None
    event_date    = data.get('event_date', '').strip() or None
    pool_name     = data.get('pool_name', '').strip()
    fee           = data.get('fee', '').strip()
    pool_format   = data.get('pool_format', 'draft')
    draft_type    = data.get('draft_type', 'manual')
    picks_per_user  = int(data.get('picks_per_user', 4))
    tiebreaker_type = data.get('tiebreaker_type', 'player')
    if tiebreaker_type not in ('player', 'winning_score'):
        tiebreaker_type = 'player'
    scoring_players_raw = data.get('scoring_players')
    try:
        scoring_players = int(scoring_players_raw) if scoring_players_raw not in (None, '') else None
    except (TypeError, ValueError):
        scoring_players = None
    if scoring_players is not None and scoring_players >= picks_per_user:
        scoring_players = None  # no-op: all picks count anyway

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
        event_id = db2("SELECT event_id FROM golf_events WHERE espn_event_id = %s", (espn_event_id,))[0][0]

    invite_code = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
    db2("""INSERT INTO golf_pools (event_id, name, fee, status, pool_format, picks_per_user, draft_type, created_by, invite_code, tiebreaker_type, scoring_players)
           VALUES (%s,%s,%s,'setup',%s,%s,%s,%s,%s,%s,%s)""",
        (event_id, pool_name, fee, pool_format, picks_per_user, draft_type, created_by, invite_code, tiebreaker_type, scoring_players))
    pool_id = db2("SELECT pool_id FROM golf_pools WHERE event_id=%s AND name=%s ORDER BY pool_id DESC LIMIT 1",
                  (event_id, pool_name))[0][0]

    if not is_super:
        db2("UPDATE golf_pool_grants SET pools_used = pools_used + 1 WHERE user_id=%s", (uid,))

    logging.info("Created golf pool %s (%s) for event %s by user %s", pool_id, pool_name, event_id, uid)
    return jsonify({'success': True, 'pool_id': pool_id, 'event_id': event_id})


@bp.route('/api/golf_admin_pools', methods=['GET'])
@golf_admin_required
def api_golf_admin_pools():
    base = """SELECT p.pool_id, p.name, p.fee, p.status, p.pool_format,
                     p.picks_per_user, p.draft_type,
                     e.event_id, e.name, e.espn_event_id, e.course, e.event_date, p.invite_code,
                     p.tiebreaker_type, p.scoring_players
              FROM golf_pools p JOIN golf_events e ON e.event_id = p.event_id"""
    if session.get('is_admin') == 1:
        rows = db2(base + " ORDER BY p.pool_id DESC")
    else:
        rows = db2(base + " WHERE p.created_by=%s ORDER BY p.pool_id DESC", (session.get('userid'),))
    return jsonify({'pools': [
        {'pool_id': r[0], 'name': r[1], 'fee': r[2], 'status': r[3],
         'pool_format': r[4], 'picks_per_user': r[5], 'draft_type': r[6],
         'event_id': r[7], 'event_name': r[8], 'espn_event_id': r[9],
         'course': r[10] or '', 'event_date': str(r[11]) if r[11] else '',
         'invite_code': r[12] or '', 'tiebreaker_type': r[13] or 'player',
         'scoring_players': r[14]}
        for r in rows]})


@bp.route('/api/golf_set_draft_order', methods=['POST'])
@golf_admin_required
def api_golf_set_draft_order():
    data = request.get_json()
    pool_id = data.get('pool_id')
    order   = data.get('order', [])  # [{user_id, pick_order}]
    if not pool_id or not order:
        return jsonify({'error': 'pool_id and order required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("DELETE FROM golf_draft_order WHERE pool_id = %s", (pool_id,))
    for slot in order:
        db2("INSERT INTO golf_draft_order (pool_id, user_id, pick_order) VALUES (%s,%s,%s)",
            (pool_id, slot['user_id'], slot['pick_order']))
    return jsonify({'success': True})


@bp.route('/api/golf_randomize_draft', methods=['POST'])
@golf_admin_required
def api_golf_randomize_draft():
    data = request.get_json()
    pool_id  = data.get('pool_id')
    user_ids = data.get('user_ids', [])
    if not pool_id or not user_ids:
        return jsonify({'error': 'pool_id and user_ids required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
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
@golf_admin_required
def api_golf_set_pool_status():
    data   = request.get_json()
    pool_id = data.get('pool_id')
    status  = data.get('status')
    if status not in ('setup', 'open', 'active', 'complete'):
        return jsonify({'error': 'invalid status'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("UPDATE golf_pools SET status = %s WHERE pool_id = %s", (status, pool_id))
    return jsonify({'success': True})


@bp.route('/api/golf_set_paid', methods=['POST'])
@golf_admin_required
def api_golf_set_paid():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    paid    = data.get('paid')
    if pool_id is None or user_id is None or paid is None:
        return jsonify({'error': 'pool_id, user_id, and paid required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("UPDATE golf_draft_order SET paid = %s WHERE pool_id = %s AND user_id = %s",
        (1 if paid else 0, pool_id, user_id))
    return jsonify({'success': True})


@bp.route('/api/golf_admin_pick', methods=['POST'])
@golf_admin_required
def api_golf_admin_pick():
    data           = request.get_json()
    pool_id        = data.get('pool_id')
    user_id        = data.get('user_id')
    player_espn_id = str(data.get('player_espn_id', '')).strip()
    player_name    = data.get('player_name', '').strip()

    if not pool_id or not user_id or not player_espn_id or not player_name:
        return jsonify({'error': 'pool_id, user_id, player_espn_id, player_name required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403

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
                             e.event_id, e.name, e.espn_event_id, e.course, e.event_date, p.invite_code,
                             p.tiebreaker_type, p.scoring_players
                      FROM golf_pools p JOIN golf_events e ON e.event_id = p.event_id
                      WHERE p.pool_id = %s""", (pool_id,))
    if not pool_row:
        return jsonify({'error': 'Pool not found'}), 404

    r = pool_row[0]
    pool  = {'pool_id': r[0], 'name': r[1], 'fee': r[2], 'status': r[3],
             'pool_format': r[4], 'picks_per_user': r[5], 'draft_type': r[6],
             'invite_code': r[12] or '', 'tiebreaker_type': r[13] or 'player',
             'scoring_players': r[14]}
    event = {'event_id': r[7], 'name': r[8], 'espn_event_id': r[9],
             'course': r[10] or '', 'event_date': str(r[11]) if r[11] else ''}

    in_pool = _can_manage_pool(pool_id) or bool(db2(
        "SELECT 1 FROM golf_draft_order WHERE pool_id=%s AND user_id=%s", (pool_id, user_id)
    ))
    if not in_pool:
        return jsonify({'error': 'You are not in this pool'}), 403

    # Participants (base draft order)
    p_rows = db2("""SELECT d.pick_order, d.user_id, u.username, d.paid, d.tiebreaker_prediction
                    FROM golf_draft_order d JOIN users u ON u.userid = d.user_id
                    WHERE d.pool_id = %s ORDER BY d.pick_order""", (pool_id,))
    participants = [{'pick_order': r[0], 'user_id': r[1], 'username': r[2], 'paid': bool(r[3]),
                     'tiebreaker_prediction': r[4]}
                    for r in p_rows]

    # All picks
    pick_rows = db2("""SELECT gp.pick_id, gp.user_id, u.username, gp.player_espn_id,
                              gp.player_name, gp.draft_position, gp.is_tiebreaker, gp.pick_type, gp.tier_id
                       FROM golf_picks gp JOIN users u ON u.userid = gp.user_id
                       WHERE gp.pool_id = %s ORDER BY gp.draft_position""", (pool_id,))
    picks = [{'pick_id': r[0], 'user_id': r[1], 'username': r[2],
              'player_espn_id': r[3], 'player_name': r[4],
              'draft_position': r[5], 'is_tiebreaker': bool(r[6]), 'pick_type': r[7], 'tier_id': r[8]}
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

    # Tiers (for async pools with tier config)
    pool_tiers, manual_players = _load_pool_tiers(pool_id)
    if pool_tiers and espn_field:
        for player in espn_field:
            tid, tname = _resolve_tier_from_data(pool_tiers, manual_players, player['espn_id'], player.get('world_rank'))
            player['tier_id']   = tid
            player['tier_name'] = tname
    tier_players_serialized = {str(tid): list(espn_ids) for tid, espn_ids in manual_players.items()}

    winning_score_leader = None

    if pool['status'] in ('active', 'complete') and participants:
        picks_by_user = {}
        for p in picks:
            picks_by_user.setdefault(p['user_id'], []).append(p)

        # For winning_score pools: find actual tournament leader
        if pool['tiebreaker_type'] == 'winning_score' and espn_field:
            valid_scores = [p['total_value'] for p in espn_field
                            if not p.get('is_eliminated') and p.get('total_value') is not None]
            if valid_scores:
                winning_score_leader = min(valid_scores)

        pred_by_user = {p['user_id']: p['tiebreaker_prediction'] for p in participants}
        scoring_players = pool.get('scoring_players')

        for participant in participants:
            uid        = participant['user_id']
            user_picks = picks_by_user.get(uid, [])
            tiebreaker_value = None
            detailed_picks   = []

            for pick in user_picks:
                espn = espn_scores_by_id.get(pick['player_espn_id'], {})
                tv = espn.get('total_value') or 0
                detailed_picks.append({
                    **pick,
                    'is_eliminated':    espn.get('is_eliminated', False),
                    'display_position': espn.get('display_position', '-'),
                    'total_display':    espn.get('total_display', 'E'),
                    'total_value':      tv,
                    'total_strokes':    espn.get('total_strokes', '-'),
                    'rounds':           espn.get('rounds', {}),
                    'counts':           True,
                })

            # Mark bench picks when pool uses scoring_players
            if scoring_players and len(detailed_picks) > scoring_players:
                sorted_indices = sorted(range(len(detailed_picks)),
                                        key=lambda i: detailed_picks[i]['total_value'])
                for i in sorted_indices[scoring_players:]:
                    detailed_picks[i]['counts'] = False

            counting_picks   = [p for p in detailed_picks if p.get('counts')]
            is_eliminated    = any(p['is_eliminated'] for p in counting_picks)
            total_value      = sum(p['total_value'] for p in counting_picks)

            for pick in detailed_picks:
                if pool['tiebreaker_type'] == 'player' and pick['is_tiebreaker']:
                    tiebreaker_value = pick['total_value']

            if pool['tiebreaker_type'] == 'winning_score':
                pred = pred_by_user.get(uid)
                if pred is not None and winning_score_leader is not None:
                    tiebreaker_value = abs(pred - winning_score_leader)

            standings.append({
                'user_id':               uid,
                'username':              participant['username'],
                'paid':                  participant['paid'],
                'is_eliminated':         is_eliminated,
                'total_value':           total_value,
                'tiebreaker_value':      tiebreaker_value,
                'tiebreaker_prediction': pred_by_user.get(uid),
                'picks':                 detailed_picks,
            })

        active    = [s for s in standings if not s['is_eliminated']]
        eliminated = [s for s in standings if s['is_eliminated']]
        active.sort(key=lambda s: (
            s['total_value'],
            0 if s['tiebreaker_value'] is not None else 1,
            s['tiebreaker_value'] if s['tiebreaker_value'] is not None else 0,
        ))
        standings = active + eliminated

    return jsonify({
        'pool':                pool,
        'event':               event,
        'participants':        participants,
        'picks':               picks,
        'current_user_picks':  current_user_picks,
        'current_user_id':     user_id,
        'snake_sequence':      snake_sequence,
        'on_clock':            on_clock,
        'is_on_clock':         is_on_clock,
        'espn_field':          espn_field,
        'standings':           standings,
        'is_admin':            is_admin,
        'winning_score_leader': winning_score_leader,
        'tiers':               pool_tiers,
        'tier_players':        {str(tid): list(ids) for tid, ids in manual_players.items()},
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

    # Tier validation for async pools with tier config
    pick_tier_id = None
    if pool_format == 'async':
        pool_tiers, manual_players = _load_pool_tiers(pool_id)
        if pool_tiers:
            from services.espn_client import get_golf_world_rankings
            world_rank = get_golf_world_rankings().get(str(player_espn_id))
            pick_tier_id, tier_name = _resolve_tier_from_data(pool_tiers, manual_players, player_espn_id, world_rank)
            if pick_tier_id is not None:
                tier_def = next(t for t in pool_tiers if t['tier_id'] == pick_tier_id)
                if tier_def['max_picks'] is not None:
                    count_in_tier = db2(
                        "SELECT COUNT(*) FROM golf_picks WHERE pool_id=%s AND user_id=%s AND tier_id=%s",
                        (pool_id, user_id, pick_tier_id)
                    )[0][0]
                    if count_in_tier >= tier_def['max_picks']:
                        return jsonify({'error': f'Max picks from "{tier_name}" reached ({tier_def["max_picks"]})'}), 400

    try:
        db2("""INSERT INTO golf_picks (pool_id, user_id, player_espn_id, player_name, draft_position, tier_id)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (pool_id, user_id, player_espn_id, player_name, draft_position, pick_tier_id))
    except Exception:
        return jsonify({'error': 'That golfer was just taken — please pick another'}), 400

    logging.info("Golf pick: pool %s user %s → %s pos %s", pool_id, user_id, player_name, draft_position)
    return jsonify({'success': True})


@bp.route('/api/golf_remove_pick', methods=['POST'])
@login_required
def api_golf_remove_pick():
    user_id = session.get('userid')
    data    = request.get_json()
    pool_id = data.get('pool_id')
    pick_id = data.get('pick_id')

    if not pool_id or not pick_id:
        return jsonify({'error': 'pool_id and pick_id required'}), 400

    pool_row = db2("SELECT status FROM golf_pools WHERE pool_id=%s", (pool_id,))
    if not pool_row or pool_row[0][0] != 'open':
        return jsonify({'error': 'Pool is not open'}), 400

    pick_row = db2("SELECT pick_id FROM golf_picks WHERE pick_id=%s AND pool_id=%s AND user_id=%s",
                   (pick_id, pool_id, user_id))
    if not pick_row:
        return jsonify({'error': 'Pick not found'}), 404

    db2("DELETE FROM golf_picks WHERE pick_id=%s", (pick_id,))

    # Re-sequence remaining picks for this user so draft_positions are gapless
    remaining = db2("SELECT pick_id FROM golf_picks WHERE pool_id=%s AND user_id=%s ORDER BY draft_position",
                    (pool_id, user_id))
    for new_pos, (pid,) in enumerate(remaining, 1):
        db2("UPDATE golf_picks SET draft_position=%s WHERE pick_id=%s", (new_pos, pid))

    logging.info("Golf remove pick: pool %s user %s pick %s", pool_id, user_id, pick_id)
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


@bp.route('/api/golf_admin_set_tiebreaker', methods=['POST'])
@golf_admin_required
def api_golf_admin_set_tiebreaker():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    pick_id = data.get('pick_id')

    if not pool_id or not user_id or not pick_id:
        return jsonify({'error': 'pool_id, user_id and pick_id required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403

    pick_row = db2("SELECT pick_id FROM golf_picks WHERE pick_id=%s AND pool_id=%s AND user_id=%s",
                   (pick_id, pool_id, user_id))
    if not pick_row:
        return jsonify({'error': 'Pick not found'}), 404

    pool_row = db2("SELECT status FROM golf_pools WHERE pool_id=%s", (pool_id,))
    if not pool_row or pool_row[0][0] == 'complete':
        return jsonify({'error': 'Cannot change tiebreaker after pool is complete'}), 400

    db2("UPDATE golf_picks SET is_tiebreaker=0 WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    db2("UPDATE golf_picks SET is_tiebreaker=1 WHERE pick_id=%s", (pick_id,))
    return jsonify({'success': True})


# ── POOL ADMIN GRANT MANAGEMENT ───────────────────────────────────────────────

@bp.route('/api/golf_pool_grants', methods=['GET'])
@api_admin_required
def api_golf_pool_grants():
    rows = db2("""SELECT g.grant_id, g.user_id, u.username, g.pools_allowed, g.pools_used,
                         gb.username, g.created_at
                  FROM golf_pool_grants g
                  JOIN users u  ON u.userid  = g.user_id
                  JOIN users gb ON gb.userid = g.granted_by
                  ORDER BY g.created_at DESC""")
    return jsonify({'grants': [
        {'grant_id': r[0], 'user_id': r[1], 'username': r[2],
         'pools_allowed': r[3], 'pools_used': r[4],
         'granted_by': r[5], 'created_at': str(r[6])}
        for r in rows]})


@bp.route('/api/golf_grant_pool_admin', methods=['POST'])
@api_admin_required
def api_golf_grant_pool_admin():
    data          = request.get_json()
    user_id       = data.get('user_id')
    pools_allowed = int(data.get('pools_allowed', 1))
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    existing = db2("SELECT grant_id FROM golf_pool_grants WHERE user_id=%s", (user_id,))
    if existing:
        db2("UPDATE golf_pool_grants SET pools_allowed=%s, granted_by=%s WHERE user_id=%s",
            (pools_allowed, session.get('userid'), user_id))
    else:
        db2("INSERT INTO golf_pool_grants (user_id, granted_by, pools_allowed, pools_used) VALUES (%s,%s,%s,0)",
            (user_id, session.get('userid'), pools_allowed))
    logging.info("Golf pool grant: user %s granted %s pools by %s", user_id, pools_allowed, session.get('userid'))
    return jsonify({'success': True})


# ── INVITE CODE JOIN ──────────────────────────────────────────────────────────

@bp.route('/api/golf_join_pool', methods=['POST'])
@login_required
def api_golf_join_pool():
    data        = request.get_json()
    invite_code = (data.get('invite_code') or '').strip().upper()
    user_id     = session.get('userid')

    if not invite_code:
        return jsonify({'error': 'invite_code required'}), 400

    pool_row = db2("SELECT pool_id, name, status FROM golf_pools WHERE invite_code = %s", (invite_code,))
    if not pool_row:
        return jsonify({'error': 'Invalid invite code'}), 404

    pool_id, pool_name, status = pool_row[0]
    if status == 'complete':
        return jsonify({'error': 'This pool is already complete'}), 400

    already = db2("SELECT 1 FROM golf_draft_order WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    if already:
        return jsonify({'error': 'You are already in this pool', 'pool_id': pool_id}), 400

    max_order = db2("SELECT COALESCE(MAX(pick_order), 0) FROM golf_draft_order WHERE pool_id=%s", (pool_id,))
    next_order = max_order[0][0] + 1
    db2("INSERT INTO golf_draft_order (pool_id, user_id, pick_order) VALUES (%s,%s,%s)",
        (pool_id, user_id, next_order))
    logging.info("User %s joined pool %s via invite code", user_id, pool_id)
    return jsonify({'success': True, 'pool_id': pool_id, 'pool_name': pool_name})


# ── WINNING SCORE TIEBREAKER ──────────────────────────────────────────────────

@bp.route('/api/golf_set_winning_score_tb', methods=['POST'])
@login_required
def api_golf_set_winning_score_tb():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    score   = data.get('score')
    user_id = session.get('userid')

    if pool_id is None or score is None:
        return jsonify({'error': 'pool_id and score required'}), 400
    try:
        score = int(score)
    except (TypeError, ValueError):
        return jsonify({'error': 'score must be an integer'}), 400

    pool_row = db2("SELECT status, tiebreaker_type FROM golf_pools WHERE pool_id=%s", (pool_id,))
    if not pool_row:
        return jsonify({'error': 'Pool not found'}), 404
    if pool_row[0][1] != 'winning_score':
        return jsonify({'error': 'Pool does not use winning score tiebreaker'}), 400
    if pool_row[0][0] != 'open':
        return jsonify({'error': 'Tiebreaker can only be set while pool is open'}), 400

    if not db2("SELECT 1 FROM golf_draft_order WHERE pool_id=%s AND user_id=%s", (pool_id, user_id)):
        return jsonify({'error': 'You are not in this pool'}), 403

    db2("UPDATE golf_draft_order SET tiebreaker_prediction=%s WHERE pool_id=%s AND user_id=%s",
        (score, pool_id, user_id))
    return jsonify({'success': True})


@bp.route('/api/golf_admin_set_winning_score_tb', methods=['POST'])
@golf_admin_required
def api_golf_admin_set_winning_score_tb():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    score   = data.get('score')

    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    if pool_id is None or user_id is None or score is None:
        return jsonify({'error': 'pool_id, user_id, and score required'}), 400
    try:
        score = int(score)
    except (TypeError, ValueError):
        return jsonify({'error': 'score must be an integer'}), 400

    db2("UPDATE golf_draft_order SET tiebreaker_prediction=%s WHERE pool_id=%s AND user_id=%s",
        (score, pool_id, user_id))
    return jsonify({'success': True})


# ── TIER MANAGEMENT ───────────────────────────────────────────────────────────

@bp.route('/api/golf_create_tier', methods=['POST'])
@golf_admin_required
def api_golf_create_tier():
    data    = request.get_json()
    pool_id = data.get('pool_id')
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    name       = (data.get('name') or '').strip()
    tier_type  = data.get('tier_type', 'ranking')
    rank_min   = data.get('rank_min')
    rank_max   = data.get('rank_max')
    min_picks  = int(data.get('min_picks') or 0)
    max_picks  = data.get('max_picks')
    if not name:
        return jsonify({'error': 'name required'}), 400
    if tier_type not in ('ranking', 'manual'):
        return jsonify({'error': 'tier_type must be ranking or manual'}), 400
    next_order_row = db2("SELECT COALESCE(MAX(tier_order), -1) + 1 FROM golf_pool_tiers WHERE pool_id=%s", (pool_id,))
    next_order = next_order_row[0][0] if next_order_row else 0
    db2("INSERT INTO golf_pool_tiers (pool_id, name, tier_order, tier_type, rank_min, rank_max, min_picks, max_picks) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (pool_id, name, next_order, tier_type,
         int(rank_min) if rank_min not in (None, '') else None,
         int(rank_max) if rank_max not in (None, '') else None,
         min_picks,
         int(max_picks) if max_picks not in (None, '') else None))
    tier_id = db2("SELECT LAST_INSERT_ID()")[0][0]
    return jsonify({'success': True, 'tier_id': tier_id})


@bp.route('/api/golf_update_tier', methods=['POST'])
@golf_admin_required
def api_golf_update_tier():
    data    = request.get_json()
    tier_id = data.get('tier_id')
    pool_id = data.get('pool_id')
    if not tier_id or not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    name      = (data.get('name') or '').strip()
    tier_type = data.get('tier_type', 'ranking')
    rank_min  = data.get('rank_min')
    rank_max  = data.get('rank_max')
    min_picks = int(data.get('min_picks') or 0)
    max_picks = data.get('max_picks')
    db2("UPDATE golf_pool_tiers SET name=%s, tier_type=%s, rank_min=%s, rank_max=%s, min_picks=%s, max_picks=%s WHERE tier_id=%s AND pool_id=%s",
        (name, tier_type,
         int(rank_min) if rank_min not in (None, '') else None,
         int(rank_max) if rank_max not in (None, '') else None,
         min_picks,
         int(max_picks) if max_picks not in (None, '') else None,
         tier_id, pool_id))
    return jsonify({'success': True})


@bp.route('/api/golf_delete_tier', methods=['POST'])
@golf_admin_required
def api_golf_delete_tier():
    data    = request.get_json()
    tier_id = data.get('tier_id')
    pool_id = data.get('pool_id')
    if not tier_id or not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("DELETE FROM golf_pool_tier_players WHERE tier_id=%s", (tier_id,))
    db2("DELETE FROM golf_pool_tiers WHERE tier_id=%s AND pool_id=%s", (tier_id, pool_id))
    return jsonify({'success': True})


@bp.route('/api/golf_save_tier_players', methods=['POST'])
@golf_admin_required
def api_golf_save_tier_players():
    data    = request.get_json()
    tier_id = data.get('tier_id')
    pool_id = data.get('pool_id')
    players = data.get('players', [])  # [{espn_id, name}]
    if not tier_id or not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("DELETE FROM golf_pool_tier_players WHERE tier_id=%s", (tier_id,))
    for p in players:
        espn_id = str(p.get('espn_id', '')).strip()
        name    = (p.get('name') or '').strip()
        if espn_id and name:
            try:
                db2("INSERT INTO golf_pool_tier_players (tier_id, pool_id, player_espn_id, player_name) VALUES (%s,%s,%s,%s)",
                    (tier_id, pool_id, espn_id, name))
            except Exception:
                pass
    return jsonify({'success': True})
