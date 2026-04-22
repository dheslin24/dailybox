from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from db_accessor.db_accessor import db, db2
from constants import PAY_TYPE_ID, BOX_TYPE_ID, EMOJIS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from utils import apology, login_required, admin_required
from services.box_service import get_games
from services.espn_client import get_all_games_for_week
from funnel_helper import elimination_check
from datetime import datetime, timedelta, timezone
import pytz
import logging

bp = Blueprint('survivor', __name__)


@bp.route('/sv_create_pool', methods=['GET', 'POST'])
def sv_create_pool():
    # Only allow admin users
    if session.get('is_admin') != 1:
        return redirect('/survivor_pool')
    error = None
    success = None
    if request.method == 'POST':
        pool_name = request.form.get('pool_name')
        pool_password = request.form.get('pool_password')
        user_id = session.get('userid')
        if not pool_name or not pool_password:
            error = 'Pool name and password are required.'
        else:
            # Check for duplicate pool_name
            check_q = f"SELECT pool_id FROM sv_pools WHERE pool_name = '{pool_name}'"
            exists = db2(check_q)
            if exists:
                error = f'A pool with the name "{pool_name}" already exists. Please choose a different name.'
                pool_id = None
            else:
                # Insert new pool into sv_pools, set current user as admin
                q = f"INSERT INTO sv_pools (pool_name, password, admin) VALUES ('{pool_name}', '{pool_password}', '{user_id}')"
                try:
                    db2(q)
                    # Fetch the pool_id using the unique pool_name
                    get_id_q = f"SELECT pool_id FROM sv_pools WHERE pool_name = '{pool_name}'"
                    result = db2(get_id_q)
                    pool_id = result[0][0] if result and len(result) > 0 else None
                    success = f'Survivor pool "{pool_name}" created successfully.'
                except Exception as e:
                    error = f'Error creating pool: {e}'
                    pool_id = None
    else:
        pool_id = None
    return render_template('sv_create_pool.html', error=error, success=success, pool_id=pool_id)


@bp.route("/survivor_pool", methods=["POST", "GET"])
def survivor_pool():
    """
    Displays the survivor pool page, which is a list of all survivor pools and the pools the user is already in
    """
    user_id = session.get('userid')
    user_pools = []
    if user_id:
        # Get pool_ids the user is in
        q = f"SELECT pool_id FROM sv_user_pools WHERE user_id = '{user_id}'"
        pool_ids = db2(q)
        if pool_ids:
            pool_ids_str = ','.join([str(row[0]) for row in pool_ids])
            # Get pool details from sv_pools
            pools_q = f"SELECT pool_id, pool_name FROM sv_pools WHERE pool_id IN ({pool_ids_str})"
            user_pools = db2(pools_q)
    return render_template("survivor_pool.html", user_pools=user_pools)

# Add route for survivor_week_display
@bp.route('/survivor_week_display', methods=['GET', 'POST'])
def survivor_week_display():
    week = request.args.get('week', default=1, type=int)
    season = request.args.get('season', default=2025, type=int)
    pool_id = request.args.get('pool_id', type=int)
    user_id = session.get('userid')
    if request.method == 'POST':
        # If pool_id not in args, get from form
        pool_id = pool_id or request.form.get('pool_id', type=int)
    games = get_all_games_for_week(season_type=2, week=week, league='nfl', season=season)
    # games = get_all_games_for_week(season_type=1, week=week, league='nfl', season=season) # testing with preseason
    est = pytz.timezone('US/Eastern')
    now_utc = datetime.now(timezone.utc)
    for game in games:
        if 'start_date' in game and game['start_date']:
            # ESPN API returns ISO8601 string, e.g. '2025-08-10T15:30Z'
            dt_str = game['start_date'].replace('Z', '')
            try:
                dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            except Exception:
                # fallback for other formats
                dt_utc = datetime.fromisoformat(dt_str)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            dt_est = dt_utc.astimezone(est)
            game['display_datetime'] = dt_est.strftime('%a %b %d %H:%M EST')
            # Lock team selection if current time is after (start_time - 5 min)
            lock_time = dt_utc - timedelta(minutes=5)
            game['locked'] = now_utc > lock_time
    selected_team = None
    selected_logo = None
    if request.method == 'POST':
        selected_team = request.form.get('selected_team')
        selected_logo = request.form.get('selected_logo')
    # Query all picks for this user and pool_id across all weeks
    used_teams = {}
    if user_id and pool_id:
        s = f"SELECT week, pick FROM sv_picks WHERE user_id = '{user_id}' AND pool_id = '{pool_id}' AND (week, pick_id) IN (SELECT week, MAX(pick_id) FROM sv_picks WHERE user_id = '{user_id}' AND pool_id = '{pool_id}' GROUP BY week)"
        picks = db2(s)
        for row in picks:
            used_teams[row[1]] = row[0]  # {team: week}
    return render_template('survivor_week_display.html', games=games, selected_team=selected_team, selected_logo=selected_logo, week=week, pool_id=pool_id, used_teams=used_teams)


# Handle submit button for selected team
@bp.route('/submit_team', methods=['POST'])
def submit_team():
    user_id = session.get('userid')
    if not user_id:
        return redirect(url_for('auth.login'))
    team = request.form.get('team')
    logo = request.form.get('logo')
    week = request.form.get('week')
    pool_id = request.form.get('pool_id') or request.args.get('pool_id')
    season = request.form.get('season') or request.args.get('season') or 2025
    print(f"Team submitted: {team}, Logo: {logo}, Week: {week}, pool ID {pool_id}, Season: {season}")
    # Backend validation: check game start time
    games = get_all_games_for_week(season_type=2, week=int(week), league='nfl', season=int(season))
    # Find the game for the selected team
    game_start_utc = None
    for game in games:
        if team == game.get('home_team') or team == game.get('away_team'):
            if 'start_date' in game and game['start_date']:
                dt_str = game['start_date'].replace('Z', '')
                try:
                    dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                except Exception:
                    dt_utc = datetime.fromisoformat(dt_str)
                    if dt_utc.tzinfo is None:
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                game_start_utc = dt_utc
                break
    now_utc = datetime.now(timezone.utc)
    if game_start_utc:
        lock_time = game_start_utc - timedelta(minutes=5)
        if now_utc > lock_time:
            # Too late to pick
            return render_template('survivor_teams_selected.html', error="Too late to pick this team. Picks must be made at least 5 minutes before game start.", pool_id=pool_id)
    # Otherwise, allow pick
    s = "INSERT INTO sv_picks(user_id, pool_id, week, pick, logo) VALUES(%s, %s, %s, %s, %s);"
    db2(s, (user_id, pool_id, week, team, logo))
    s_picks = f"SELECT week, pick, logo FROM sv_picks WHERE user_id = '{user_id}' AND (week, pick_id) IN (SELECT week, MAX(pick_id) FROM sv_picks WHERE user_id = '{user_id}' GROUP BY week) ORDER BY week ASC;"
    picks = db2(s_picks)
    return redirect(url_for('survivor.survivor_teams_selected', pool_id=pool_id))

# Route to handle team clicks
@bp.route('/team_click', methods=['POST'])
def team_click():
    team = request.form.get('team')
    game_id = request.form.get('game_id')
    logo = request.form.get('logo')
    week = request.args.get('week', default=1, type=int)
    print(f"Team clicked: {team}, Game ID: {game_id}, Logo: {logo}")
    return render_template('team_selected.html', team=team, logo=logo, week=week)

@bp.route('/survivor_teams_selected', methods=['POST', 'GET'])
def survivor_teams_selected():
    user_id = session.get('userid')
    pool_id = request.args.get('pool_id')
    s = f"SELECT week, pick, logo FROM sv_picks WHERE user_id = '{user_id}' AND pool_id = '{pool_id}' AND (week, pick_id) IN (SELECT week, MAX(pick_id) FROM sv_picks WHERE user_id = '{user_id}' AND pool_id = '{pool_id}' GROUP BY week) ORDER BY week ASC;"
    picks_raw = db2(s)
    # Get game start times for each pick to determine locked status
    from datetime import datetime, timezone
    season = request.args.get('season', default=2025, type=int)
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
                        dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    except Exception:
                        dt_utc = datetime.fromisoformat(dt_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    locked = now_utc > dt_utc
                break
        picks.append((week, team, logo, locked))
    pool_name = None
    if pool_id:
        q = f"SELECT pool_name FROM sv_pools WHERE pool_id = '{pool_id}'"
        result = db2(q)
        if result and len(result) > 0:
            pool_name = result[0][0]
    return render_template('survivor_teams_selected.html', picks=picks, pool_id=pool_id, pool_name=pool_name)

# Route to display all users and their picks for a given pool
@bp.route('/survivor_pool_picks')
def survivor_pool_picks():
    pool_id = request.args.get('pool_id', type=int)
    season = request.args.get('season', default=2025, type=int)
    user_id = session.get('userid')
    # Get all users in this pool
    user_rows = db2(f"SELECT u.userid, u.username FROM users u JOIN sv_user_pools up ON u.userid = up.user_id WHERE up.pool_id = '{pool_id}'")
    users = [{'user_id': row[0], 'username': row[1]} for row in user_rows]
    # Get all weeks for this pool (from sv_picks)
    week_rows = db2(f"SELECT DISTINCT week FROM sv_picks WHERE pool_id = '{pool_id}' ORDER BY week ASC")
    weeks = [row[0] for row in week_rows]
    # Get all picks for all users in this pool
    pick_rows = db2(f"SELECT user_id, week, pick, logo FROM sv_picks WHERE pool_id = '{pool_id}'")
    # Get all games for all weeks
    games_by_week = {}
    for week in weeks:
        games_by_week[week] = get_all_games_for_week(season_type=2, week=week, league='nfl', season=season)
        # games_by_week[week] = get_all_games_for_week(season_type=1, week=week, league='nfl', season=season)  # testing with preseason
    # Build pick dict with win/lose and locked info
    picks = {}
    for row in pick_rows:
        uid, week, team, logo = row
        # Find game start time for this pick
        locked = False
        result = False
        for game in games_by_week[week]:
            if team == game.get('home_team') or team == game.get('away_team'):
                logging.info(f"Found game for team {team} in week {week}: {game}")
                if 'start_date' in game and game['start_date']:
                    dt_str = game['start_date'].replace('Z', '')
                    try:
                        dt_utc = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    except Exception:
                        dt_utc = datetime.fromisoformat(dt_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    locked = now_utc > dt_utc
                if game.get('winner_team'):
                    logging.info(f"Game winner: {game['winner_team']}")
                    # If game has a winner, set result
                    if team == game['winner_team']:
                        result = 'win'
                    else:
                        result = 'lose'
                break
        picks[(uid, week)] = {'team': team, 'logo': logo, 'locked': locked, 'result': result}
    logging.info(f"picks {picks}")
    return render_template('survivor_pool_picks.html', users=users, weeks=weeks, picks=picks)

# Route to handle joining a pool
@bp.route('/join_pool', methods=['POST'])
def join_pool():
    pool_id = request.form.get('pool_id')
    pool_name = request.form.get('pool_name')
    pool_password = request.form.get('pool_password')
    found = False
    pool_row = None
    # Check by pool_id
    if pool_id:
        s = f"SELECT pool_id FROM sv_pools WHERE pool_id = '{pool_id}' AND password = '{pool_password}'"
        result = db2(s)
        if result:
            found = True
            pool_row = result[0]
    # Check by pool_name if not found
    if not found and pool_name:
        s = f"SELECT pool_id FROM sv_pools WHERE pool_name = '{pool_name}' AND password = '{pool_password}'"
        result = db2(s)
        if result:
            found = True
            pool_row = result[0]
    if found:
        user_id = session.get('userid')
        pool_id_val = pool_row[0]
        # Add user to sv_user_pools only if not already present
        check_q = f"SELECT 1 FROM sv_user_pools WHERE user_id = '{user_id}' AND pool_id = '{pool_id_val}'"
        exists = db2(check_q)
        if not exists:
            insert_q = f"INSERT INTO sv_user_pools (user_id, pool_id, active) VALUES ('{user_id}', '{pool_id_val}', 1)"
            db2(insert_q)
            print(f"User {user_id} added to pool {pool_id_val}")
            return redirect(url_for('survivor.survivor_teams_selected', pool_id=pool_id_val))
        else:
            print(f"User {user_id} is already in pool {pool_id_val}")
            return redirect(url_for('survivor.survivor_teams_selected', pool_id=pool_id_val))
    else:
        print(f"No matching pool for ID={pool_id}, Name={pool_name}")
        return "No matching pool found."
