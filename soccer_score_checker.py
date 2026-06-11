#!/usr/bin/env python3
"""
Cron script — run every 5 minutes via GoDaddy cPanel.
Pulls WC match results from ESPN and writes them to the DB.
Only does real work if any matches are live or finishing soon.

GoDaddy cPanel setup:
  */5 * * * * cd /path/to/dailybox && /path/to/venv/bin/python soccer_score_checker.py >> /path/to/logs/soccer_checker.log 2>&1
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from services.espn_client import get_world_cup_matches, invalidate_wc_cache
from db_accessor.db_accessor import db2


def run():
    invalidate_wc_cache()
    matches = get_world_cup_matches()
    if not matches:
        return

    now = datetime.utcnow()
    window_start = now - timedelta(hours=3)
    window_end = now + timedelta(hours=3)

    active = [
        m for m in matches
        if m['status'] in ('in_progress', 'final')
        or (m['match_date'] and window_start <= m['match_date'] <= window_end)
    ]
    if not active:
        return  # nothing happening nearby — skip updates

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

    print(f"[{now.isoformat()}] soccer_score_checker: {updated} matches updated")


if __name__ == '__main__':
    run()
