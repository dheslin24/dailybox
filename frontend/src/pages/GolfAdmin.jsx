import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout'

const EMPTY_FORM = {
  espn_event_id: '', event_name: '', course: '', event_date: '',
  pool_name: '', fee: '', pool_format: 'draft', draft_type: 'manual', picks_per_user: 4,
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
  const [adminTbUser, setAdminTbUser] = useState('')
  const [msg, setMsg]                 = useState('')
  const [userFilter, setUserFilter]   = useState('')
  const [userSort, setUserSort]       = useState({ col: 'username', dir: 'asc' })

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(''), 4000) }

  const loadUsers = () =>
    fetch('/api/golf_users').then(r => r.json()).then(d => setUsers(d.users || []))

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
  }, [])

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
    fetch('/api/golf_admin_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool_id: selectedPoolId,
        user_id: parseInt(adminPick.user_id),
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
    fetch('/api/golf_admin_set_tiebreaker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id: parseInt(adminTbUser), pick_id }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flash(d.error); return }
        flash('Tiebreaker set')
        loadPoolDetail(selectedPoolId)
      })
  }

  const handleSetPaid = (user_id, paid) => {
    fetch('/api/golf_set_paid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, user_id, paid }),
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

      {/* Init DB */}
      <div className="row" style={{ marginBottom: 20 }}>
        <div className="col-md-12">
          <button className="btn btn-default btn-sm" onClick={handleInitDb}>
            Initialize DB Tables
          </button>
        </div>
      </div>

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
        <div className="panel-heading"><strong>Create New Pool</strong></div>
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
            </tbody>
          </table>

          <button className="btn btn-success" style={{ marginTop: 16 }} onClick={handleCreatePool}>
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
              {pool.pool_format} · {pool.picks_per_user} picks/user · fee: {poolDetail.pool.fee || 'none'}
            </span>
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
              {pool.status === 'open' && (
                <div className="col-md-5">
                  <h4>Admin Pick Override</h4>
                  <div className="form-group">
                    <label>User</label>
                    <select className="form-control input-sm"
                      value={adminPick.user_id}
                      onChange={e => setAdminPick(p => ({ ...p, user_id: e.target.value }))}>
                      <option value="">— select user —</option>
                      {(poolDetail?.participants || []).map(p => (
                        <option key={p.user_id} value={p.user_id}>{p.username}</option>
                      ))}
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
                      onChange={e => setAdminTbUser(e.target.value)}>
                      <option value="">— select user —</option>
                      {(poolDetail?.participants || []).map(p => (
                        <option key={p.user_id} value={p.user_id}>{p.username}</option>
                      ))}
                    </select>
                  </div>
                  {adminTbUser && (() => {
                    const userPicks = (poolDetail?.picks || [])
                      .filter(p => p.user_id === parseInt(adminTbUser))
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
              <input
                className="form-control input-sm"
                style={{ maxWidth: 300, marginBottom: 8 }}
                placeholder="Filter by name or email…"
                value={userFilter}
                onChange={e => setUserFilter(e.target.value)}
              />
              {(() => {
                const q = userFilter.toLowerCase()
                const cols = ['username', 'first_name', 'last_name', 'email']
                const filtered = q
                  ? users.filter(u => cols.some(c => (u[c] || '').toLowerCase().includes(q)))
                  : users
                const sorted = [...filtered].sort((a, b) => {
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
                      <th>Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(poolDetail?.participants || []).map(participant => {
                      const userPicks = (poolDetail?.picks || [])
                        .filter(p => p.user_id === participant.user_id)
                        .sort((a, b) => a.draft_position - b.draft_position)
                      return (
                        <tr key={participant.user_id}>
                          <td>{participant.pick_order}</td>
                          <td><strong>{participant.username}</strong></td>
                          {Array.from({ length: pool.picks_per_user }, (_, i) => (
                            <td key={i}>{userPicks[i]?.player_name || '—'}</td>
                          ))}
                          <td>
                            <button
                              className={`btn btn-xs ${participant.paid ? 'btn-success' : 'btn-default'}`}
                              onClick={() => handleSetPaid(participant.user_id, !participant.paid)}>
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
          </div>
        </div>
      )}
    </Layout>
  )
}
