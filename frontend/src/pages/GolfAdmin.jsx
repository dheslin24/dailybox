import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout'
import { useSession } from '../SessionContext'

const EMPTY_FORM = {
  espn_event_id: '', event_name: '', course: '', event_date: '',
  pool_name: '', fee: '', pool_format: 'draft', draft_type: 'manual', picks_per_user: 4,
  tiebreaker_type: 'player', scoring_players: '', dnf_handling: 'eliminate', dnf_penalty: 1,
  max_entries_per_user: 1,
}

const STATUS_FLOW = ['setup', 'open', 'active', 'complete']

export default function GolfAdmin() {
  const [espnEvents, setEspnEvents]   = useState([])
  const [espnLoading, setEspnLoading] = useState(false)
  const [users, setUsers]             = useState([])
  const [pools, setPools]             = useState([])
  const [selectedPoolId, setSelectedPoolId] = useState(null)
  const [poolDetail, setPoolDetail]   = useState(null)
  const [form, setForm]               = useState(EMPTY_FORM)
  const [draftSlots, setDraftSlots]   = useState(Array(20).fill(''))
  const [adminPick, setAdminPick]     = useState({ user_id: '', espn_id: '', name: '' })
  const [adminTbUser, setAdminTbUser]             = useState('')
  const [adminTbWinScore, setAdminTbWinScore]     = useState('')
  const [tierForm, setTierForm]                   = useState(null)
  const [expandedManualTier, setExpandedManualTier] = useState(null)
  const [manualSelections, setManualSelections]   = useState(new Set())
  const [tierPlayerFilter, setTierPlayerFilter]   = useState('')
  const [msg, setMsg]                 = useState('')
  const [userFilter, setUserFilter]       = useState('')
  const [userSort, setUserSort]           = useState({ col: 'username', dir: 'asc' })
  const [previousUserIds, setPreviousUserIds] = useState(new Set())
  const [showAllUsers, setShowAllUsers]   = useState(false)
  const [userLimit, setUserLimit]         = useState(25)
  const [grants, setGrants]           = useState([])
  const [grantForm, setGrantForm]     = useState({ user_id: '', pools_allowed: 1 })
  const [deputyPickUserId, setDeputyPickUserId] = useState('')

  const session = useSession()
  const isSuperAdmin = session?.is_admin === 1
  const isPoolAdmin  = !isSuperAdmin && session?.has_golf_grant
  const golfGrant    = session?.golf_grant   // { pools_allowed, pools_used }

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(''), 4000) }

  const loadGrants = () => {
    if (!isSuperAdmin) return
    fetch('/api/golf_pool_grants').then(r => r.json()).then(d => setGrants(d.grants || []))
  }

  const loadUsers = () =>
    fetch('/api/golf_users')
      .then(r => r.json())
      .then(d => {
        setUsers(d.users || [])
        const ids = new Set(d.previous_user_ids || [])
        setPreviousUserIds(ids)
        if (ids.size === 0) setShowAllUsers(true)
      })

  const loadPools = () =>
    fetch('/api/golf_admin_pools').then(r => r.json()).then(d => setPools(d.pools || []))

  const loadPoolDetail = useCallback((pool_id) => {
    fetch(`/api/golf_pool?pool_id=${pool_id}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setPoolDetail(d)
        const slots = Array(20).fill('')
        d.participants.forEach(p => { slots[p.pick_order - 1] = String(p.user_id) })
        setDraftSlots(slots)
      })
  }, [])

  useEffect(() => {
    loadUsers()
    loadPools()
    loadGrants()
  }, [isSuperAdmin])

  useEffect(() => {
    if (selectedPoolId) loadPoolDetail(selectedPoolId)
  }, [selectedPoolId, loadPoolDetail])

  const handleLoadEspn = () => {
    setEspnLoading(true)
    fetch('/api/golf_espn_events')
      .then(r => r.json())
      .then(d => { setEspnEvents(d.events || []); setEspnLoading(false) })
      .catch(() => { flash('Failed to load ESPN events'); setEspnLoading(false) })
  }

  const handleSelectEspnEvent = (ev) => {
    setForm(f => ({
      ...f,
      espn_event_id: ev.espn_event_id,
      event_name: ev.name,
      course: '',
      event_date: ev.start_date,
    }))
    fetch(`/api/golf_event_venue?event_id=${ev.espn_event_id}`)
      .then(r => r.json())
      .then(d => { if (d.venue) setForm(f => ({ ...f, course: d.venue })) })
  }

  const handleCreatePool = () => {
    if (!form.espn_event_id || !form.event_name || !form.pool_name)
      return flash('ESPN event, event name, and pool name are required')
    fetch('/api/golf_create_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, picks_per_user: parseInt(form.picks_per_user) }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash(`Pool created (id ${d.pool_id})`)
        setForm(EMPTY_FORM)
        loadPools()
        setSelectedPoolId(d.pool_id)
      })
  }

  const handleInitDb = () => {
    fetch('/api/golf_init_db', { method: 'POST' })
      .then(r => r.json())
      .then(d => flash(d.error || 'DB tables initialised'))
  }

  const handleGrantPoolAdmin = () => {
    if (!grantForm.user_id) return flash('Select a user')
    fetch('/api/golf_grant_pool_admin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: parseInt(grantForm.user_id), pools_allowed: parseInt(grantForm.pools_allowed) }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Grant saved')
        setGrantForm({ user_id: '', pools_allowed: 1 })
        loadGrants()
      })
  }

  const handleSaveDraftOrder = () => {
    const order = draftSlots
      .map((uid, i) => ({ user_id: parseInt(uid), pick_order: i + 1 }))
      .filter(s => s.user_id)
    if (!order.length) return flash('No users assigned to slots')
    fetch('/api/golf_set_draft_order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, order }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Draft order saved')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleRandomize = () => {
    const user_ids = draftSlots.map(Number).filter(Boolean)
    if (!user_ids.length) return flash('Add users to slots before randomizing')
    fetch('/api/golf_randomize_draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_ids }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        const newSlots = Array(20).fill('')
        d.order.forEach((o, i) => {
          const user = users.find(u => u.username === o.username)
          if (user) newSlots[i] = String(user.userid)
        })
        setDraftSlots(newSlots)
        flash('Draft order randomized and saved')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleSetStatus = (status) => {
    fetch('/api/golf_set_pool_status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, status }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash(`Status → ${status}`)
        loadPools()
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleAdminPick = () => {
    if (!adminPick.user_id || !adminPick.espn_id || !adminPick.name)
      return flash('Select user and enter player ESPN ID and name')
    const [pickUserId, pickEntryNum] = adminPick.user_id.split('|')
    fetch('/api/golf_admin_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool_id: selectedPoolId,
        user_id: parseInt(pickUserId),
        entry_number: parseInt(pickEntryNum),
        player_espn_id: adminPick.espn_id,
        player_name: adminPick.name,
      }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Pick set')
        setAdminPick({ user_id: '', espn_id: '', name: '' })
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleAdminSetTiebreaker = (pick_id) => {
    const [tbUserId] = adminTbUser.split('|')
    fetch('/api/golf_admin_set_tiebreaker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: parseInt(tbUserId), pick_id }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Tiebreaker set')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleAdminSetWinningScoreTb = () => {
    if (!adminTbUser || adminTbWinScore === '') return
    const [tbUserId, tbEntryNum] = adminTbUser.split('|')
    fetch('/api/golf_admin_set_winning_score_tb', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: parseInt(tbUserId), entry_number: parseInt(tbEntryNum), score: parseInt(adminTbWinScore) }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Tiebreaker set')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleAddDeputy = () => {
    if (!deputyPickUserId) return
    fetch('/api/golf_add_deputy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: parseInt(deputyPickUserId) }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setDeputyPickUserId('')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleRemoveDeputy = (userId) => {
    fetch('/api/golf_remove_deputy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: userId }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        loadPoolDetail(selectedPoolId)
      })
  }

  const EMPTY_TIER_FORM = { tier_id: null, name: '', tier_type: 'ranking', rank_min: '', rank_max: '', min_picks: 0, max_picks: '' }

  const handleSaveTier = () => {
    if (!tierForm || !tierForm.name.trim()) return
    const url = tierForm.tier_id ? '/api/golf_update_tier' : '/api/golf_create_tier'
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...tierForm, pool_id: selectedPoolId }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setTierForm(null)
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleDeleteTier = (tier_id) => {
    fetch('/api/golf_delete_tier', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tier_id, pool_id: selectedPoolId }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        if (expandedManualTier === tier_id) setExpandedManualTier(null)
        loadPoolDetail(selectedPoolId)
      })
  }

  const openManualAssign = (tier_id) => {
    const existing = poolDetail?.tier_players?.[String(tier_id)] || []
    setManualSelections(new Set(existing))
    setExpandedManualTier(tier_id)
    setTierPlayerFilter('')
  }

  const handleSaveTierPlayers = () => {
    const field = poolDetail?.espn_field || []
    const players = field
      .filter(p => manualSelections.has(String(p.espn_id)))
      .map(p => ({ espn_id: p.espn_id, name: p.name }))
    fetch('/api/golf_save_tier_players', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tier_id: expandedManualTier, pool_id: selectedPoolId, players }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setExpandedManualTier(null)
        loadPoolDetail(selectedPoolId)
      })
  }

  const toggleManualPlayer = (espn_id) => {
    setManualSelections(prev => {
      const next = new Set(prev)
      if (next.has(String(espn_id))) next.delete(String(espn_id))
      else next.add(String(espn_id))
      return next
    })
  }

  const handleSetPaid = (user_id, entry_number, paid) => {
    fetch('/api/golf_set_paid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id, entry_number, paid }),
    })
      .then(r => r.json())
      .then(d => { if (!d.error) loadPoolDetail(selectedPoolId) })
  }

  const pool = poolDetail?.pool
  const espnField = poolDetail?.espn_field || []

  return (
    <Layout>
      <h2>Golf Pool Admin</h2>

      {msg && <div className="alert alert-info">{msg}</div>}

      {/* Init DB — super admin only */}
      {isSuperAdmin && (
        <div className="row" style={{ marginBottom: 20 }}>
          <div className="col-md-12">
            <button className="btn btn-default btn-sm" onClick={handleInitDb}>
              Initialize DB Tables
            </button>
          </div>
        </div>
      )}

      {/* Grant Pool Admin Access — super admin only */}
      {isSuperAdmin && (
        <div className="panel panel-warning">
          <div className="panel-heading"><strong>Grant Golf Pool Admin Access</strong></div>
          <div className="panel-body">
            <div className="row">
              <div className="col-md-8">
                <div className="form-inline" style={{ marginBottom: 12 }}>
                  <select className="form-control input-sm" style={{ marginRight: 8, minWidth: 200 }}
                    value={grantForm.user_id}
                    onChange={e => setGrantForm(f => ({ ...f, user_id: e.target.value }))}>
                    <option value="">— select user —</option>
                    {users.map(u => (
                      <option key={u.userid} value={u.userid}>{u.username} — {u.first_name} {u.last_name}</option>
                    ))}
                  </select>
                  <label style={{ marginRight: 6 }}>Pools allowed:</label>
                  <input type="number" min="1" max="20" className="form-control input-sm"
                    style={{ width: 70, marginRight: 8 }}
                    value={grantForm.pools_allowed}
                    onChange={e => setGrantForm(f => ({ ...f, pools_allowed: e.target.value }))} />
                  <button className="btn btn-warning btn-sm" onClick={handleGrantPoolAdmin}>
                    Save Grant
                  </button>
                </div>
                {grants.length > 0 && (
                  <table className="table table-condensed table-bordered" style={{ marginBottom: 0 }}>
                    <thead>
                      <tr><th>User</th><th>Pools Allowed</th><th>Used</th><th>Granted By</th><th>Date</th></tr>
                    </thead>
                    <tbody>
                      {grants.map(g => (
                        <tr key={g.grant_id}
                          style={g.pools_used >= g.pools_allowed ? { color: '#9ca3af' } : {}}>
                          <td><strong>{g.username}</strong></td>
                          <td>{g.pools_allowed}</td>
                          <td>{g.pools_used}</td>
                          <td>{g.granted_by}</td>
                          <td style={{ fontSize: 11 }}>{g.created_at?.slice(0, 10)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pool Selector */}
      {pools.length > 0 && (
        <div className="panel panel-info">
          <div className="panel-heading"><strong>Manage Existing Pool</strong></div>
          <div className="panel-body">
            <div className="row">
              <div className="col-md-6">
                <select className="form-control"
                  value={selectedPoolId || ''}
                  onChange={e => setSelectedPoolId(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">— select a pool —</option>
                  {pools.map(p => (
                    <option key={p.pool_id} value={p.pool_id}>
                      {p.name} ({p.event_name}) — {p.status}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Pool */}
      <div className="panel panel-default">
        <div className="panel-heading">
          <strong>Create New Pool</strong>
          {isPoolAdmin && golfGrant && (
            <span style={{ marginLeft: 12, fontSize: 13 }}>
              {golfGrant.pools_allowed - golfGrant.pools_used > 0
                ? <span className="label label-success">
                    {golfGrant.pools_allowed - golfGrant.pools_used} of {golfGrant.pools_allowed} remaining
                  </span>
                : <span className="label label-danger">No pools remaining</span>
              }
            </span>
          )}
        </div>
        <div className="panel-body" style={{ maxWidth: 860 }}>

          {/* Step 1: pick a tournament */}
          <h5 style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: 6, marginBottom: 12 }}>
            Step 1 — Select Tournament
          </h5>
          <button className="btn btn-info btn-sm" onClick={handleLoadEspn} disabled={espnLoading}>
            {espnLoading ? 'Loading…' : 'Load Upcoming ESPN Events'}
          </button>
          {espnEvents.length > 0 && (
            <table className="table table-condensed table-bordered" style={{ marginTop: 12 }}>
              <thead>
                <tr><th>Event</th><th>Dates</th><th>Venue</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {espnEvents.map(ev => (
                  <tr key={ev.espn_event_id}
                    style={form.espn_event_id === ev.espn_event_id ? { background: '#dff0d8' } : {}}>
                    <td>{ev.name}</td>
                    <td>{ev.start_date}{ev.end_date && ev.end_date !== ev.start_date ? ` – ${ev.end_date}` : ''}</td>
                    <td>{ev.venue}</td>
                    <td>{ev.status_desc}</td>
                    <td>
                      <button className="btn btn-xs btn-primary"
                        onClick={() => handleSelectEspnEvent(ev)}>Select</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Step 2: pool details */}
          <h5 style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: 6, marginTop: 24, marginBottom: 12 }}>
            Step 2 — Pool Details
          </h5>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {[
                { label: 'ESPN Event ID', field: 'espn_event_id', type: 'text', placeholder: 'auto-filled from selection' },
                { label: 'Tournament Name', field: 'event_name', type: 'text', placeholder: 'e.g. The Masters' },
                { label: 'Course / Venue', field: 'course', type: 'text', placeholder: 'e.g. Augusta National Golf Club' },
                { label: 'Start Date', field: 'event_date', type: 'date', placeholder: '' },
                { label: 'Pool Name', field: 'pool_name', type: 'text', placeholder: 'e.g. Masters 2026 — Group A' },
                { label: 'Entry Fee', field: 'fee', type: 'text', placeholder: 'e.g. $50' },
              ].map(({ label, field, type, placeholder }) => (
                <tr key={field}>
                  <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle', whiteSpace: 'nowrap' }}>
                    {label}
                  </td>
                  <td style={{ padding: '4px 0' }}>
                    <input className="form-control" type={type} placeholder={placeholder}
                      value={form[field]}
                      onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))} />
                  </td>
                </tr>
              ))}
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  Pool Format
                </td>
                <td style={{ padding: '4px 0' }}>
                  <select className="form-control" value={form.pool_format}
                    onChange={e => setForm(f => ({ ...f, pool_format: e.target.value }))}>
                    <option value="draft">Draft — snake order, each golfer unique to one user</option>
                    <option value="async">Async — users pick freely, duplicate golfers allowed</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  Picks per User
                </td>
                <td style={{ padding: '4px 0' }}>
                  <input className="form-control" type="number" min="1" max="10"
                    style={{ width: 80 }}
                    value={form.picks_per_user}
                    onChange={e => setForm(f => ({ ...f, picks_per_user: e.target.value }))} />
                </td>
              </tr>
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  Scoring Players
                </td>
                <td style={{ padding: '4px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input className="form-control" type="number" min="1"
                      style={{ width: 80 }}
                      placeholder="all"
                      value={form.scoring_players}
                      onChange={e => setForm(f => ({ ...f, scoring_players: e.target.value }))} />
                    <span className="text-muted" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                      of {form.picks_per_user} picks count toward score (leave blank = all count)
                    </span>
                  </div>
                </td>
              </tr>
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  Tiebreaker Type
                </td>
                <td style={{ padding: '4px 0' }}>
                  <select className="form-control" value={form.tiebreaker_type}
                    onChange={e => setForm(f => ({ ...f, tiebreaker_type: e.target.value }))}>
                    <option value="player">Individual player score</option>
                    <option value="winning_score">Tournament winning score prediction</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  DNF Handling
                </td>
                <td style={{ padding: '4px 0' }}>
                  <select className="form-control" value={form.dnf_handling}
                    onChange={e => setForm(f => ({ ...f, dnf_handling: e.target.value }))}>
                    <option value="eliminate">Eliminate — participant is out if any pick misses cut/withdraws</option>
                    <option value="worst_score">Penalty score — DNF picks receive worst active score + N strokes</option>
                  </select>
                  {form.dnf_handling === 'worst_score' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                      <label style={{ margin: 0, fontWeight: 400 }}>Strokes added to worst:</label>
                      <input className="form-control input-sm" type="number" min="0"
                        style={{ width: 70 }}
                        value={form.dnf_penalty}
                        onChange={e => setForm(f => ({ ...f, dnf_penalty: e.target.value }))} />
                      <span className="text-muted" style={{ fontSize: 12 }}>
                        (0 = equal to worst, 1 = worst + 1, etc.)
                      </span>
                    </div>
                  )}
                </td>
              </tr>
              <tr>
                <td style={{ width: 180, padding: '6px 12px 6px 0', fontWeight: 600, verticalAlign: 'middle' }}>
                  Entries per User
                </td>
                <td style={{ padding: '4px 0' }}>
                  {form.pool_format === 'async' ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input className="form-control" type="number" min="1" max="10"
                        style={{ width: 80 }}
                        value={form.max_entries_per_user}
                        onChange={e => setForm(f => ({ ...f, max_entries_per_user: e.target.value }))} />
                      <span className="text-muted" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                        max entries per user (1 = one entry, the default)
                      </span>
                    </div>
                  ) : (
                    <span className="text-muted" style={{ fontSize: 12 }}>1 (draft pools allow one entry per user)</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>

          <button className="btn btn-success" style={{ marginTop: 16 }} onClick={handleCreatePool}
            disabled={isPoolAdmin && golfGrant && golfGrant.pools_used >= golfGrant.pools_allowed}>
            Create Pool
          </button>
        </div>
      </div>

      {/* Pool List */}
      {pools.length > 0 && (
        <div className="panel panel-default">
          <div className="panel-heading"><strong>All Pools</strong></div>
          <table className="table table-condensed table-bordered">
            <thead>
              <tr><th>ID</th><th>Pool Name</th><th>Event</th><th>Format</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {pools.map(p => (
                <tr key={p.pool_id}
                  style={selectedPoolId === p.pool_id ? { background: '#dff0d8' } : {}}>
                  <td>{p.pool_id}</td>
                  <td>{p.name}</td>
                  <td>{p.event_name}</td>
                  <td>{p.pool_format}</td>
                  <td><span className="label label-default">{p.status}</span></td>
                  <td>
                    <button className="btn btn-xs btn-primary"
                      onClick={() => setSelectedPoolId(p.pool_id)}>Manage</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pool Management */}
      {pool && (
        <div className="panel panel-primary">
          <div className="panel-heading">
            <strong>Managing: {pool.name}</strong>
            <span className="label label-default" style={{ marginLeft: 10 }}>{pool.status}</span>
            <span style={{ marginLeft: 10, fontSize: 12 }}>
              {pool.pool_format} · {pool.picks_per_user} picks/user · fee: {poolDetail.pool.fee || 'none'} · TB: {pool.tiebreaker_type === 'winning_score' ? 'winning score' : 'player score'}
            </span>
            {pool.invite_code && (
              <span style={{ marginLeft: 16, fontSize: 13 }}>
                Invite code: <strong style={{ letterSpacing: 2 }}>{pool.invite_code}</strong>
              </span>
            )}
          </div>
          <div className="panel-body">
            <div className="row">

              {/* Status */}
              <div className="col-md-3">
                <h4>Status</h4>
                {STATUS_FLOW.map(s => (
                  <button key={s}
                    className={`btn btn-sm btn-block ${pool.status === s ? 'btn-success' : 'btn-default'}`}
                    style={{ marginBottom: 4 }}
                    onClick={() => handleSetStatus(s)}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>

              {/* Admin Pick Override */}
              {pool.status !== 'complete' && (poolDetail?.participants || []).length > 0 && (
                <div className="col-md-5">
                  <h4>Admin Pick Override</h4>
                  <div className="form-group">
                    <label>User</label>
                    <select className="form-control input-sm"
                      value={adminPick.user_id}
                      onChange={e => setAdminPick(p => ({ ...p, user_id: e.target.value }))}>
                      <option value="">— select user —</option>
                      {(() => {
                        const participants = poolDetail?.participants || []
                        const multiEntry = new Set(
                          participants.filter(p => participants.filter(q => q.user_id === p.user_id).length > 1).map(p => p.user_id)
                        )
                        return participants.map(p => (
                          <option key={`${p.user_id}|${p.entry_number}`} value={`${p.user_id}|${p.entry_number}`}>
                            {p.username}{multiEntry.has(p.user_id) ? ` (Entry ${p.entry_number})` : ''}
                          </option>
                        ))
                      })()}
                    </select>
                  </div>
                  {espnField.length > 0 ? (
                    <div className="form-group">
                      <label>Player</label>
                      <select className="form-control input-sm"
                        value={adminPick.espn_id}
                        onChange={e => {
                          const player = espnField.find(p => p.espn_id === e.target.value)
                          setAdminPick(p => ({
                            ...p,
                            espn_id: e.target.value,
                            name: player?.name || '',
                          }))
                        }}>
                        <option value="">— select player —</option>
                        {espnField.map(p => (
                          <option key={p.espn_id} value={p.espn_id}>{p.name}</option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <>
                      <div className="form-group">
                        <label>Player ESPN ID</label>
                        <input className="form-control input-sm" placeholder="e.g. 388"
                          value={adminPick.espn_id}
                          onChange={e => setAdminPick(p => ({ ...p, espn_id: e.target.value }))} />
                      </div>
                      <div className="form-group">
                        <label>Player Name</label>
                        <input className="form-control input-sm" placeholder="e.g. Scottie Scheffler"
                          value={adminPick.name}
                          onChange={e => setAdminPick(p => ({ ...p, name: e.target.value }))} />
                      </div>
                    </>
                  )}
                  <button className="btn btn-warning btn-sm" onClick={handleAdminPick}>
                    Set Pick
                  </button>
                </div>
              )}

              {/* Admin Tiebreaker Override */}
              {pool.status !== 'complete' && (poolDetail?.participants || []).length > 0 && (
                <div className="col-md-4">
                  <h4>Set Tiebreaker</h4>
                  <div className="form-group">
                    <label>User</label>
                    <select className="form-control input-sm"
                      value={adminTbUser}
                      onChange={e => { setAdminTbUser(e.target.value); setAdminTbWinScore('') }}>
                      <option value="">— select user —</option>
                      {(() => {
                        const participants = poolDetail?.participants || []
                        const multiEntry = new Set(
                          participants.filter(p => participants.filter(q => q.user_id === p.user_id).length > 1).map(p => p.user_id)
                        )
                        return participants.map(p => (
                          <option key={`${p.user_id}|${p.entry_number}`} value={`${p.user_id}|${p.entry_number}`}>
                            {p.username}{multiEntry.has(p.user_id) ? ` (Entry ${p.entry_number})` : ''}
                          </option>
                        ))
                      })()}
                    </select>
                  </div>
                  {adminTbUser && pool.tiebreaker_type === 'player' && (() => {
                    const [tbUserId, tbEntryNum] = adminTbUser.split('|')
                    const userPicks = (poolDetail?.picks || [])
                      .filter(p => p.user_id === parseInt(tbUserId) && p.entry_number === parseInt(tbEntryNum))
                      .sort((a, b) => a.draft_position - b.draft_position)
                    if (!userPicks.length) return <p className="text-muted" style={{ fontSize: 12 }}>No picks yet.</p>
                    return userPicks.map(pick => (
                      <div key={pick.pick_id} style={{ marginBottom: 4 }}>
                        <button
                          className={`btn btn-sm ${pick.is_tiebreaker ? 'btn-info' : 'btn-default'}`}
                          onClick={() => handleAdminSetTiebreaker(pick.pick_id)}>
                          {pick.player_name}{pick.is_tiebreaker ? ' ★' : ''}
                        </button>
                      </div>
                    ))
                  })()}
                  {adminTbUser && pool.tiebreaker_type === 'winning_score' && (() => {
                    const [tbUserId, tbEntryNum] = adminTbUser.split('|')
                    const participant = (poolDetail?.participants || []).find(p => p.user_id === parseInt(tbUserId) && p.entry_number === parseInt(tbEntryNum))
                    const current = participant?.tiebreaker_prediction
                    return (
                      <div>
                        {current !== null && current !== undefined && (
                          <p className="text-muted" style={{ fontSize: 12, marginBottom: 6 }}>
                            Current: {current >= 0 ? `+${current}` : current}
                          </p>
                        )}
                        <div className="input-group input-group-sm">
                          <input type="number" className="form-control" placeholder="Score vs par (e.g. -12)"
                            value={adminTbWinScore}
                            onChange={e => setAdminTbWinScore(e.target.value)} />
                          <span className="input-group-btn">
                            <button className="btn btn-info" onClick={handleAdminSetWinningScoreTb}>Set</button>
                          </span>
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>

            {/* Participants */}
            <div style={{ marginTop: 20 }}>
              <h4>
                {pool.pool_format === 'draft' ? 'Draft Order' : 'Participants'}
                {pool.pool_format === 'draft' && (
                  <button className="btn btn-xs btn-warning" style={{ marginLeft: 8 }}
                    onClick={handleRandomize}>Randomize</button>
                )}
              </h4>
              <p className="text-muted" style={{ fontSize: 12 }}>
                {pool.pool_format === 'draft'
                  ? 'Enter each user\'s pick number (1, 2, 3…). Leave blank to exclude. Click a row to highlight.'
                  : 'Check each user participating in this pool. Click a row to toggle.'
                }
              </p>
              {previousUserIds.size > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <button
                    className={`btn btn-xs ${!showAllUsers ? 'btn-primary' : 'btn-default'}`}
                    onClick={() => { setShowAllUsers(false); setUserFilter('') }}>
                    Past participants ({previousUserIds.size})
                  </button>
                  <button
                    className={`btn btn-xs ${showAllUsers ? 'btn-primary' : 'btn-default'}`}
                    style={{ marginLeft: 4 }}
                    onClick={() => { setShowAllUsers(true); setUserFilter('') }}>
                    All users ({users.length})
                  </button>
                </div>
              )}
              <div style={{ marginBottom: 8 }}>
                {[10, 25, 50, null, 0].map(n => (
                  <button key={String(n)}
                    className={`btn btn-xs ${userLimit === n ? 'btn-info' : 'btn-default'}`}
                    style={{ marginRight: 4 }}
                    onClick={() => setUserLimit(n)}>
                    {n === null ? 'All' : n === 0 ? 'None' : n}
                  </button>
                ))}
              </div>
              {userLimit !== 0 && (
                <input
                  className="form-control input-sm"
                  style={{ maxWidth: 300, marginBottom: 8 }}
                  placeholder="Filter by name or email…"
                  value={userFilter}
                  onChange={e => setUserFilter(e.target.value)}
                />
              )}
              {userLimit !== 0 && (() => {
                const scopedUsers = showAllUsers ? users : users.filter(u => previousUserIds.has(u.userid))
                const q = userFilter.toLowerCase()
                const cols = ['username', 'first_name', 'last_name', 'email']
                const filtered = q
                  ? scopedUsers.filter(u => cols.some(c => (u[c] || '').toLowerCase().includes(q)))
                  : scopedUsers
                const limited = userLimit === null ? filtered : filtered.slice(0, userLimit)
                const sorted = [...limited].sort((a, b) => {
                  const av = (a[userSort.col] || '').toLowerCase()
                  const bv = (b[userSort.col] || '').toLowerCase()
                  return userSort.dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
                })
                const sortIcon = (col) => {
                  if (userSort.col !== col) return ' ↕'
                  return userSort.dir === 'asc' ? ' ↑' : ' ↓'
                }
                const handleSortClick = (col) => {
                  setUserSort(s => s.col === col
                    ? { col, dir: s.dir === 'asc' ? 'desc' : 'asc' }
                    : { col, dir: 'asc' }
                  )
                }
                const thStyle = { cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }
                return (
                  <div style={{ overflowX: 'auto' }}>
                    <table className="table table-condensed table-bordered table-hover" style={{ marginBottom: 8 }}>
                      <thead>
                        <tr>
                          <th style={{ width: 80, textAlign: 'center' }}>
                            {pool.pool_format === 'draft' ? 'Pick #' : 'In Pool'}
                          </th>
                          {[['username','Username'],['first_name','First'],['last_name','Last'],['email','Email']].map(([col, label]) => (
                            <th key={col} style={thStyle} onClick={() => handleSortClick(col)}>
                              {label}{sortIcon(col)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sorted.map(u => {
                          const uid = String(u.userid)
                          if (pool.pool_format === 'async') {
                            const checked = draftSlots.some(s => s === uid)
                            const toggle = () => {
                              if (checked) {
                                setDraftSlots(draftSlots.map(s => s === uid ? '' : s))
                              } else {
                                const updated = [...draftSlots]
                                const idx = updated.findIndex(s => !s)
                                if (idx >= 0) updated[idx] = uid
                                else updated.push(uid)
                                setDraftSlots(updated)
                              }
                            }
                            return (
                              <tr key={uid} style={{ cursor: 'pointer', ...(checked ? { background: '#dff0d8' } : {}) }}
                                onClick={toggle}>
                                <td style={{ textAlign: 'center' }} onClick={e => e.stopPropagation()}>
                                  <input type="checkbox" checked={checked} onChange={toggle} />
                                </td>
                                <td>{u.username}</td>
                                <td>{u.first_name}</td>
                                <td>{u.last_name}</td>
                                <td>{u.email}</td>
                              </tr>
                            )
                          } else {
                            const slotIdx = draftSlots.findIndex(s => s === uid)
                            const pickNum = slotIdx >= 0 ? slotIdx + 1 : ''
                            return (
                              <tr key={uid} style={pickNum ? { background: '#dff0d8' } : {}}>
                                <td style={{ textAlign: 'center' }}>
                                  <input
                                    type="number" min="1" max="20"
                                    className="form-control input-sm"
                                    style={{ width: 60, margin: '0 auto' }}
                                    value={pickNum}
                                    onChange={e => {
                                      const n = parseInt(e.target.value)
                                      const updated = [...draftSlots]
                                      const ex = updated.findIndex(s => s === uid)
                                      if (ex >= 0) updated[ex] = ''
                                      if (!isNaN(n) && n >= 1 && n <= 20) updated[n - 1] = uid
                                      setDraftSlots(updated)
                                    }}
                                  />
                                </td>
                                <td>{u.username}</td>
                                <td>{u.first_name}</td>
                                <td>{u.last_name}</td>
                                <td>{u.email}</td>
                              </tr>
                            )
                          }
                        })}
                      </tbody>
                    </table>
                  </div>
                )
              })()}

              <button className="btn btn-primary btn-sm" onClick={handleSaveDraftOrder}>
                Save {pool.pool_format === 'draft' ? 'Draft Order' : 'Participants'}
              </button>
            </div>

            {/* Draft Board / Payments */}
            {(poolDetail?.participants || []).length > 0 && (
              <div style={{ marginTop: 20 }}>
                <h4>Draft Board</h4>
                <table className="table table-condensed table-bordered table-striped">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>User</th>
                      {Array.from({ length: pool.picks_per_user }, (_, i) => (
                        <th key={i}>Pick {i + 1}</th>
                      ))}
                      {pool.tiebreaker_type === 'winning_score' && <th>TB Prediction</th>}
                      <th>Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(poolDetail?.participants || []).map(participant => {
                      const userPicks = (poolDetail?.picks || [])
                        .filter(p => p.user_id === participant.user_id && p.entry_number === participant.entry_number)
                        .sort((a, b) => a.draft_position - b.draft_position)
                      const pred = participant.tiebreaker_prediction
                      const fmtPred = pred === null || pred === undefined ? null
                        : pred === 0 ? 'E' : pred > 0 ? `+${pred}` : String(pred)
                      return (
                        <tr key={`${participant.user_id}-${participant.entry_number}`}>
                          <td>{participant.pick_order}</td>
                          <td><strong>{participant.username}</strong></td>
                          {Array.from({ length: pool.picks_per_user }, (_, i) => (
                            <td key={i}>{userPicks[i]?.player_name || '—'}</td>
                          ))}
                          {pool.tiebreaker_type === 'winning_score' && (
                            <td style={{ whiteSpace: 'nowrap' }}>
                              {fmtPred
                                ? <span style={{ color: pred < 0 ? '#15803d' : pred > 0 ? '#dc2626' : '#374151', fontWeight: 'bold' }}>{fmtPred}</span>
                                : <span className="label label-warning">Not set</span>
                              }
                            </td>
                          )}
                          <td>
                            <button
                              className={`btn btn-xs ${participant.paid ? 'btn-success' : 'btn-default'}`}
                              onClick={() => handleSetPaid(participant.user_id, participant.entry_number || 1, !participant.paid)}>
                              {participant.paid ? '$' : 'Unpaid'}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── Deputies ─────────────────────────────────────────────────── */}
            {poolDetail?.can_manage_deputies && (
              <div style={{ marginTop: 20 }}>
                <h4>Pool Deputies</h4>
                <p className="text-muted" style={{ fontSize: 12, marginTop: -6 }}>
                  Deputies can manage this pool but cannot add or remove other deputies.
                </p>
                {(poolDetail?.deputies || []).length === 0 ? (
                  <p className="text-muted" style={{ fontSize: 13 }}>No deputies assigned.</p>
                ) : (
                  <ul style={{ paddingLeft: 0, listStyle: 'none', marginBottom: 8 }}>
                    {(poolDetail?.deputies || []).map(d => (
                      <li key={d.user_id} style={{ marginBottom: 4 }}>
                        <strong>{d.username}</strong>{' '}
                        <button className="btn btn-xs btn-danger"
                          onClick={() => handleRemoveDeputy(d.user_id)}>Remove</button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="input-group input-group-sm" style={{ maxWidth: 320 }}>
                  <select className="form-control" value={deputyPickUserId}
                    onChange={e => setDeputyPickUserId(e.target.value)}>
                    <option value="">— select user to deputize —</option>
                    {users
                      .filter(u => !(poolDetail?.deputies || []).some(d => d.user_id === u.userid))
                      .map(u => (
                        <option key={u.userid} value={u.userid}>{u.username}</option>
                      ))}
                  </select>
                  <span className="input-group-btn">
                    <button className="btn btn-info" onClick={handleAddDeputy}
                      disabled={!deputyPickUserId}>Add</button>
                  </span>
                </div>
              </div>
            )}

            {/* ── Tier Configuration (async pools only) ───────────────────── */}
            {pool.pool_format === 'async' && (
              <div style={{ marginTop: 28 }}>
                <h4>
                  Tier Configuration
                  <button className="btn btn-xs btn-success" style={{ marginLeft: 10 }}
                    onClick={() => { setTierForm({ ...EMPTY_TIER_FORM }); setExpandedManualTier(null) }}>
                    + Add Tier
                  </button>
                </h4>
                <p className="text-muted" style={{ fontSize: 12, marginTop: -6 }}>
                  Tiers restrict how many picks a user can make from each group.
                  Players not in any tier are freely pickable with no constraint.
                </p>

                {/* Tier form */}
                {tierForm && (
                  <div style={{ background: '#f9f9f9', border: '1px solid #ddd', borderRadius: 4, padding: 14, marginBottom: 14, maxWidth: 340 }}>
                    <h5 style={{ marginTop: 0 }}>{tierForm.tier_id ? 'Edit Tier' : 'New Tier'}</h5>

                    <div className="form-group form-group-sm">
                      <label>Name</label>
                      <input className="form-control" placeholder="e.g. Top 10"
                        value={tierForm.name}
                        onChange={e => setTierForm(f => ({ ...f, name: e.target.value }))} />
                    </div>

                    <div className="form-group form-group-sm">
                      <label>Type</label>
                      <select className="form-control" value={tierForm.tier_type}
                        onChange={e => setTierForm(f => ({ ...f, tier_type: e.target.value }))}>
                        <option value="ranking">World Ranking</option>
                        <option value="manual">Manual</option>
                      </select>
                    </div>

                    {tierForm.tier_type === 'ranking' && (
                      <div className="form-group form-group-sm">
                        <label>Rank Range</label>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          <input className="form-control" type="number" min="1" placeholder="Min"
                            style={{ minWidth: 0 }}
                            value={tierForm.rank_min}
                            onChange={e => setTierForm(f => ({ ...f, rank_min: e.target.value }))} />
                          <span className="text-muted" style={{ flexShrink: 0 }}>–</span>
                          <input className="form-control" type="number" min="1" placeholder="Max (blank = ∞)"
                            style={{ minWidth: 0 }}
                            value={tierForm.rank_max}
                            onChange={e => setTierForm(f => ({ ...f, rank_max: e.target.value }))} />
                        </div>
                      </div>
                    )}

                    <div className="form-group form-group-sm">
                      <label>Players Required</label>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <input className="form-control" type="number" min="0" placeholder="Min (0)"
                          style={{ minWidth: 0 }}
                          value={tierForm.min_picks}
                          onChange={e => setTierForm(f => ({ ...f, min_picks: e.target.value }))} />
                        <span className="text-muted" style={{ flexShrink: 0 }}>–</span>
                        <input className="form-control" type="number" min="1" placeholder="Max (blank = ∞)"
                          style={{ minWidth: 0 }}
                          value={tierForm.max_picks}
                          onChange={e => setTierForm(f => ({ ...f, max_picks: e.target.value }))} />
                      </div>
                    </div>

                    <button className="btn btn-sm btn-success" onClick={handleSaveTier}>Save</button>
                    <button className="btn btn-sm btn-default" style={{ marginLeft: 6 }}
                      onClick={() => setTierForm(null)}>Cancel</button>
                  </div>
                )}

                {/* Tier list */}
                {(poolDetail?.tiers || []).length === 0 && !tierForm && (
                  <p className="text-muted" style={{ fontSize: 12 }}>No tiers defined — pool behaves as unrestricted async.</p>
                )}
                {(poolDetail?.tiers || []).map(tier => (
                  <div key={tier.tier_id} style={{ border: '1px solid #e5e7eb', borderRadius: 4, marginBottom: 8, overflow: 'hidden' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: '#f8f9fa' }}>
                      <strong style={{ flex: 1 }}>{tier.name}</strong>
                      <span className={`label label-${tier.tier_type === 'ranking' ? 'info' : 'default'}`}>
                        {tier.tier_type === 'ranking'
                          ? `Rank ${tier.rank_min ?? '?'}–${tier.rank_max ?? '∞'}`
                          : `Manual (${(poolDetail?.tier_players?.[String(tier.tier_id)] || []).length} players)`
                        }
                      </span>
                      <span className="text-muted" style={{ fontSize: 12 }}>
                        min {tier.min_picks} · max {tier.max_picks ?? '∞'}
                      </span>
                      {tier.tier_type === 'manual' && (
                        <button className="btn btn-xs btn-default"
                          onClick={() => expandedManualTier === tier.tier_id ? setExpandedManualTier(null) : openManualAssign(tier.tier_id)}>
                          {expandedManualTier === tier.tier_id ? 'Close' : 'Assign Players'}
                        </button>
                      )}
                      <button className="btn btn-xs btn-warning"
                        onClick={() => { setTierForm({ tier_id: tier.tier_id, name: tier.name, tier_type: tier.tier_type, rank_min: tier.rank_min ?? '', rank_max: tier.rank_max ?? '', min_picks: tier.min_picks, max_picks: tier.max_picks ?? '' }) }}>
                        Edit
                      </button>
                      <button className="btn btn-xs btn-danger"
                        onClick={() => handleDeleteTier(tier.tier_id)}>
                        ✕
                      </button>
                    </div>

                    {/* Manual player assignment panel */}
                    {expandedManualTier === tier.tier_id && (() => {
                      const field = poolDetail?.espn_field || []
                      if (field.length === 0) {
                        return (
                          <div style={{ padding: '10px 12px', fontSize: 13, color: '#666' }}>
                            Tournament field not available — set pool to Open first.
                          </div>
                        )
                      }
                      const filteredField = field.filter(p =>
                        !tierPlayerFilter || p.name.toLowerCase().includes(tierPlayerFilter.toLowerCase())
                      )
                      return (
                        <div style={{ padding: '10px 12px' }}>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                            <input className="form-control input-sm" style={{ maxWidth: 200 }}
                              placeholder="Filter players…"
                              value={tierPlayerFilter}
                              onChange={e => setTierPlayerFilter(e.target.value)} />
                            <span className="text-muted" style={{ fontSize: 12 }}>
                              {manualSelections.size} selected
                            </span>
                            <button className="btn btn-sm btn-success" onClick={handleSaveTierPlayers}>
                              Save Selections
                            </button>
                          </div>
                          <div style={{ maxHeight: 260, overflowY: 'auto', columns: 3, columnGap: 12 }}>
                            {filteredField.map(p => (
                              <label key={p.espn_id} style={{ display: 'block', fontWeight: 'normal', fontSize: 13, cursor: 'pointer', marginBottom: 2, breakInside: 'avoid' }}>
                                <input type="checkbox"
                                  checked={manualSelections.has(String(p.espn_id))}
                                  onChange={() => toggleManualPlayer(p.espn_id)}
                                  style={{ marginRight: 5 }} />
                                {p.name}
                                {p.world_rank ? <span className="text-muted" style={{ fontSize: 11 }}> #{p.world_rank}</span> : ''}
                              </label>
                            ))}
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  )
}
