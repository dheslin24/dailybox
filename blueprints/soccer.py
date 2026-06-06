import logging
import random
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from db_accessor.db_accessor import db2
from services.espn_client import assign_wc_group_letters, get_world_cup_matches, invalidate_wc_cache
from utils import api_admin_required, login_required, soccer_admin_required

bp = Blueprint('soccer', __name__)


# ── SCHEMA ────────────────────────────────────────────────────────────────────

def _init_schema():
    db2("""CREATE TABLE IF NOT EXISTS soccer_tournaments (
        tournament_id INT AUTO_INCREMENT PRIMARY KEY,
        name          VARCHAR(100) NOT NULL,
        espn_league   VARCHAR(50)  DEFAULT 'fifa.world',
        status        VARCHAR(20)  DEFAULT 'upcoming'
    )""")
    db2("""CREATE TABLE IF NOT EXISTS soccer_matches (
        match_id           INT AUTO_INCREMENT PRIMARY KEY,
        tournament_id      INT          NOT NULL,
        espn_event_id      VARCHAR(50)  NOT NULL,
        home_espn_team_id  VARCHAR(50),
        home_name          VARCHAR(100),
        home_abbr          VARCHAR(10),
        home_logo          VARCHAR(255),
        away_espn_team_id  VARCHAR(50),
        away_name          VARCHAR(100),
        away_abbr          VARCHAR(10),
        away_logo          VARCHAR(255),
        match_date         DATETIME,
        round_type         VARCHAR(20)  NOT NULL DEFAULT 'group',
        group_letter       CHAR(1),
        match_order        INT          DEFAULT 0,
        status             VARCHAR(20)  DEFAULT 'scheduled',
        home_score         INT,
        away_score         INT,
        result             CHAR(1),
        venue              VARCHAR(200),
        UNIQUE KEY uq_espn_event (espn_event_id)
    )""")
    db2("""CREATE TABLE IF NOT EXISTS soccer_pools (
        pool_id       INT AUTO_INCREMENT PRIMARY KEY,
        tournament_id INT          NOT NULL,
        name          VARCHAR(100) NOT NULL,
        created_by    INT,
        invite_code   VARCHAR(8),
        status        VARCHAR(20)  DEFAULT 'open',
        fee           VARCHAR(50)  DEFAULT '',
        pts_group       INT          DEFAULT 1,
        pts_r32         INT          DEFAULT 2,
        pts_r16         INT          DEFAULT 3,
        pts_qf          INT          DEFAULT 4,
        pts_sf          INT          DEFAULT 5,
        pts_3rd         INT          DEFAULT 3,
        pts_final       INT          DEFAULT 6,
        pick_format     VARCHAR(20)  DEFAULT 'standard',
        pts_group_draw  INT          DEFAULT 0,
        created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_invite (invite_code)
    )""")
    # Migration for pools table already created without new columns
    for col, defn in [('pick_format', "VARCHAR(20) DEFAULT 'standard'"),
                      ('pts_group_draw', 'INT DEFAULT 0')]:
        try:
            db2(f"ALTER TABLE soccer_pools ADD COLUMN {col} {defn}")
        except Exception:
            pass  # already exists
    try:
        db2("ALTER TABLE soccer_matches ADD COLUMN venue VARCHAR(200)")
    except Exception:
        pass  # already exists
    db2("""CREATE TABLE IF NOT EXISTS soccer_pool_entries (
        entry_id  INT AUTO_INCREMENT PRIMARY KEY,
        pool_id   INT     NOT NULL,
        user_id   INT     NOT NULL,
        paid      TINYINT DEFAULT 0,
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pool_user (pool_id, user_id)
    )""")
    db2("""CREATE TABLE IF NOT EXISTS soccer_picks (
        pick_id      INT AUTO_INCREMENT PRIMARY KEY,
        pool_id      INT    NOT NULL,
        user_id      INT    NOT NULL,
        match_id     INT    NOT NULL,
        pick         CHAR(1) NOT NULL,
        submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pool_user_match (pool_id, user_id, match_id)
    )""")
    db2("""CREATE TABLE IF NOT EXISTS soccer_pool_grants (
        user_id       INT NOT NULL,
        granted_by    INT,
        pools_allowed INT     DEFAULT 1,
        pools_used    INT     DEFAULT 0,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id)
    )""")
    db2("""CREATE TABLE IF NOT EXISTS soccer_pool_deputies (
        pool_id    INT NOT NULL,
        user_id    INT NOT NULL,
        granted_by INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pool_user (pool_id, user_id)
    )""")
    existing = db2("SELECT tournament_id FROM soccer_tournaments WHERE espn_league='fifa.world'")
    if not existing:
        db2("INSERT INTO soccer_tournaments (name, espn_league, status) VALUES (%s,%s,%s)",
            ('2026 FIFA World Cup', 'fifa.world', 'upcoming'))


try:
    _init_schema()
except Exception as _e:
    logging.warning("soccer schema init error: %s", _e)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _can_manage_pool(pool_id):
    if session.get('is_admin') == 1:
        return True
    uid = session.get('userid')
    if not uid:
        return False
    if db2("SELECT 1 FROM soccer_pools WHERE pool_id=%s AND created_by=%s", (pool_id, uid)):
        return True
    return bool(db2("SELECT 1 FROM soccer_pool_deputies WHERE pool_id=%s AND user_id=%s", (pool_id, uid)))


def _get_tournament_id():
    row = db2("SELECT tournament_id FROM soccer_tournaments WHERE espn_league='fifa.world' LIMIT 1")
    return row[0][0] if row else None


def _gen_invite_code():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    for _ in range(20):
        code = ''.join(random.choices(chars, k=6))
        if not db2("SELECT 1 FROM soccer_pools WHERE invite_code=%s", (code,)):
            return code
    return None


_ROUND_PT_COL = {
    'group': 'pts_group', 'r32': 'pts_r32', 'r16': 'pts_r16',
    'qf': 'pts_qf', 'sf': 'pts_sf', '3rd': 'pts_3rd', 'final': 'pts_final',
}

ROUND_DISPLAY = {
    'group': 'Group Stage', 'r32': 'Round of 32', 'r16': 'Round of 16',
    'qf': 'Quarterfinals', 'sf': 'Semifinals', '3rd': 'Third Place', 'final': 'Final',
}


def _compute_standings(pool_id):
    pool_row = db2("""SELECT pts_group, pts_r32, pts_r16, pts_qf, pts_sf, pts_3rd, pts_final,
                             pick_format, pts_group_draw
                      FROM soccer_pools WHERE pool_id=%s""", (pool_id,))
    if not pool_row:
        return []
    pts_map = dict(zip(['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final'], pool_row[0][:7]))
    pick_format = pool_row[0][7] or 'standard'
    pts_group_draw = pool_row[0][8] or 0

    entries = db2("""SELECT e.user_id, u.username
                     FROM soccer_pool_entries e
                     JOIN users u ON u.userid = e.user_id
                     WHERE e.pool_id=%s""", (pool_id,))
    if not entries:
        return []

    picks = db2("""SELECT p.user_id, p.pick, m.result, m.round_type
                   FROM soccer_picks p
                   JOIN soccer_matches m ON m.match_id = p.match_id
                   WHERE p.pool_id=%s AND m.result IS NOT NULL""", (pool_id,))

    user_data = {r[0]: {'username': r[1], 'total': 0, 'by_round': {}, 'correct': 0, 'picked': 0}
                 for r in entries}

    for row in (picks or []):
        user_id, pick, result, round_type = row
        if user_id not in user_data:
            continue
        user_data[user_id]['picked'] += 1
        pts = 0
        if pick_format == 'winner_only' and round_type == 'group':
            # winner_only: no Draw picks allowed; draws award consolation pts to both sides
            if result == 'D':
                pts = pts_group_draw  # consolation for a drawn game
                user_data[user_id]['correct'] += 1  # count as "got something"
            elif pick == result:
                pts = pts_map.get(round_type, 0)
                user_data[user_id]['correct'] += 1
        else:
            if pick == result:
                pts = pts_map.get(round_type, 0)
                user_data[user_id]['correct'] += 1
        if pts:
            user_data[user_id]['total'] += pts
            user_data[user_id]['by_round'][round_type] = user_data[user_id]['by_round'].get(round_type, 0) + pts

    standings = [{'user_id': uid, 'username': d['username'], 'total_points': d['total'],
                  'by_round': d['by_round'], 'correct_picks': d['correct'], 'total_picks': d['picked']}
                 for uid, d in user_data.items()]
    standings.sort(key=lambda x: -x['total_points'])
    for i, s in enumerate(standings):
        s['rank'] = standings[i - 1]['rank'] if i > 0 and s['total_points'] == standings[i - 1]['total_points'] else i + 1
    return standings


# ── ADMIN: GRANTS ─────────────────────────────────────────────────────────────

@bp.route('/api/soccer_grant_pool_admin', methods=['POST'])
@api_admin_required
def soccer_grant_pool_admin():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    pools_allowed = int(data.get('pools_allowed', 1))
    if not username:
        return jsonify({'error': 'username required'}), 400
    user = db2("SELECT userid FROM users WHERE username=%s", (username,))
    if not user:
        return jsonify({'error': 'user not found'}), 404
    uid = user[0][0]
    db2("""INSERT INTO soccer_pool_grants (user_id, granted_by, pools_allowed, pools_used)
           VALUES (%s,%s,%s,0)
           ON DUPLICATE KEY UPDATE pools_allowed=%s, granted_by=%s""",
        (uid, session['userid'], pools_allowed, pools_allowed, session['userid']))
    return jsonify({'success': True})


@bp.route('/api/soccer_pool_grants', methods=['GET'])
@api_admin_required
def soccer_pool_grants():
    rows = db2("""SELECT g.user_id, u.username, g.pools_allowed, g.pools_used, g.created_at
                  FROM soccer_pool_grants g JOIN users u ON u.userid = g.user_id
                  ORDER BY g.created_at DESC""")
    return jsonify([{'user_id': r[0], 'username': r[1], 'pools_allowed': r[2],
                     'pools_used': r[3], 'created_at': str(r[4])} for r in (rows or [])])


# ── ADMIN: USER LIST ──────────────────────────────────────────────────────────

@bp.route('/api/soccer_users', methods=['GET'])
@soccer_admin_required
def soccer_users():
    rows = db2("""SELECT userid, username FROM users
                  WHERE active = 1 AND alias_of_userid IS NULL
                  ORDER BY username""")
    return jsonify([{'userid': r[0], 'username': r[1]} for r in (rows or [])])


# ── ADMIN: POOL MANAGEMENT ────────────────────────────────────────────────────

@bp.route('/api/soccer_create_pool', methods=['POST'])
@soccer_admin_required
def soccer_create_pool():
    uid = session['userid']
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400

    if session.get('is_admin') != 1:
        grant = db2("SELECT pools_allowed, pools_used FROM soccer_pool_grants WHERE user_id=%s", (uid,))
        if not grant or grant[0][1] >= grant[0][0]:
            return jsonify({'error': 'pool quota exceeded'}), 403

    t_id = _get_tournament_id()
    if not t_id:
        return jsonify({'error': 'tournament not found'}), 500

    invite_code = _gen_invite_code()
    if not invite_code:
        return jsonify({'error': 'could not generate invite code'}), 500

    pts = {k: int(data.get(k, v)) for k, v in [
        ('pts_group', 1), ('pts_r32', 2), ('pts_r16', 3),
        ('pts_qf', 4), ('pts_sf', 5), ('pts_3rd', 3), ('pts_final', 6)
    ]}
    pick_format = data.get('pick_format', 'standard')
    if pick_format not in ('standard', 'winner_only'):
        pick_format = 'standard'
    pts_group_draw = int(data.get('pts_group_draw', 0))

    db2("""INSERT INTO soccer_pools
           (tournament_id, name, created_by, invite_code, status, fee,
            pts_group, pts_r32, pts_r16, pts_qf, pts_sf, pts_3rd, pts_final,
            pick_format, pts_group_draw)
           VALUES (%s,%s,%s,%s,'open',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (t_id, name, uid, invite_code, data.get('fee', ''),
         pts['pts_group'], pts['pts_r32'], pts['pts_r16'],
         pts['pts_qf'], pts['pts_sf'], pts['pts_3rd'], pts['pts_final'],
         pick_format, pts_group_draw))

    pool_id = db2("SELECT LAST_INSERT_ID()")[0][0]
    db2("INSERT IGNORE INTO soccer_pool_entries (pool_id, user_id) VALUES (%s,%s)", (pool_id, uid))

    if session.get('is_admin') != 1:
        db2("UPDATE soccer_pool_grants SET pools_used = pools_used + 1 WHERE user_id=%s", (uid,))

    return jsonify({'success': True, 'pool_id': pool_id, 'invite_code': invite_code})


@bp.route('/api/soccer_admin_pools', methods=['GET'])
@soccer_admin_required
def soccer_admin_pools():
    uid = session['userid']
    if session.get('is_admin') == 1:
        rows = db2("""SELECT pool_id, name, status, invite_code, fee, created_at,
                             pts_group, pts_r32, pts_r16, pts_qf, pts_sf, pts_3rd, pts_final,
                             pick_format, pts_group_draw
                      FROM soccer_pools ORDER BY created_at DESC""")
    else:
        rows = db2("""SELECT DISTINCT p.pool_id, p.name, p.status, p.invite_code, p.fee, p.created_at,
                             p.pts_group, p.pts_r32, p.pts_r16, p.pts_qf, p.pts_sf, p.pts_3rd, p.pts_final,
                             p.pick_format, p.pts_group_draw
                      FROM soccer_pools p
                      LEFT JOIN soccer_pool_deputies d ON d.pool_id=p.pool_id AND d.user_id=%s
                      WHERE p.created_by=%s OR d.user_id IS NOT NULL
                      ORDER BY p.created_at DESC""", (uid, uid))
    return jsonify([{
        'pool_id': r[0], 'name': r[1], 'status': r[2], 'invite_code': r[3],
        'fee': r[4], 'created_at': str(r[5]),
        'pts_group': r[6], 'pts_r32': r[7], 'pts_r16': r[8],
        'pts_qf': r[9], 'pts_sf': r[10], 'pts_3rd': r[11], 'pts_final': r[12],
        'pick_format': r[13] or 'standard', 'pts_group_draw': r[14] or 0,
    } for r in (rows or [])])


@bp.route('/api/soccer_add_user', methods=['POST'])
@login_required
def soccer_add_user():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    username = (data.get('username') or '').strip()
    if not pool_id or not username:
        return jsonify({'error': 'pool_id and username required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    user = db2("SELECT userid FROM users WHERE username=%s", (username,))
    if not user:
        return jsonify({'error': 'user not found'}), 404
    db2("INSERT IGNORE INTO soccer_pool_entries (pool_id, user_id) VALUES (%s,%s)", (pool_id, user[0][0]))
    return jsonify({'success': True})


@bp.route('/api/soccer_remove_user', methods=['POST'])
@login_required
def soccer_remove_user():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    if not pool_id or not user_id:
        return jsonify({'error': 'pool_id and user_id required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("DELETE FROM soccer_pool_entries WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    db2("DELETE FROM soccer_picks WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    return jsonify({'success': True})


@bp.route('/api/soccer_set_paid', methods=['POST'])
@login_required
def soccer_set_paid():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    if not pool_id or not user_id:
        return jsonify({'error': 'pool_id and user_id required'}), 400
    if not _can_manage_pool(pool_id):
        return jsonify({'error': 'forbidden'}), 403
    db2("UPDATE soccer_pool_entries SET paid=%s WHERE pool_id=%s AND user_id=%s",
        (1 if data.get('paid') else 0, pool_id, user_id))
    return jsonify({'success': True})


@bp.route('/api/soccer_add_deputy', methods=['POST'])
@login_required
def soccer_add_deputy():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    username = (data.get('username') or '').strip()
    if not pool_id or not username:
        return jsonify({'error': 'pool_id and username required'}), 400
    uid = session['userid']
    if session.get('is_admin') != 1:
        if not db2("SELECT 1 FROM soccer_pools WHERE pool_id=%s AND created_by=%s", (pool_id, uid)):
            return jsonify({'error': 'forbidden'}), 403
    user = db2("SELECT userid FROM users WHERE username=%s", (username,))
    if not user:
        return jsonify({'error': 'user not found'}), 404
    db2("INSERT IGNORE INTO soccer_pool_deputies (pool_id, user_id, granted_by) VALUES (%s,%s,%s)",
        (pool_id, user[0][0], uid))
    return jsonify({'success': True})


@bp.route('/api/soccer_remove_deputy', methods=['POST'])
@login_required
def soccer_remove_deputy():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    user_id = data.get('user_id')
    if not pool_id or not user_id:
        return jsonify({'error': 'pool_id and user_id required'}), 400
    uid = session['userid']
    if session.get('is_admin') != 1:
        if not db2("SELECT 1 FROM soccer_pools WHERE pool_id=%s AND created_by=%s", (pool_id, uid)):
            return jsonify({'error': 'forbidden'}), 403
    db2("DELETE FROM soccer_pool_deputies WHERE pool_id=%s AND user_id=%s", (pool_id, user_id))
    return jsonify({'success': True})


# ── MATCH SEEDING & REFRESH ───────────────────────────────────────────────────

@bp.route('/api/soccer_seed_matches', methods=['POST'])
@api_admin_required
def soccer_seed_matches():
    try:
        t_id = _get_tournament_id()
        if not t_id:
            return jsonify({'error': 'tournament not found — schema may not have initialized'}), 500

        invalidate_wc_cache()
        matches = get_world_cup_matches()
        if not matches:
            return jsonify({'error': 'no matches returned from ESPN — check server log'}), 500

        # Derive group letters by finding connected components in group-stage matches
        group_map = assign_wc_group_letters(matches)  # {espn_team_id: 'A'..'L'}

        inserted = updated = 0
        for i, m in enumerate(matches):
            ht, at = m['home_team'], m['away_team']
            group_letter = m['group_letter'] or group_map.get(ht['espn_team_id']) or group_map.get(at['espn_team_id'])

            fields = (
                ht['espn_team_id'], ht['name'], ht['abbreviation'], ht['logo_url'],
                at['espn_team_id'], at['name'], at['abbreviation'], at['logo_url'],
                m['match_date'], m['round_type'], group_letter, i,
                m['status'], m['home_score'], m['away_score'], m['result'], m.get('venue', ''),
            )
            existing = db2("SELECT match_id FROM soccer_matches WHERE espn_event_id=%s", (m['espn_event_id'],))
            if existing:
                db2("""UPDATE soccer_matches SET
                       home_espn_team_id=%s, home_name=%s, home_abbr=%s, home_logo=%s,
                       away_espn_team_id=%s, away_name=%s, away_abbr=%s, away_logo=%s,
                       match_date=%s, round_type=%s, group_letter=%s, match_order=%s,
                       status=%s, home_score=%s, away_score=%s, result=%s, venue=%s
                       WHERE espn_event_id=%s""",
                    (*fields, m['espn_event_id']))
                updated += 1
            else:
                db2("""INSERT INTO soccer_matches
                       (tournament_id, espn_event_id,
                        home_espn_team_id, home_name, home_abbr, home_logo,
                        away_espn_team_id, away_name, away_abbr, away_logo,
                        match_date, round_type, group_letter, match_order,
                        status, home_score, away_score, result, venue)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (t_id, m['espn_event_id'], *fields))
                inserted += 1

        return jsonify({'success': True, 'inserted': inserted, 'updated': updated,
                        'total': len(matches), 'groups_mapped': len(group_map),
                        'no_group': sum(1 for m in matches if m['round_type'] == 'group' and not (group_map.get(m['home_team']['espn_team_id']) or group_map.get(m['away_team']['espn_team_id'])))})
    except Exception as e:
        logging.exception("soccer_seed_matches error")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/soccer_refresh_matches', methods=['POST'])
@login_required
def soccer_refresh_matches():
    try:
        data = request.get_json() or {}
        pool_id = data.get('pool_id')
        if pool_id and not _can_manage_pool(pool_id):
            return jsonify({'error': 'forbidden'}), 403

        invalidate_wc_cache()
        matches = get_world_cup_matches()
        updated = 0
        for m in matches:
            if db2("SELECT 1 FROM soccer_matches WHERE espn_event_id=%s", (m['espn_event_id'],)):
                ht, at = m['home_team'], m['away_team']
                db2("""UPDATE soccer_matches SET
                       status=%s, home_score=%s, away_score=%s, result=%s,
                       home_name=%s, home_abbr=%s, home_logo=%s,
                       away_name=%s, away_abbr=%s, away_logo=%s,
                       venue=%s
                       WHERE espn_event_id=%s""",
                    (m['status'], m['home_score'], m['away_score'], m['result'],
                     ht['name'], ht['abbreviation'], ht['logo_url'],
                     at['name'], at['abbreviation'], at['logo_url'],
                     m.get('venue', ''), m['espn_event_id']))
                updated += 1

        return jsonify({'success': True, 'updated': updated})
    except Exception as e:
        logging.exception("soccer_refresh_matches error")
        return jsonify({'error': str(e)}), 500


# ── USER: JOIN / LIST ─────────────────────────────────────────────────────────

@bp.route('/api/soccer_join_pool', methods=['POST'])
@login_required
def soccer_join_pool():
    data = request.get_json() or {}
    code = (data.get('invite_code') or '').strip().upper()
    if not code:
        return jsonify({'error': 'invite code required'}), 400
    pool = db2("SELECT pool_id, name, status FROM soccer_pools WHERE invite_code=%s", (code,))
    if not pool:
        return jsonify({'error': 'invalid invite code'}), 404
    pool_id, pool_name, pool_status = pool[0]
    if pool_status not in ('open', 'active'):
        return jsonify({'error': 'pool is not accepting new members'}), 400
    db2("INSERT IGNORE INTO soccer_pool_entries (pool_id, user_id) VALUES (%s,%s)",
        (pool_id, session['userid']))
    return jsonify({'success': True, 'pool_id': pool_id, 'pool_name': pool_name})


@bp.route('/api/soccer_pools', methods=['GET'])
@login_required
def soccer_pools():
    uid = session['userid']
    rows = db2("""SELECT p.pool_id, p.name, p.status, p.fee, p.invite_code,
                         p.pts_group, p.pts_r32, p.pts_r16, p.pts_qf, p.pts_sf, p.pts_3rd, p.pts_final
                  FROM soccer_pools p
                  JOIN soccer_pool_entries e ON e.pool_id=p.pool_id AND e.user_id=%s
                  ORDER BY p.created_at DESC""", (uid,))
    return jsonify([{
        'pool_id': r[0], 'name': r[1], 'status': r[2], 'fee': r[3], 'invite_code': r[4],
        'pts_group': r[5], 'pts_r32': r[6], 'pts_r16': r[7],
        'pts_qf': r[8], 'pts_sf': r[9], 'pts_3rd': r[10], 'pts_final': r[11],
    } for r in (rows or [])])


# ── USER: POOL DETAIL ─────────────────────────────────────────────────────────

@bp.route('/api/soccer_pool', methods=['GET'])
@login_required
def soccer_pool():
    pool_id = request.args.get('pool_id', type=int)
    if not pool_id:
        return jsonify({'error': 'pool_id required'}), 400

    uid = session['userid']

    pool_row = db2("""SELECT pool_id, name, status, invite_code, fee, created_by,
                             pts_group, pts_r32, pts_r16, pts_qf, pts_sf, pts_3rd, pts_final,
                             pick_format, pts_group_draw
                      FROM soccer_pools WHERE pool_id=%s""", (pool_id,))
    if not pool_row:
        return jsonify({'error': 'pool not found'}), 404
    p = pool_row[0]
    pool = {
        'pool_id': p[0], 'name': p[1], 'status': p[2], 'invite_code': p[3],
        'fee': p[4], 'created_by': p[5],
        'pts_group': p[6], 'pts_r32': p[7], 'pts_r16': p[8],
        'pts_qf': p[9], 'pts_sf': p[10], 'pts_3rd': p[11], 'pts_final': p[12],
        'pick_format': p[13] or 'standard', 'pts_group_draw': p[14] or 0,
    }

    is_member = bool(db2("SELECT 1 FROM soccer_pool_entries WHERE pool_id=%s AND user_id=%s", (pool_id, uid)))
    can_manage = _can_manage_pool(pool_id)

    t_id = _get_tournament_id()
    match_rows = db2("""SELECT match_id, espn_event_id,
                               home_espn_team_id, home_name, home_abbr, home_logo,
                               away_espn_team_id, away_name, away_abbr, away_logo,
                               match_date, round_type, group_letter, match_order,
                               status, home_score, away_score, result, venue
                        FROM soccer_matches WHERE tournament_id=%s
                        ORDER BY match_date ASC, match_order ASC""", (t_id,))

    now_utc = datetime.utcnow()
    matches = []
    for r in (match_rows or []):
        md = r[10]
        matches.append({
            'match_id': r[0], 'espn_event_id': r[1],
            'home_espn_team_id': r[2], 'home_name': r[3], 'home_abbr': r[4], 'home_logo': r[5],
            'away_espn_team_id': r[6], 'away_name': r[7], 'away_abbr': r[8], 'away_logo': r[9],
            'match_date': (md.isoformat() + 'Z') if md else None,
            'round_type': r[11], 'group_letter': r[12], 'match_order': r[13],
            'status': r[14], 'home_score': r[15], 'away_score': r[16], 'result': r[17],
            'venue': r[18] or '',
            'is_locked': md is not None and md <= now_utc,
        })

    # Current user's picks keyed by match_id
    pick_rows = db2("SELECT match_id, pick FROM soccer_picks WHERE pool_id=%s AND user_id=%s", (pool_id, uid))
    user_picks = {r[0]: r[1] for r in (pick_rows or [])}

    # All picks for this pool: {match_id: {user_id: pick}}
    all_pick_rows = db2("SELECT user_id, match_id, pick FROM soccer_picks WHERE pool_id=%s", (pool_id,))
    all_picks = {}
    for row in (all_pick_rows or []):
        all_picks.setdefault(row[1], {})[row[0]] = row[2]

    # Members
    member_rows = db2("""SELECT e.user_id, u.username, e.paid
                         FROM soccer_pool_entries e
                         JOIN users u ON u.userid=e.user_id
                         WHERE e.pool_id=%s ORDER BY u.username""", (pool_id,))
    members = [{'user_id': r[0], 'username': r[1], 'paid': r[2]} for r in (member_rows or [])]

    # Deputies
    deputy_rows = db2("""SELECT d.user_id, u.username
                         FROM soccer_pool_deputies d
                         JOIN users u ON u.userid=d.user_id
                         WHERE d.pool_id=%s""", (pool_id,))
    deputies = [{'user_id': r[0], 'username': r[1]} for r in (deputy_rows or [])]

    standings = _compute_standings(pool_id)

    return jsonify({
        'pool': pool,
        'matches': matches,
        'user_picks': user_picks,
        'all_picks': all_picks,
        'members': members,
        'deputies': deputies,
        'standings': standings,
        'is_member': is_member,
        'can_manage': can_manage,
        'current_user': {'user_id': uid, 'username': session.get('username')},
    })


# ── USER: PICKS ───────────────────────────────────────────────────────────────

@bp.route('/api/soccer_pick', methods=['POST'])
@login_required
def soccer_pick():
    data = request.get_json() or {}
    pool_id = data.get('pool_id')
    match_id = data.get('match_id')
    pick = (data.get('pick') or '').strip().upper()

    if not pool_id or not match_id or pick not in ('H', 'D', 'A'):
        return jsonify({'error': 'pool_id, match_id, and valid pick (H/D/A) required'}), 400

    uid = session['userid']
    if not db2("SELECT 1 FROM soccer_pool_entries WHERE pool_id=%s AND user_id=%s", (pool_id, uid)):
        return jsonify({'error': 'not a pool member'}), 403

    match = db2("SELECT match_date, round_type FROM soccer_matches WHERE match_id=%s", (match_id,))
    if not match:
        return jsonify({'error': 'match not found'}), 404

    match_date, round_type = match[0]
    if match_date and match_date <= datetime.utcnow():
        return jsonify({'error': 'match has already started'}), 400

    if round_type != 'group' and pick == 'D':
        return jsonify({'error': 'draw not allowed in knockout rounds'}), 400

    if round_type == 'group' and pick == 'D':
        pool_row = db2("SELECT pick_format FROM soccer_pools WHERE pool_id=%s", (pool_id,))
        if pool_row and pool_row[0][0] == 'winner_only':
            return jsonify({'error': 'draw not allowed in this pool format'}), 400

    db2("""INSERT INTO soccer_picks (pool_id, user_id, match_id, pick)
           VALUES (%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE pick=%s, submitted_at=CURRENT_TIMESTAMP""",
        (pool_id, uid, match_id, pick, pick))

    return jsonify({'success': True})
