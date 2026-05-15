# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Dev Commands

**Backend (Flask):**
```bash
source venv/bin/activate
python app.py
```
Runs on port 5000. Requires `.env` with `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`, `CAPTCHA_SECRET`, `APP_ENV=dev`.

**Frontend (React/Vite):**
```bash
cd frontend
npm run dev      # dev server on :5173, proxies /api → localhost:5000
npm run build    # outputs to ../static/dist (what Flask serves in prod)
npm run lint     # eslint
```

In dev, run both simultaneously. Vite proxies all `/api` calls to Flask so CORS is not a concern locally.

**Prod build flow:** `npm run build` → Flask serves `static/dist/index.html` for all non-API routes.

---

## Architecture

### Request flow

```
Browser → Flask (app.py)
  ├── /api/* → Blueprint handlers → db2() → MySQL
  ├── /app/* → serves static/dist/index.html (React SPA)
  └── legacy routes → redirect to /app/<path>
```

Flask is purely an API server + static file host. There are no Jinja templates in active use — all UI is React.

### Frontend

React 19 SPA with React Router 7, `basename="/app"`. Entry point is `frontend/src/main.jsx`.

- `App.jsx` — defines all 47 routes; nearly all are wrapped in `<ProtectedRoute />`
- `SessionContext.jsx` — single global context; fetches `/api/me` on mount, exposes `{ logged_in, username, is_admin, has_golf_grant, has_golf_deputy }`
- `ProtectedRoute.jsx` — redirects to `/login` if `session.logged_in` is false
- `components/Layout.jsx` — shared nav shell

### Backend

7 blueprints registered in `app.py`, all without a URL prefix (routes start directly with `/` or `/api/`):

| Blueprint | File | Domain |
|---|---|---|
| `auth_bp` | blueprints/auth.py | Login, register, `/api/me`, session |
| `boxes_bp` | blueprints/boxes.py | Box pool games (dailybox, custom, nutcracker, private) |
| `admin_bp` | blueprints/admin.py | User/alias mgmt, money, admin views |
| `pickem_bp` | blueprints/pickem.py | Pick'em and bowl games |
| `survivor_bp` | blueprints/survivor.py | Survivor elimination pools |
| `golf_bp` | blueprints/golf.py | Golf draft pools |
| `horse_racing_bp` | blueprints/horse_racing.py | Horse racing draft pools |

### Database

No ORM. All queries use `db2()` from `db_accessor/db_accessor.py`:

```python
from db_accessor.db_accessor import db2

rows = db2("SELECT * FROM users WHERE userid = %s", (userid,))   # returns list of tuples
db2("UPDATE users SET balance = %s WHERE userid = %s", (bal, uid))  # returns ()
```

10-connection MySQL pool. Always use parameterized queries (`%s`). Auto-commits writes.

### Auth

Session-based (Flask-Session, filesystem, 7-day lifetime). Session stores `userid`, `username`, `is_admin`.

**Backend decorators** (in `utils.py`):
- `@login_required` — redirects non-authenticated to `/app/login`
- `@api_admin_required` — returns 403 JSON for non-admins (use on API routes)
- `@golf_admin_required` — allows super admins, golf grant holders, or pool deputies

**Frontend:** `useSession()` hook from `SessionContext` gives current user state.

### ESPN Integration

`services/espn_client.py` wraps ESPN's public API with in-memory TTL caching. Used for live NFL scores, PGA golf events/rankings, and quarterly/per-minute score breakdowns. Called directly from blueprint handlers — not a background job.

`score_checker.py` is a separate script that polls ESPN and writes scores to the DB. It runs as a standalone process on the production server (GoDaddy), not as part of the Flask app.

### Game types

Defined in `constants.py`:
- **BOX_TYPE_ID:** 1=dailybox, 2=custom, 3=nutcracker, 4=private
- **PAY_TYPE_ID:** 1=four_qtr, 2=single, 3=every_score, 4=touch, 5=ten_man, 6=satellite, 7=ten_man_final_reverse, 8=every_minute, 9=ten_man_final_half

### File uploads

Images (png/jpg/jpeg/gif) uploaded via `/upload_file` and `/remove_image` routes in `boxes.py`. Upload folder is configured on the Flask instance.

---

## No test suite

There are no automated tests. Manual testing only. Ad-hoc ESPN API scripts live in `line_checker/`.

---

## Future: iOS (planned summer 2026)

`IOS_PLAN.md` in the repo root documents a Capacitor hybrid wrapper plan. The existing site and API stay unchanged; Capacitor adds an iOS layer. Not started yet.
