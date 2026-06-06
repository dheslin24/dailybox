import { useCallback, useEffect, useRef, useState } from 'react'
import Layout from '../components/Layout'
import { useSession } from '../SessionContext'

function UserAutocomplete({ users, value, onChange, onSelect, placeholder }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const matches = value.trim().length > 0
    ? users.filter(u => u.username.toLowerCase().includes(value.toLowerCase())).slice(0, 8)
    : []

  useEffect(() => {
    const close = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative', flex: 1 }}>
      <input
        className="form-control input-sm"
        placeholder={placeholder || 'Search username'}
        value={value}
        onChange={e => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        autoComplete="off"
      />
      {open && matches.length > 0 && (
        <ul style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 1000,
          background: '#fff', border: '1px solid #d1d5db', borderRadius: 4,
          margin: 0, padding: 0, listStyle: 'none',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)', maxHeight: 200, overflowY: 'auto',
        }}>
          {matches.map(u => (
            <li
              key={u.userid}
              onMouseDown={() => { onSelect(u.username); setOpen(false) }}
              style={{ padding: '6px 10px', cursor: 'pointer', fontSize: 13 }}
              onMouseEnter={e => e.currentTarget.style.background = '#f3f4f6'}
              onMouseLeave={e => e.currentTarget.style.background = '#fff'}
            >
              {u.username}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const DEFAULT_PTS = { pts_group: 1, pts_r32: 2, pts_r16: 3, pts_qf: 4, pts_sf: 5, pts_3rd: 3, pts_final: 6 }
const PTS_LABELS = [
  ['pts_group', 'Group Stage'],
  ['pts_r32', 'Round of 32'],
  ['pts_r16', 'Round of 16'],
  ['pts_qf', 'Quarterfinals'],
  ['pts_sf', 'Semifinals'],
  ['pts_3rd', 'Third Place'],
  ['pts_final', 'Final'],
]

export default function SoccerAdmin() {
  const session = useSession()
  const isSuperAdmin = session?.is_admin === 1

  const [pools, setPools] = useState([])
  const [users, setUsers] = useState([])
  const [selectedPoolId, setSelectedPoolId] = useState(null)
  const [poolDetail, setPoolDetail] = useState(null)
  const [msg, setMsg] = useState('')

  // Create pool form
  const [createForm, setCreateForm] = useState({ name: '', fee: '', pick_format: 'standard', pts_group_draw: 0, ...DEFAULT_PTS })
  const [createdCode, setCreatedCode] = useState(null)

  // Add user
  const [addUsername, setAddUsername] = useState('')
  const [addDeputyUsername, setAddDeputyUsername] = useState('')

  // Grants (super admin)
  const [grants, setGrants] = useState([])
  const [grantForm, setGrantForm] = useState({ username: '', pools_allowed: 1 })

  // Seed/refresh state
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState(null)

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(''), 5000) }

  const loadPools = () =>
    fetch('/api/soccer_admin_pools').then(r => r.json()).then(d => {
      if (Array.isArray(d)) setPools(d)
    })

  const loadUsers = () =>
    fetch('/api/soccer_users').then(r => r.json()).then(d => {
      if (Array.isArray(d)) setUsers(d)
    })

  const loadDetail = useCallback(() => {
    if (!selectedPoolId) { setPoolDetail(null); return }
    fetch(`/api/soccer_pool?pool_id=${selectedPoolId}`)
      .then(r => r.json())
      .then(d => { if (!d.error) setPoolDetail(d) })
  }, [selectedPoolId])

  const loadGrants = () => {
    if (!isSuperAdmin) return
    fetch('/api/soccer_pool_grants').then(r => r.json()).then(d => {
      if (Array.isArray(d)) setGrants(d)
    })
  }

  useEffect(() => { loadPools(); loadGrants(); loadUsers() }, [])
  useEffect(() => { loadDetail() }, [loadDetail])

  const handleCreate = () => {
    if (!createForm.name.trim()) { flash('Pool name required'); return }
    fetch('/api/soccer_create_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(createForm),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setCreatedCode(d.invite_code)
        setCreateForm({ name: '', fee: '', pick_format: 'standard', pts_group_draw: 0, ...DEFAULT_PTS })
        loadPools()
        setSelectedPoolId(d.pool_id)
      })
  }

  const handleSeed = () => {
    setSeeding(true)
    setSeedResult(null)
    fetch('/api/soccer_seed_matches', { method: 'POST' })
      .then(r => r.json())
      .then(d => { setSeedResult(d); setSeeding(false); loadDetail() })
      .catch(() => { setSeedResult({ error: 'Request failed' }); setSeeding(false) })
  }

  const handleAddUser = () => {
    if (!addUsername.trim()) return
    fetch('/api/soccer_add_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, username: addUsername.trim() }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setAddUsername('')
        loadDetail()
      })
  }

  const handleRemoveUser = (userId) => {
    if (!window.confirm('Remove this user from the pool?')) return
    fetch('/api/soccer_remove_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: userId }),
    }).then(() => loadDetail())
  }

  const handleSetPaid = (userId, paid) => {
    fetch('/api/soccer_set_paid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: userId, paid }),
    }).then(() => loadDetail())
  }

  const handleAddDeputy = () => {
    if (!addDeputyUsername.trim()) return
    fetch('/api/soccer_add_deputy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, username: addDeputyUsername.trim() }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setAddDeputyUsername('')
        loadDetail()
      })
  }

  const handleRemoveDeputy = (userId) => {
    fetch('/api/soccer_remove_deputy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: userId }),
    }).then(() => loadDetail())
  }

  const handleGrantAdmin = () => {
    if (!grantForm.username.trim()) return
    fetch('/api/soccer_grant_pool_admin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(grantForm),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        setGrantForm({ username: '', pools_allowed: 1 })
        loadGrants()
      })
  }

  const pd = poolDetail
  const deputies = pd?.deputies || []
  const deputyIds = new Set(deputies.map(d => d.user_id))
  const nonDeputyMembers = (pd?.members || []).filter(m => !deputyIds.has(m.user_id))

  return (
    <Layout>
      <div style={{ maxWidth: 860, margin: '0 auto', padding: '20px 16px' }}>
        <h2 style={{ marginBottom: 20 }}>⚽ Soccer Pool Admin</h2>

        {msg && <div className="alert alert-info">{msg}</div>}

        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>

          {/* LEFT: Create pool + Seed matches */}
          <div style={{ flex: '0 0 280px', minWidth: 260 }}>

            {/* Create Pool */}
            <div className="panel panel-default">
              <div className="panel-heading"><strong>Create Pool</strong></div>
              <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <input
                  className="form-control"
                  placeholder="Pool name"
                  value={createForm.name}
                  onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                />
                <input
                  className="form-control"
                  placeholder="Fee (e.g. $20)"
                  value={createForm.fee}
                  onChange={e => setCreateForm(f => ({ ...f, fee: e.target.value }))}
                />
                <div style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', marginTop: 4 }}>Pick format</div>
                <select
                  className="form-control"
                  value={createForm.pick_format}
                  onChange={e => setCreateForm(f => ({ ...f, pick_format: e.target.value }))}
                >
                  <option value="standard">Standard (H / Draw / A)</option>
                  <option value="winner_only">Winner Only (H / A — draw gives consolation pts)</option>
                </select>
                {createForm.pick_format === 'winner_only' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#6b7280', flex: 1 }}>Draw consolation pts</span>
                    <input
                      type="number" min={0} max={99}
                      className="form-control"
                      style={{ width: 60, padding: '4px 6px' }}
                      value={createForm.pts_group_draw}
                      onChange={e => setCreateForm(f => ({ ...f, pts_group_draw: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                )}
                <div style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', marginTop: 4 }}>Points per round</div>
                {PTS_LABELS.map(([key, label]) => (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#6b7280', flex: 1 }}>{label}</span>
                    <input
                      type="number" min={0} max={99}
                      className="form-control"
                      style={{ width: 60, padding: '4px 6px' }}
                      value={createForm[key]}
                      onChange={e => setCreateForm(f => ({ ...f, [key]: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                ))}
                <button className="btn btn-primary btn-sm" style={{ marginTop: 4 }} onClick={handleCreate}>
                  Create Pool
                </button>
                {createdCode && (
                  <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 6, padding: 10, marginTop: 4 }}>
                    <div style={{ fontSize: 12, color: '#15803d' }}>Pool created!</div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>
                      Invite code: <span style={{ letterSpacing: 3, fontFamily: 'monospace' }}>{createdCode}</span>
                    </div>
                    <button className="btn btn-xs btn-default" style={{ marginTop: 4 }} onClick={() => setCreatedCode(null)}>Dismiss</button>
                  </div>
                )}
              </div>
            </div>

            {/* Seed Matches (super admin only) */}
            {isSuperAdmin && (
              <div className="panel panel-default" style={{ marginTop: 16 }}>
                <div className="panel-heading"><strong>Match Data (ESPN)</strong></div>
                <div className="panel-body">
                  <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
                    Seed pulls all WC 2026 matches from ESPN and stores them in the DB.
                    Run once before the tournament, then use Refresh to update scores.
                  </p>
                  <button className="btn btn-warning btn-sm" onClick={handleSeed} disabled={seeding}>
                    {seeding ? 'Seeding...' : '⬇ Seed Matches from ESPN'}
                  </button>
                  {seedResult && (
                    <div style={{ marginTop: 8, fontSize: 12 }}>
                      {seedResult.error
                        ? <span style={{ color: '#dc2626' }}>Error: {seedResult.error}</span>
                        : <span style={{ color: '#15803d' }}>
                            ✓ {seedResult.inserted} inserted, {seedResult.updated} updated ({seedResult.total} total)
                          </span>
                      }
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Grants (super admin only) */}
            {isSuperAdmin && (
              <div className="panel panel-default" style={{ marginTop: 16 }}>
                <div className="panel-heading"><strong>Pool Admin Grants</strong></div>
                <div className="panel-body">
                  <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                    <input
                      className="form-control input-sm"
                      placeholder="Username"
                      value={grantForm.username}
                      onChange={e => setGrantForm(f => ({ ...f, username: e.target.value }))}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="number" min={1} max={10}
                      className="form-control input-sm"
                      style={{ width: 52 }}
                      value={grantForm.pools_allowed}
                      onChange={e => setGrantForm(f => ({ ...f, pools_allowed: parseInt(e.target.value) || 1 }))}
                    />
                    <button className="btn btn-default btn-sm" onClick={handleGrantAdmin}>Grant</button>
                  </div>
                  {grants.length > 0 && (
                    <table className="table table-condensed" style={{ fontSize: 12, marginBottom: 0 }}>
                      <thead><tr><th>User</th><th>Used / Allowed</th></tr></thead>
                      <tbody>
                        {grants.map(g => (
                          <tr key={g.user_id}>
                            <td>{g.username}</td>
                            <td>{g.pools_used} / {g.pools_allowed}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* RIGHT: Manage selected pool */}
          <div style={{ flex: 1, minWidth: 280 }}>
            {/* Pool selector */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>Manage Pool</label>
              <select
                className="form-control"
                value={selectedPoolId || ''}
                onChange={e => setSelectedPoolId(e.target.value ? parseInt(e.target.value) : null)}
              >
                <option value="">— select a pool —</option>
                {pools.map(p => (
                  <option key={p.pool_id} value={p.pool_id}>{p.name} ({p.status})</option>
                ))}
              </select>
            </div>

            {pd && (
              <>
                {/* Pool info */}
                <div style={{ background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: 6, padding: '10px 14px', marginBottom: 16 }}>
                  <div style={{ fontWeight: 600 }}>{pd.pool.name}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                    Invite code: <strong style={{ letterSpacing: 2, fontFamily: 'monospace' }}>{pd.pool.invite_code}</strong>
                    <span style={{ marginLeft: 12 }}>Status: {pd.pool.status}</span>
                  </div>
                  {pd.pool.fee && <div style={{ fontSize: 12, color: '#6b7280' }}>Fee: {pd.pool.fee}</div>}
                  <a href={`/app/soccer_pool/${pd.pool.pool_id}`} style={{ fontSize: 12, marginTop: 4, display: 'inline-block' }}>
                    View pool →
                  </a>
                </div>

                {/* Members */}
                <div className="panel panel-default">
                  <div className="panel-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>Members ({pd.members.length})</strong>
                  </div>
                  <div className="panel-body">
                    <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                      <UserAutocomplete
                        users={users}
                        value={addUsername}
                        onChange={setAddUsername}
                        onSelect={name => { setAddUsername(name) }}
                        placeholder="Add by username"
                      />
                      <button className="btn btn-default btn-sm" onClick={handleAddUser}>Add</button>
                    </div>
                    {pd.members.length === 0 ? (
                      <div style={{ fontSize: 12, color: '#9ca3af' }}>No members yet.</div>
                    ) : (
                      <table className="table table-condensed" style={{ fontSize: 13, marginBottom: 0 }}>
                        <thead><tr><th>Username</th><th>Paid</th><th></th></tr></thead>
                        <tbody>
                          {pd.members.map(m => (
                            <tr key={m.user_id}>
                              <td>{m.username}</td>
                              <td>
                                <input
                                  type="checkbox"
                                  checked={!!m.paid}
                                  onChange={e => handleSetPaid(m.user_id, e.target.checked)}
                                />
                              </td>
                              <td>
                                <button
                                  className="btn btn-xs btn-danger"
                                  onClick={() => handleRemoveUser(m.user_id)}
                                >✕</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* Deputies */}
                <div className="panel panel-default" style={{ marginTop: 12 }}>
                  <div className="panel-heading"><strong>Deputies ({deputies.length})</strong></div>
                  <div className="panel-body">
                    <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                      <select
                        className="form-control input-sm"
                        style={{ flex: 1 }}
                        value={addDeputyUsername}
                        onChange={e => setAddDeputyUsername(e.target.value)}
                      >
                        <option value="">— add deputy —</option>
                        {nonDeputyMembers.map(m => (
                          <option key={m.user_id} value={m.username}>{m.username}</option>
                        ))}
                      </select>
                      <button className="btn btn-default btn-sm" onClick={handleAddDeputy}>Add</button>
                    </div>
                    {deputies.length === 0 ? (
                      <div style={{ fontSize: 12, color: '#9ca3af' }}>No deputies.</div>
                    ) : (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {deputies.map(d => (
                          <span key={d.user_id} style={{ background: '#e0e7ff', color: '#3730a3', borderRadius: 12, padding: '3px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                            {d.username}
                            <button
                              style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', padding: 0, fontSize: 12 }}
                              onClick={() => handleRemoveDeputy(d.user_id)}
                            >✕</button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
