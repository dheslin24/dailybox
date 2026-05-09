import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'

function ScoreBadge({ val, display }) {
  if (display === 'E' || val === 0) return <span style={{ color: '#374151' }}>E</span>
  if (val < 0) return <span style={{ color: '#15803d', fontWeight: 'bold' }}>{display}</span>
  return <span style={{ color: '#dc2626', fontWeight: 'bold' }}>{display}</span>
}

function RoundCells({ rounds, numRounds }) {
  return Array.from({ length: numRounds }, (_, i) => (
    <td key={i}>{rounds[String(i + 1)] || '—'}</td>
  ))
}

export default function GolfPool() {
  const [searchParams] = useSearchParams()
  const paramPoolId = searchParams.get('pool_id')

  const [pools, setPools]           = useState(null)
  const [selectedPoolId, setSelectedPoolId] = useState(paramPoolId ? parseInt(paramPoolId) : null)
  const [data, setData]             = useState(null)
  const [filter, setFilter]         = useState('')
  const [pickMsg, setPickMsg]       = useState('')
  const [tbMsg, setTbMsg]           = useState('')
  const [teeTimes, setTeeTimes]     = useState({})
  const [lbPickedOnly, setLbPickedOnly] = useState(false)
  const [joinCode, setJoinCode]         = useState('')
  const [joinMsg, setJoinMsg]           = useState('')

  const flashPick = (m) => { setPickMsg(m); setTimeout(() => setPickMsg(''), 4000) }
  const flashTb   = (m) => { setTbMsg(m);   setTimeout(() => setTbMsg(''), 4000) }

  const handleJoinPool = () => {
    if (!joinCode.trim()) return
    fetch('/api/golf_join_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invite_code: joinCode.trim() }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setJoinMsg(d.error); return }
        setJoinMsg(`Joined "${d.pool_name}"!`)
        setSelectedPoolId(d.pool_id)
        fetch('/api/golf_pools').then(r => r.json()).then(d2 => setPools(d2.pools || []))
      })
  }

  useEffect(() => {
    fetch('/api/golf_pools')
      .then(r => r.json())
      .then(d => {
        const list = d.pools || []
        setPools(list)
        if (!selectedPoolId && list.length === 1) setSelectedPoolId(list[0].pool_id)
      })
  }, [])

  const load = useCallback(() => {
    if (!selectedPoolId) return
    fetch(`/api/golf_pool?pool_id=${selectedPoolId}`)
      .then(r => r.json())
      .then(d => { if (!d.error) setData(d) })
  }, [selectedPoolId])

  useEffect(load, [load])

  useEffect(() => {
    if (!data) return
    const status = data.pool?.status
    if (status === 'complete') return
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load, data])

  // Fetch tee times separately (slow call) so the main page loads fast
  useEffect(() => {
    if (!selectedPoolId || !data) return
    const status = data.pool?.status
    if (status !== 'open' && status !== 'active') return
    const fetchTT = () => {
      fetch(`/api/golf_tee_times?pool_id=${selectedPoolId}`)
        .then(r => r.json())
        .then(d => { if (d.tee_times) setTeeTimes(d.tee_times) })
        .catch(() => {})
    }
    fetchTT()
    const id = setInterval(fetchTT, 60000)
    return () => clearInterval(id)
  }, [selectedPoolId, data?.pool?.status])

  const handlePick = (player) => {
    if (!data?.is_on_clock && data?.pool?.pool_format === 'draft') return
    fetch('/api/golf_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pool_id: selectedPoolId,
        player_espn_id: player.espn_id,
        player_name: player.name,
      }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flashPick(d.error); return }
        setFilter('')
        load()
      })
  }

  const handleRemovePick = (pick_id) => {
    fetch('/api/golf_remove_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, pick_id }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flashPick(d.error); return }
        load()
      })
  }

  const handleSetTiebreaker = (pick_id) => {
    fetch('/api/golf_set_tiebreaker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, pick_id }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flashTb(d.error); return }
        flashTb('Tiebreaker set')
        load()
      })
  }

  // ── Pool list selector ────────────────────────────────────────────────────
  if (!selectedPoolId) {
    return (
      <Layout>
        <h2>Golf Pools</h2>
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <img src="/static/homer_golf_sandwedge_3.gif" alt="" style={{ width: '50%' }} />
        </div>
        {pools === null && <p>Loading…</p>}
        {pools !== null && pools.length === 0 && (
          <div style={{ maxWidth: 400, margin: '0 auto' }}>
            <p>You are not in any golf pools yet. Enter an invite code to join one:</p>
            <div className="input-group">
              <input
                type="text"
                className="form-control"
                placeholder="Invite code"
                value={joinCode}
                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === 'Enter' && handleJoinPool()}
                maxLength={8}
                style={{ letterSpacing: 2, textTransform: 'uppercase' }}
              />
              <span className="input-group-btn">
                <button className="btn btn-primary" onClick={handleJoinPool}>Join</button>
              </span>
            </div>
            {joinMsg && <p style={{ marginTop: 8 }}>{joinMsg}</p>}
          </div>
        )}
        {pools && pools.length > 1 && (
          <div className="list-group" style={{ maxWidth: 600, margin: '0 auto' }}>
            {pools.map(p => (
              <button key={p.pool_id} className="list-group-item"
                onClick={() => setSelectedPoolId(p.pool_id)}>
                <strong>{p.name}</strong>
                <span className="text-muted" style={{ marginLeft: 8 }}>{p.event_name}</span>
                <span className="label label-default pull-right">{p.status}</span>
              </button>
            ))}
          </div>
        )}
      </Layout>
    )
  }

  if (!data) return <Layout><p>Loading…</p></Layout>

  const { pool, event, participants, picks, current_user_picks,
          snake_sequence, on_clock, is_on_clock, espn_field, standings, is_admin } = data

  const pickedIds      = new Set(picks.map(p => p.player_espn_id))
  const myPickedIds    = new Set(current_user_picks.map(p => p.player_espn_id))
  const canPick        = pool.status === 'open' &&
    current_user_picks.length < pool.picks_per_user &&
    (pool.pool_format === 'async' || is_on_clock)

  const filteredField  = espn_field.filter(p =>
    !filter || p.name.toLowerCase().includes(filter.toLowerCase())
  )

  // Max rounds across all players (for column headers)
  const maxRounds = espn_field.reduce((m, p) => Math.max(m, Object.keys(p.rounds || {}).length), 0)
    || standings.reduce((m, s) =>
        s.picks.reduce((mm, p) => Math.max(mm, Object.keys(p.rounds || {}).length), m), 0)

  return (
    <Layout>
      {/* Pool selector (if multiple) */}
      {pools && pools.length > 1 && (
        <div style={{ marginBottom: 12 }}>
          <select className="form-control" style={{ maxWidth: 400, display: 'inline-block' }}
            value={selectedPoolId}
            onChange={e => { setSelectedPoolId(parseInt(e.target.value)); setData(null) }}>
            {pools.map(p => (
              <option key={p.pool_id} value={p.pool_id}>{p.name} — {p.event_name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Header */}
      <h2 className="text-center">{pool.name}</h2>
      <h4 className="text-center">{event.name}</h4>
      {event.course && <p className="text-center text-muted">{event.course}</p>}
      <p className="text-center">
        {event.event_date && <span>{event.event_date}&nbsp;&nbsp;</span>}
        {event.espn_status && <span style={{ color: '#6b7280' }}>ESPN: {event.espn_status}</span>}
      </p>
      <p className="text-center">
        Entry Fee: <strong>{pool.fee || 'None'}</strong>
        &nbsp;&nbsp;Format: <strong>{pool.pool_format}</strong>
        &nbsp;&nbsp;Picks/user: <strong>{pool.picks_per_user}</strong>
      </p>

      {/* ── SETUP ──────────────────────────────────────────────────────────── */}
      {pool.status === 'setup' && (
        <div className="alert alert-info text-center">Draft has not opened yet. Check back soon.</div>
      )}

      {/* ── OPEN: on-clock banner (draft format) ───────────────────────────── */}
      {pool.status === 'open' && pool.pool_format === 'draft' && on_clock && (
        <div className="row">
          <div className="col-md-12">
            <div style={{
              padding: '12px 20px', borderRadius: 6, marginBottom: 16, textAlign: 'center',
              background: is_on_clock ? '#d1fae5' : '#fef9c3',
              border: `2px solid ${is_on_clock ? '#16a34a' : '#ca8a04'}`,
            }}>
              {is_on_clock ? (
                <strong style={{ color: '#15803d', fontSize: 18 }}>
                  It&apos;s your pick! (Round {on_clock.round}, Pick #{on_clock.pick_num})
                </strong>
              ) : (
                <span style={{ color: '#92400e', fontSize: 16 }}>
                  ⏰ On the clock: <strong>{on_clock.username}</strong>
                  &nbsp;— Round {on_clock.round}, Pick #{on_clock.pick_num}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── OPEN: async all-picked banner ─────────────────────────────────── */}
      {pool.status === 'open' && pool.pool_format === 'async' &&
        current_user_picks.length >= pool.picks_per_user && (
        <div className="alert alert-success text-center">
          You&apos;ve submitted all {pool.picks_per_user} picks. Waiting for the tournament to begin.
        </div>
      )}

      {/* ── OPEN: field picker ─────────────────────────────────────────────── */}
      {pool.status === 'open' && espn_field.length === 0 && (
        <div className="alert alert-info text-center">
          Tournament field is not yet available. Please check back closer to tournament start time.
        </div>
      )}

      {pool.status === 'open' && espn_field.length > 0 && (
        <div className="row" style={{ marginBottom: 20 }}>
          <div className="col-md-8">
            <h4>
              Tournament Field
              {canPick && <span style={{ color: '#15803d', marginLeft: 8, fontSize: 14 }}>
                — select a golfer to pick
              </span>}
            </h4>
            <input className="form-control" style={{ marginBottom: 8 }}
              placeholder="Filter by name…" value={filter}
              onChange={e => setFilter(e.target.value)} />
            {pickMsg && <div className="alert alert-danger">{pickMsg}</div>}
            <div style={{ maxHeight: 420, overflowY: 'auto', border: '1px solid #dee2e6', borderRadius: 4 }}>
              <table className="table table-condensed table-bordered" style={{ marginBottom: 0 }}>
                <thead>
                  <tr><th>Rank</th><th>Player</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {filteredField.map(player => {
                    const isMine  = myPickedIds.has(player.espn_id)
                    const isTaken = pickedIds.has(player.espn_id)
                    const isElim  = player.is_eliminated
                    let rowStyle  = {}
                    let label     = null
                    if (isMine)       { rowStyle = { background: '#dbeafe' }; label = <span className="label label-primary">Your pick</span> }
                    else if (isTaken && pool.pool_format === 'draft')
                                      { rowStyle = { background: '#f1f5f9', color: '#94a3b8' }; label = <span className="label label-default">Taken</span> }
                    else if (isElim)  { rowStyle = { color: '#94a3b8' }; label = <span className="label label-warning">CUT/WD</span> }
                    else if (canPick) { rowStyle = { cursor: 'pointer', background: '#f0fdf4' } }

                    return (
                      <tr key={player.espn_id} style={rowStyle}
                        onClick={() => {
                          if (!isMine && !isElim && canPick &&
                              !(isTaken && pool.pool_format === 'draft'))
                            handlePick(player)
                        }}>
                        <td>{player.world_rank ? `#${player.world_rank}` : '—'}</td>
                        <td>
                          {player.name}
                          {label && <span style={{ marginLeft: 6 }}>{label}</span>}
                        </td>
                        <td>
                          {isTaken && !isMine && pool.pool_format === 'draft'
                            ? picks.find(p => p.player_espn_id === player.espn_id)?.username || '—'
                            : ''}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* My current picks while drafting */}
          <div className="col-md-4">
            <h4>My Picks ({current_user_picks.length} / {pool.picks_per_user})</h4>
            {current_user_picks.length === 0
              ? <p className="text-muted">None yet.</p>
              : current_user_picks.map((p, i) => (
                <div key={p.pick_id} style={{
                  padding: '8px 12px', marginBottom: 6, borderRadius: 4,
                  background: '#dbeafe', border: '1px solid #93c5fd',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <span>
                    <strong>{i + 1}. {p.player_name}</strong>
                    {p.is_tiebreaker && <span className="label label-info" style={{ marginLeft: 6 }}>TB</span>}
                  </span>
                  <button className="btn btn-xs btn-danger" title="Remove pick"
                    onClick={() => handleRemovePick(p.pick_id)}>
                    ✕
                  </button>
                </div>
              ))
            }
          </div>
        </div>
      )}

      {/* ── OPEN: snake draft board (draft format) ────────────────────────── */}
      {pool.status === 'open' && pool.pool_format === 'draft' && snake_sequence.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h4>Draft Board</h4>
          <div style={{ overflowX: 'auto' }}>
            <table className="table table-condensed table-bordered table-striped">
              <thead>
                <tr><th>Pick #</th><th>Round</th><th>User</th><th>Golfer</th></tr>
              </thead>
              <tbody>
                {snake_sequence.map(slot => (
                  <tr key={slot.pick_num} style={
                    on_clock?.pick_num === slot.pick_num
                      ? { background: is_on_clock ? '#d1fae5' : '#fef9c3', fontWeight: 'bold' }
                      : slot.has_pick ? { background: '#f1f5f9' } : {}
                  }>
                    <td>{slot.pick_num}</td>
                    <td>{slot.round}</td>
                    <td>{slot.username}</td>
                    <td>{slot.player_name || (on_clock?.pick_num === slot.pick_num ? '⏰ picking…' : '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── ACTIVE / COMPLETE: pool standings ─────────────────────────────── */}
      {(pool.status === 'active' || pool.status === 'complete') && standings.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h3 className="text-center">Pool Standings</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="table table-bordered table-striped">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  {Array.from({ length: pool.picks_per_user }, (_, i) => (
                    <th key={i}>Pick {i + 1}</th>
                  ))}
                  <th>Total</th>
                  <th>Paid</th>
                </tr>
              </thead>
              <tbody>
                {standings.map((s, idx) => {
                  const sortedPicks = [...s.picks].sort((a, b) => a.draft_position - b.draft_position)
                  return (
                    <tr key={s.user_id} style={s.is_eliminated ? { background: '#f1f5f9', color: '#94a3b8' } : {}}>
                      <td>{s.is_eliminated ? '—' : idx + 1}</td>
                      <td>
                        <strong>{s.username}</strong>
                        {s.is_eliminated && <span className="label label-danger" style={{ marginLeft: 6 }}>Eliminated</span>}
                      </td>
                      {Array.from({ length: pool.picks_per_user }, (_, i) => {
                        const pick = sortedPicks[i]
                        if (!pick) return <td key={i}>—</td>
                        return (
                          <td key={i}>
                            <div style={{ lineHeight: 1.3 }}>
                              <span style={pick.is_eliminated ? { textDecoration: 'line-through', color: '#94a3b8' } : {}}>
                                {pick.player_name}
                              </span>
                              {pick.is_eliminated
                                ? <span className="label label-warning" style={{ marginLeft: 4, fontSize: 10 }}>CUT</span>
                                : <span style={{ marginLeft: 4 }}><ScoreBadge val={pick.total_value} display={pick.total_display} /></span>
                              }
                              {pick.is_tiebreaker && <span className="label label-info" style={{ marginLeft: 4, fontSize: 10 }}>TB</span>}
                            </div>
                          </td>
                        )
                      })}
                      <td>
                        {s.is_eliminated
                          ? <span style={{ color: '#94a3b8' }}>—</span>
                          : <ScoreBadge val={s.total_value}
                              display={s.total_value === 0 ? 'E' : (s.total_value > 0 ? `+${s.total_value}` : String(s.total_value))} />
                        }
                      </td>
                      <td>{s.paid ? <span style={{ color: '#15803d' }}>$</span> : ''}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── ACTIVE / COMPLETE: ESPN leaderboard ───────────────────────────── */}
      {(pool.status === 'active' || pool.status === 'complete') && espn_field.length > 0 && (() => {
        // Build espn_id → [usernames] map (all pickers, not just one)
        const pickerMap = {}
        picks.forEach(p => {
          if (!pickerMap[p.player_espn_id]) pickerMap[p.player_espn_id] = []
          pickerMap[p.player_espn_id].push(p.username)
        })
        const hasStatus = Object.keys(teeTimes).length > 0
        const lbField = lbPickedOnly
          ? espn_field.filter(p => pickerMap[p.espn_id])
          : espn_field
        return (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>Tournament Leaderboard</h3>
              <button
                className={`btn btn-xs ${lbPickedOnly ? 'btn-primary' : 'btn-default'}`}
                onClick={() => setLbPickedOnly(v => !v)}>
                {lbPickedOnly ? 'Picked players only' : 'All players'}
              </button>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="table table-condensed table-bordered table-striped">
                <thead>
                  <tr>
                    <th>Player</th>
                    <th>Score</th>
                    {hasStatus && <th>Status</th>}
                    {maxRounds > 0 && Array.from({ length: maxRounds }, (_, i) => (
                      <th key={i}>R{i + 1}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lbField.map(player => {
                    const pickers = pickerMap[player.espn_id] || []
                    let pickerLabel = null
                    if (pickers.length === 1) {
                      pickerLabel = <span className="label label-default" style={{ marginLeft: 6, fontSize: 10 }}>{pickers[0]}</span>
                    } else if (pickers.length <= 3) {
                      pickerLabel = pickers.map(u => (
                        <span key={u} className="label label-default" style={{ marginLeft: 4, fontSize: 10 }}>{u}</span>
                      ))
                    } else if (pickers.length > 3) {
                      pickerLabel = <span className="label label-default" style={{ marginLeft: 6, fontSize: 10 }}>many</span>
                    }

                    const tt = teeTimes[String(player.espn_id)] || {}
                    let statusCell = null
                    if (hasStatus) {
                      if (tt.thru > 0) {
                        statusCell = <td>Thru {tt.thru}</td>
                      } else if (tt.tee_time) {
                        statusCell = <td style={{ whiteSpace: 'nowrap' }}>{tt.tee_time}</td>
                      } else {
                        statusCell = <td>—</td>
                      }
                    }

                    return (
                      <tr key={player.espn_id}
                        style={player.is_eliminated ? { background: '#f1f5f9', color: '#9ca3af' } : {}}>
                        <td>
                          {player.name}
                          {pickerLabel}
                        </td>
                        <td>
                          {player.is_eliminated
                            ? <span className="label label-warning">CUT/WD</span>
                            : <ScoreBadge val={player.total_value} display={player.total_display} />
                          }
                        </td>
                        {statusCell}
                        {maxRounds > 0 && <RoundCells rounds={player.rounds} numRounds={maxRounds} />}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })()}

      {/* ── Tiebreaker selector ────────────────────────────────────────────── */}
      {current_user_picks.length > 0 && pool.status === 'open' && (
        <div className="panel panel-default" style={{ maxWidth: 500, margin: '0 auto 20px' }}>
          <div className="panel-heading"><strong>Your Tiebreaker Pick</strong></div>
          <div className="panel-body">
            <p className="text-muted" style={{ fontSize: 13 }}>
              Select one golfer whose individual score will be used to break a tie.
            </p>
            {tbMsg && <div className="alert alert-info">{tbMsg}</div>}
            {current_user_picks.map(pick => (
              <div key={pick.pick_id} style={{ marginBottom: 6 }}>
                <button
                  className={`btn btn-sm ${pick.is_tiebreaker ? 'btn-info' : 'btn-default'}`}
                  onClick={() => handleSetTiebreaker(pick.pick_id)}>
                  {pick.player_name}
                  {pick.is_tiebreaker && ' ★'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Layout>
  )
}
