# iOS App Plan — Capacitor Approach

> **Status:** Future project, planned for summer 2026. Site stays untouched.

---

## Goal

Wrap the existing Dailybox React SPA in a Capacitor iOS shell and submit to the App Store. The web app and Flask API remain completely unchanged — this adds an iOS layer on top.

---

## Why Capacitor

- React SPA + Flask API are already cleanly separated — the hard work is done
- 47 JSON API endpoints are already the iOS backend
- Reuses all existing React components; no UI rewrite
- Fastest path to App Store (~12–20 focused sessions)
- Existing site is untouched throughout

---

## Hard Prerequisites (resolve before starting)

| Item | Notes |
|---|---|
| **Mac with Xcode** | Only needed for the final ~10% — iOS build, simulator testing, App Store submission |
| **Apple Developer account** | $99/year at developer.apple.com |
| **Privacy policy URL** | App Store requires one — even a simple one |
| **Production HTTPS** | Already likely in place; confirm |

---

## Session-by-Session Plan

### Phase 1: Capacitor Setup (1–2 sessions)
- `npm install @capacitor/core @capacitor/cli` in `/frontend`
- `npx cap init` — set App ID (e.g. `com.dailybox.app`) and app name
- Create `capacitor.config.ts` pointing at production server URL
- `npx cap add ios`
- Verify app loads in browser via `npx cap serve`

### Phase 2: iOS Simulator Build (1–2 sessions, requires Mac)
- `npm run build && npx cap sync`
- Open in Xcode: `npx cap open ios`
- Run in iPhone simulator — identify layout/crash issues
- Fix any white screen / routing issues (React Router + Capacitor quirks)

### Phase 3: Mobile UX Fixes (4–8 sessions — bulk of work)
Priority fixes for small screens:
- Bootstrap 3 tables (boxes grid, golf leaderboard, pick'em standings) — need horizontal scroll or responsive reflow
- Navigation — may need a hamburger menu or bottom tab bar
- Touch targets — buttons/links need to be finger-friendly (min 44px)
- Draft order pages — heavy table layouts, need mobile audit
- Forms — ensure inputs don't zoom on focus (font-size >= 16px)

### Phase 4: Auth & CORS Verification (1–2 sessions)
- Capacitor WebViews handle cookies like a browser — Flask sessions should work as-is
- Verify login/logout/session persistence on device
- Add CORS origin for the Capacitor app if needed in Flask
- Test protected routes behave correctly

### Phase 5: App Store Prep (2–3 sessions)
- App icons (1024×1024 master, Xcode generates sizes)
- Launch screen
- Screenshots for all required device sizes (iPhone 6.9", 6.5", 5.5")
- App Store Connect: app name, subtitle, description, keywords, category (Sports or Games)
- Privacy policy URL
- Age rating questionnaire
- First submission

### Phase 6: Review & Fixes (1–3 sessions)
- Apple review: 1–7 days
- Common rejection reasons: crashes on reviewer device, missing privacy policy, web wrapper flag
- Iterate until approved

---

## Known Gotchas

**React Router + Capacitor:** The app uses React Router with browser history. Capacitor needs hash-based routing or a custom history config — will need a small config change in `App.jsx` or `vite.config.js`.

**ESPN API calls:** These go server→ESPN, not client→ESPN, so no CORS issues there.

**Flask sessions on device:** Should work fine. If not, the fallback is migrating auth to JWTs stored in Capacitor's SecureStorage plugin — heavier lift but doable.

**Bootstrap 3:** Old and not mobile-first. We'll fix layouts as we encounter them rather than a full Bootstrap upgrade (too risky).

---

## What Stays Completely Unchanged

- All Flask blueprints and API routes
- MySQL database and schema
- ESPN integration and score polling
- AWS SES email
- The existing website at its current URL

---

## After Launch (optional next steps)

- **Push notifications** via Capacitor Push Notifications plugin + APNs backend
- **Biometric auth** (Face ID) via Capacitor Biometrics plugin — low effort, high polish
- **Android** — Capacitor supports it; `npx cap add android` + Android Studio build
- **React Native migration** — if the app gains traction and you want a truly native feel

---

## Starting Point When Ready

```bash
cd /home/dheslin/bygtech/dailybox/frontend
npm install @capacitor/core @capacitor/cli @capacitor/ios
npx cap init
```

First session goal: get Capacitor installed and the app loading via `npx cap serve`.
