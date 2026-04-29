from flask import Blueprint, jsonify, request, session
from db_accessor.db_accessor import db2
from utils import login_required
from services.espn_client import get_all_games_for_week
from datetime import datetime, timedelta, timezone
import pytz
import logging

bp = Blueprint('survivor', __name__)


@bp.route('/api/sv_create_pool', methods=['POST'])
def api_sv_create_pool():
    if session.get('is_admin') != 1:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    pool_name = data.get('pool_name', '').strip()
    pool_password = data.get('pool_password', '').strip()
    if not pool_name or not pool_password:
        return jsonify({'error': 'Pool name and password are required.'})
    if db2("SELECT pool_id FROM sv_pools WHERE pool_name = %s", (pool_name,)):
        return jsonify({'error': f'A pool named "{pool_name}" already exists.'})
    try:
        db2("INSERT INTO sv_pools (pool_name, password, admin) VALUES (%s, %s, %s)", (pool_name, pool_password, session['userid']))
        result = db2("SELECT pool_id FROM sv_pools WHERE pool_name = %s", (pool_name,))
        return jsonify({'success': True, 'pool_id': result[0][0] if result else None, 'pool_name': pool_name})
    except Exception as e:
        return jsonify({'error': str(e)})

@bp.route("/api/survivor_pool", methods=["GET"])
@login_required
def api_survivor_pool():
    user_id = session.get('userid')
    user_pools = []
    if user_id:
        pool_ids = db2("SELECT pool_id FROM sv_user_pools WHERE user_id = %s", (user_id,))
        if pool_ids:
            pool_ids_str = ','.join([str(row[0]) for row in pool_ids])
            rows = db2(f"SELECT pool_id, pool_name FROM sv_pools WHERE pool_id IN ({pool_ids_str})")
            user_pools = [{'pool_id': r[0], 'pool_name': r[1]} for r in rows]
    return jsonify({'user_pools': user_pools})


@bp.route("/api/join_pool", methods=["POST"])
@login_required
def api_join_pool():
    data = request.get_json()
    pool_id = data.get('pool_id')
    pool_name = data.get('pool_name')
    pool_password = data.get('pool_password')
    pool_row = None
    if pool_id:
        result = db2("SELECT pool_id FROM sv_pools WHERE pool_id = %s AND password = %s", (pool_id, pool_password))
        if result: pool_row = result[0]
    if not pool_row and pool_name:
        result = db2("SELECT pool_id FROM sv_pools WHERE pool_name = %s AND password = %s", (pool_name, pool_password))
        if result: pool_row = result[0]
    if pool_row:
        user_id = session.get('userid')
        pid = pool_row[0]
        exists = db2("SELECT 1 FROM sv_user_pools WHERE user_id = %s AND pool_id = %s", (user_id, pid))
        if not exists:
            db2("INSERT INTO sv_user_pools (user_id, pool_id, active) VALUES (%s, %s, 1)", (user_id, pid))
        return jsonify({'success': True, 'pool_id': pid})
    return jsonify({'error': 'No matching pool found.'})


@bp.route("/api/survivor_teams_selected", methods=["GET"])
@login_required
def api_survivor_teams_selected():
    user_id = session.get('userid')
    pool_id = request.args.get('pool_id')
    season = request.args.get('season', default=2025, type=int)
    picks_raw = db2(
        "SELECT week, pick, logo FROM sv_picks WHERE user_id = %s AND pool_id = %s AND (week, pick_id) IN (SELECT week, MAX(pick_id) FROM sv_picks WHERE user_id = %s AND pool_id = %s GROUP BY week) ORDER BY week ASC;",
        (user_id, pool_id, user_id, pool_id)
    )
    picks = []
    for pick in picks_raw:
        week, team, logo = pick
        locked = False
        games = get_all_games_for_week(season_type=2, week=week, league='nfl', season=season)
        for game in games:
            if team == game.get('home_team') or team == game.get('away_team'):
                if 'start_date' in game and game['start_date']:
                    dt_str = game['start_date'].replace('Z', '')
                    try:
                        dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
                    except Exception:
                        dt_utc = datetime.fromisoformat(dt_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    locked = datetime.now(timezone.utc) > dt_utc
                break
        picks.append({'week': week, 'team': team, 'logo': logo, 'locked': locked})
    pool_name = None
    if pool_id:
        result = db2("SELECT pool_name FROM sv_pools WHERE pool_id = %s", (pool_id,))
        if result: pool_name = result[0][0]
    return jsonify({'picks': picks, 'pool_name': pool_name, 'pool_id': pool_id})


@bp.route("/api/survivor_week_display", methods=["GET"])
@login_required
def api_survivor_week_display():
    week = request.args.get('week', default=1, type=int)
    season = request.args.get('season', default=2025, type=int)
    pool_id = request.args.get('pool_id', type=int)
    user_id = session.get('userid')
    games = get_all_games_for_week(season_type=2, week=week, league='nfl', season=season)
    est = pytz.timezone('US/Eastern')
    now_utc = datetime.now(timezone.utc)
    for game in games:
        if 'start_date' in game and game['start_date']:
            dt_str = game['start_date'].replace('Z', '')
            try:
                dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
            except Exception:
                dt_utc = datetime.fromisoformat(dt_str)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            game['display_datetime'] = dt_utc.astimezone(est).strftime('%a %b %d %H:%M EST')
            game['locked'] = now_utc > dt_utc - timedelta(minutes=5)
    used_teams = {}
    if user_id and pool_id:
        picks = db2(
            "SELECT week, pick FROM sv_picks WHERE user_id = %s AND pool_id = %s AND (week, pick_id) IN (SELECT week, MAX(pick_id) FROM sv_picks WHERE user_id = %s AND pool_id = %s GROUP BY week)",
            (user_id, pool_id, user_id, pool_id)
        )
        for row in picks:
            used_teams[row[1]] = row[0]
    return jsonify({'games': games, 'used_teams': used_teams, 'week': week, 'pool_id': pool_id})


@bp.route("/api/submit_team", methods=["POST"])
@login_required
def api_submit_team():
    data = request.get_json()
    user_id = session.get('userid')
    team = data.get('team')
    logo = data.get('logo')
    week = data.get('week')
    pool_id = data.get('pool_id')
    season = data.get('season', 2025)
    games = get_all_games_for_week(season_type=2, week=int(week), league='nfl', season=int(season))
    now_utc = datetime.now(timezone.utc)
    for game in games:
        if team == game.get('home_team') or team == game.get('away_team'):
            if 'start_date' in game and game['start_date']:
                dt_str = game['start_date'].replace('Z', '')
                try:
                    dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
                except Exception:
                    dt_utc = datetime.fromisoformat(dt_str)
                    if dt_utc.tzinfo is None:
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                if now_utc > dt_utc - timedelta(minutes=5):
                    return jsonify({'error': 'Too late to pick this team. Picks must be made at least 5 minutes before game start.'})
            break
    db2("INSERT INTO sv_picks(user_id, pool_id, week, pick, logo) VALUES(%s, %s, %s, %s, %s);", (user_id, pool_id, week, team, logo))
    return jsonify({'success': True})


@bp.route("/api/survivor_pool_picks", methods=["GET"])
@login_required
def api_survivor_pool_picks():
    pool_id = request.args.get('pool_id', type=int)
    season = request.args.get('season', default=2025, type=int)
    user_id = session.get('userid')
    user_rows = db2("SELECT u.userid, u.username FROM users u JOIN sv_user_pools up ON u.userid = up.user_id WHERE up.pool_id = %s", (pool_id,))
    users = [{'user_id': r[0], 'username': r[1]} for r in user_rows]
    week_rows = db2("SELECT DISTINCT week FROM sv_picks WHERE pool_id = %s ORDER BY week ASC", (pool_id,))
    weeks = [r[0] for r in week_rows]
    pick_rows = db2("SELECT user_id, week, pick, logo FROM sv_picks WHERE pool_id = %s", (pool_id,))
    games_by_week = {w: get_all_games_for_week(season_type=2, week=w, league='nfl', season=season) for w in weeks}
    picks = {}
    for row in pick_rows:
        uid, week, team, logo = row
        locked = False
        result = None
        for game in games_by_week.get(week, []):
            if team == game.get('home_team') or team == game.get('away_team'):
                if 'start_date' in game and game['start_date']:
                    dt_str = game['start_date'].replace('Z', '')
                    try:
                        dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
                    except Exception:
                        dt_utc = datetime.fromisoformat(dt_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    locked = datetime.now(timezone.utc) > dt_utc
                if game.get('winner_team'):
                    result = 'win' if team == game['winner_team'] else 'lose'
                break
        picks[f"{uid}_{week}"] = {'team': team, 'logo': logo, 'locked': locked, 'result': result}
    return jsonify({'users': users, 'weeks': weeks, 'picks': picks, 'current_userid': user_id})
