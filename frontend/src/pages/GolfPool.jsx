import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'

function ScoreBadge({ val, display }) {
  if (display === 'E' || val === 0) return <span style={{ color: '#374151', whiteSpace: 'nowrap' }}>E</span>
  if (val < 0) return <span style={{ color: '#15803d', fontWeight: 'bold', whiteSpace: 'nowrap' }}>{display}</span>
  return <span style={{ color: '#dc2626', fontWeight: 'bold', whiteSpace: 'nowrap' }}>{display}</span>
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
  const [winScoreInput, setWinScoreInput] = useState('')
  const [showCompleted, setShowCompleted] = useState(false)
  const [activeEntry, setActiveEntry]   = useState(1)

  const flashPick = (m) => { setPickMsg(m); setTimeout(() => setPickMsg(''), 4000) }
  const flashTb   = (m) => { setTbMsg(m);   setTimeout(() => setTbMsg(''), 4000) }

  const handleJoinPool = (code) => {
    const invite = (code || joinCode).trim()
    if (!invite) return
    fetch('/api/golf_join_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invite_code: invite }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setJoinMsg(d.error); return }
        if (d.entry_number) setActiveEntry(d.entry_number)
        setJoinMsg(`Joined "${d.pool_name}"!`)
        setSelectedPoolId(d.pool_id)
        fetch('/api/golf_pools').then(r => r.json()).then(d2 => setPools(d2.pools || []))
        load()
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
      .then(d => {
        if (!d.error) {
          setData(d)
          setActiveEntry(e => (d.current_user_entries || []).includes(e) ? e : (d.current_user_entries?.[0] || 1))
        }
      })
  }, [selectedPoolId])

  useEffect(load, [load])

  useEffect(() => {
    if (!data) return
    const status = data.pool?.status
    if (status !== 'active') return  // only poll live scores during active tournament
    const id = setInterval(() => {
      if (document.visibilityState !== 'hidden') load()
    }, 60000)  // match backend cache TTL — polling faster returns the same data
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
        entry_number: activeEntry,
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

  const handleSetWinningScoreTb = (score) => {
    fetch('/api/golf_set_winning_score_tb', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: selectedPoolId, score, entry_number: activeEntry }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { flashTb(d.error); return }
        flashTb('Prediction saved!')
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
                <button className="btn btn-primary" onClick={() => handleJoinPool()}>Join</button>
              </span>
            </div>
            {joinMsg && <p style={{ marginTop: 8 }}>{joinMsg}</p>}
          </div>
        )}
        {pools && pools.length > 0 && (() => {
          const ONE_WEEK = 7 * 24 * 60 * 60 * 1000
          const ACTIVE = new Set(['setup', 'open', 'active'])
          const isRecent = (p) => ACTIVE.has(p.status) ||
            (p.status === 'complete' && p.event_date && (Date.now() - new Date(p.event_date).getTime()) <= ONE_WEEK)
          const visible = showCompleted ? pools : pools.filter(isRecent)
          const hiddenCount = pools.length - pools.filter(isRecent).length
          return (
            <>
              {hiddenCount > 0 && (
                <div style={{ textAlign: 'center', marginBottom: 10 }}>
                  <button className="btn btn-xs btn-default"
                    onClick={() => setShowCompleted(s => !s)}>
                    {showCompleted
                      ? 'Hide completed pools'
                      : `Show ${hiddenCount} >7 day old completed pool${hiddenCount !== 1 ? 's' : ''}`}
                  </button>
                </div>
              )}
              {visible.length === 0 && (
                <p className="text-center text-muted">No active pools. <button className="btn btn-link btn-xs" style={{ padding: 0 }} onClick={() => setShowCompleted(true)}>Show completed pools</button></p>
              )}
              {visible.length > 0 && (
                <div className="list-group" style={{ maxWidth: 600, margin: '0 auto' }}>
                  {visible.map(p => (
                    <button key={p.pool_id} className="list-group-item"
                      onClick={() => setSelectedPoolId(p.pool_id)}>
                      <strong>{p.name}</strong>
                      <span className="text-muted" style={{ marginLeft: 8 }}>{p.event_name}</span>
                      <span className="label label-default pull-right">{p.status}</span>
                    </button>
                  ))}
                </div>
              )}
              <div style={{ maxWidth: 400, margin: '24px auto 0' }}>
                <p style={{ marginBottom: 6 }}>Have an invite code? Join another pool:</p>
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
                    <button className="btn btn-primary" onClick={() => handleJoinPool()}>Join</button>
                  </span>
                </div>
                {joinMsg && <p style={{ marginTop: 8 }}>{joinMsg}</p>}
              </div>
            </>
          )
        })()}
      </Layout>
    )
  }

  if (!data) return <Layout><p>Loading…</p></Layout>

  const { pool, event, participants, picks, current_user_picks, current_user_entries = [1],
          snake_sequence, on_clock, is_on_clock, espn_field, standings, is_admin,
          winning_score_leader, current_user_id, tiers = [], projected_cut = null } = data

  const multiEntry         = pool.max_entries_per_user > 1
  const current_entry_picks = current_user_picks.filter(p => p.entry_number === activeEntry)
  const pickedIds          = new Set(picks.map(p => p.player_espn_id))
  const myPickedIds        = new Set(current_entry_picks.map(p => p.player_espn_id))
  const canPick            = pool.status === 'open' &&
    current_entry_picks.length < pool.picks_per_user &&
    (pool.pool_format === 'async' || is_on_clock)
  const canAddEntry        = pool.status === 'open' && pool.pool_format === 'async' &&
    current_user_entries.length < pool.max_entries_per_user
  const currentEntryFull   = current_entry_picks.length >= pool.picks_per_user

  const filteredField  = espn_field.filter(p =>
    !filter || p.name.toLowerCase().includes(filter.toLowerCase())
  )

  // Tier pick counts (for async + tiered pools) — scoped to active entry
  const pickCountByTier = {}
  current_entry_picks.forEach(p => {
    if (p.tier_id != null) pickCountByTier[p.tier_id] = (pickCountByTier[p.tier_id] || 0) + 1
  })
  const tierAtMax = (tier_id) => {
    if (tier_id == null) return false
    const t = tiers.find(t => t.tier_id === tier_id)
    return t && t.max_picks !== null && (pickCountByTier[tier_id] || 0) >= t.max_picks
  }

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
        {pool.scoring_players && (
          <>&nbsp;&nbsp;Scoring: <strong>top {pool.scoring_players} of {pool.picks_per_user}</strong></>
        )}
        {pool.dnf_handling === 'worst_score' && (
          <>&nbsp;&nbsp;DNF: <strong>worst{pool.dnf_penalty > 0 ? ` +${pool.dnf_penalty}` : ''}</strong></>
        )}
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
        current_entry_picks.length >= pool.picks_per_user && (
        <div className="alert alert-success text-center">
          You&apos;ve submitted all {pool.picks_per_user} picks{multiEntry ? ` for Entry ${activeEntry}` : ''}. Waiting for the tournament to begin.
        </div>
      )}

      {/* ── SETUP / OPEN: who's joined ────────────────────────────────────── */}
      {(pool.status === 'setup' || pool.status === 'open') && participants.length > 0 && (() => {
        const byUser = Object.values(
          participants.reduce((acc, p) => {
            if (!acc[p.user_id]) acc[p.user_id] = { username: p.username, count: 0 }
            acc[p.user_id].count++
            return acc
          }, {})
        ).sort((a, b) => a.username.localeCompare(b.username))
        const totalEntries = participants.length
        const uniqueUsers  = byUser.length
        return (
          <div style={{ marginBottom: 16, padding: '8px 14px', background: '#f8f9fa', borderRadius: 6, border: '1px solid #e5e7eb' }}>
            <span style={{ fontWeight: 600, marginRight: 8 }}>
              {uniqueUsers} {uniqueUsers === 1 ? 'player' : 'players'} joined
              {multiEntry && totalEntries !== uniqueUsers ? ` (${totalEntries} entries)` : ''}:
            </span>
            {byUser.map((u, i) => (
              <span key={u.username}>
                {u.username}{multiEntry && u.count > 1 ? ` (${u.count})` : ''}
                {i < byUser.length - 1 ? ', ' : ''}
              </span>
            ))}
          </div>
        )
      })()}

      {/* ── OPEN: field picker ─────────────────────────────────────────────── */}
      {pool.status === 'open' && espn_field.length === 0 && (
        <div className="alert alert-info text-center">
          Tournament field is not yet available. Please check back closer to tournament start time.
        </div>
      )}

      {pool.status === 'open' && espn_field.length > 0 && (
        <div className="row" style={{ marginBottom: 20 }}>
          <div className="col-md-4">
            <h4>My Picks ({current_entry_picks.length} / {pool.picks_per_user})</h4>
            {multiEntry && (
              <div style={{ marginBottom: 8, display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                {current_user_entries.map(en => (
                  <button key={en}
                    className={`btn btn-xs ${activeEntry === en ? 'btn-primary' : 'btn-default'}`}
                    onClick={() => setActiveEntry(en)}>
                    Entry {en}
                  </button>
                ))}
                {canAddEntry && (
                  <span
                    title={!currentEntryFull ? `Complete all ${pool.picks_per_user} picks for Entry ${activeEntry} first` : ''}
                    style={!currentEntryFull ? { cursor: 'not-allowed' } : {}}>
                    <button className="btn btn-xs btn-success"
                      disabled={!currentEntryFull}
                      style={!currentEntryFull ? { pointerEvents: 'none' } : {}}
                      onClick={() => handleJoinPool(pool.invite_code)}>
                      + Add Entry
                    </button>
                  </span>
                )}
              </div>
            )}
            {current_entry_picks.length === 0
              ? <p className="text-muted">None yet.</p>
              : current_entry_picks.map((p, i) => (
                <div key={p.pick_id} style={{
                  padding: '8px 12px', marginBottom: 6, borderRadius: 4,
                  background: '#dbeafe', border: '1px solid #93c5fd',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <span>
                    <strong>{i + 1}. {p.player_name}</strong>
                    {p.is_tiebreaker && <span className="label label-info" style={{ marginLeft: 6 }}>TB</span>}
                    {p.tier_id != null && tiers.find(t => t.tier_id === p.tier_id) && (
                      <span className="label label-default" style={{ marginLeft: 6, fontSize: 10 }}>
                        {tiers.find(t => t.tier_id === p.tier_id).name}
                      </span>
                    )}
                  </span>
                  <button className="btn btn-xs btn-danger" title="Remove pick"
                    onClick={() => handleRemovePick(p.pick_id)}>
                    ✕
                  </button>
                </div>
              ))
            }
            {pool.tiebreaker_type === 'winning_score' && (() => {
              const pred = participants.find(p => p.user_id === current_user_id && p.entry_number === activeEntry)?.tiebreaker_prediction
              const fmtPred = pred === null || pred === undefined ? null
                : pred === 0 ? 'E' : pred > 0 ? `+${pred}` : String(pred)
              return (
                <div style={{ marginTop: 8, padding: '8px 12px', borderRadius: 4, background: '#f0f9ff', border: '1px solid #bae6fd', fontSize: 13 }}>
                  <strong>Winning score prediction:</strong>{' '}
                  {fmtPred
                    ? <strong style={{ color: pred < 0 ? '#15803d' : pred > 0 ? '#dc2626' : '#374151' }}>{fmtPred}</strong>
                    : <span className="text-muted">not set — scroll down to enter</span>
                  }
                </div>
              )
            })()}
          </div>
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
            {(() => {
              const PlayerRow = ({ player }) => {
                const isMine    = myPickedIds.has(player.espn_id)
                const isTaken   = pickedIds.has(player.espn_id)
                const isElim    = player.is_eliminated
                const blocked   = pool.pool_format === 'async' && tiers.length > 0 && tierAtMax(player.tier_id)
                let rowStyle    = {}
                let label       = null
                if (isMine)                              { rowStyle = { background: '#dbeafe' }; label = <span className="label label-primary">Your pick</span> }
                else if (isTaken && pool.pool_format === 'draft') { rowStyle = { background: '#f1f5f9', color: '#94a3b8' }; label = <span className="label label-default">Taken</span> }
                else if (isElim)                         { rowStyle = { color: '#94a3b8' }; label = <span className="label label-warning">CUT/WD</span> }
                else if (blocked)                        { rowStyle = { color: '#94a3b8' }; label = <span className="label label-warning">Max</span> }
                else if (canPick)                        { rowStyle = { cursor: 'pointer', background: '#f0fdf4' } }
                return (
                  <tr key={player.espn_id} style={rowStyle}
                    onClick={() => {
                      if (!isMine && !isElim && !blocked && canPick &&
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
              }

              if (pool.pool_format === 'async' && tiers.length > 0) {
                // Group filtered field by tier
                const tierGroups = {}
                const uncovered  = []
                filteredField.forEach(p => {
                  if (p.tier_id != null) {
                    if (!tierGroups[p.tier_id]) tierGroups[p.tier_id] = []
                    tierGroups[p.tier_id].push(p)
                  } else {
                    uncovered.push(p)
                  }
                })
                const renderTierTable = (players) => (
                  <table className="table table-condensed table-bordered" style={{ marginBottom: 0 }}>
                    <thead><tr><th>Rank</th><th>Player</th><th></th></tr></thead>
                    <tbody>{players.map(p => <PlayerRow key={p.espn_id} player={p} />)}</tbody>
                  </table>
                )
                return (
                  <div>
                    {tiers.map(tier => {
                      const players   = tierGroups[tier.tier_id] || []
                      const myCount   = pickCountByTier[tier.tier_id] || 0
                      const atMax     = tier.max_picks !== null && myCount >= tier.max_picks
                      const constraint = [
                        tier.min_picks > 0 ? `min ${tier.min_picks}` : '',
                        tier.max_picks !== null ? `max ${tier.max_picks}` : '',
                      ].filter(Boolean).join(', ')
                      return (
                        <div key={tier.tier_id} style={{ marginBottom: 12 }}>
                          <div style={{ background: '#f8f9fa', padding: '6px 10px', borderRadius: '4px 4px 0 0', border: '1px solid #dee2e6', borderBottom: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <strong>{tier.name}</strong>
                            {constraint && <span className="text-muted" style={{ fontSize: 12 }}>({constraint})</span>}
                            <span className={`label label-${atMax ? 'warning' : 'default'}`} style={{ fontSize: 11 }}>
                              {myCount} selected{tier.max_picks !== null ? ` / ${tier.max_picks}` : ''}
                            </span>
                            {tier.tier_type === 'ranking' && tier.rank_min != null && (
                              <span className="text-muted" style={{ fontSize: 11 }}>
                                rank {tier.rank_min}–{tier.rank_max ?? '∞'}
                              </span>
                            )}
                          </div>
                          <div style={{ border: '1px solid #dee2e6', borderRadius: '0 0 4px 4px', overflow: 'hidden' }}>
                            {players.length === 0
                              ? <p className="text-muted" style={{ padding: '8px 12px', margin: 0, fontSize: 13 }}>No players match filter.</p>
                              : renderTierTable(players)}
                          </div>
                        </div>
                      )
                    })}
                    {uncovered.length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ background: '#f8f9fa', padding: '6px 10px', borderRadius: '4px 4px 0 0', border: '1px solid #dee2e6', borderBottom: 'none' }}>
                          <strong>Other</strong>
                          <span className="text-muted" style={{ fontSize: 12, marginLeft: 8 }}>unconstrained</span>
                        </div>
                        <div style={{ border: '1px solid #dee2e6', borderRadius: '0 0 4px 4px', overflow: 'hidden' }}>
                          {renderTierTable(uncovered)}
                        </div>
                      </div>
                    )}
                  </div>
                )
              }

              // Flat view (draft or untired async)
              return (
                <div style={{ maxHeight: 420, overflowY: 'auto', border: '1px solid #dee2e6', borderRadius: 4 }}>
                  <table className="table table-condensed table-bordered" style={{ marginBottom: 0 }}>
                    <thead><tr><th>Rank</th><th>Player</th><th>Status</th></tr></thead>
                    <tbody>{filteredField.map(p => <PlayerRow key={p.espn_id} player={p} />)}</tbody>
                  </table>
                </div>
              )
            })()}
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
          {pool.tiebreaker_type === 'winning_score' && (
            <p className="text-center text-muted" style={{ fontSize: 13, marginTop: -8 }}>
              Tiebreaker: closest prediction to tournament winning score
              {winning_score_leader !== null && winning_score_leader !== undefined
                ? ` — current leader: ${winning_score_leader >= 0 ? `+${winning_score_leader}` : winning_score_leader}`
                : ''}
            </p>
          )}
          {pool.scoring_players && (
            <p className="text-center text-muted" style={{ fontSize: 13, marginTop: -8 }}>
              Top {pool.scoring_players} of {pool.picks_per_user} picks count toward score
            </p>
          )}
          {pool.dnf_handling === 'worst_score' && (
            <p className="text-center text-muted" style={{ fontSize: 13, marginTop: -8 }}>
              DNF picks receive{' '}
              {pool.dnf_penalty === 0
                ? 'worst active player score'
                : `worst active player score + ${pool.dnf_penalty} stroke${pool.dnf_penalty !== 1 ? 's' : ''}`}
            </p>
          )}
          {(() => {
            // Build column definitions — tier-named if tiers exist, otherwise Pick 1..N
            const pickColumns = tiers.length === 0
              ? Array.from({ length: pool.picks_per_user }, (_, i) => ({ label: `Pick ${i + 1}`, tier_id: null, idx: i }))
              : [...tiers].sort((a, b) => a.tier_order - b.tier_order).flatMap(tier => {
                  const count = tier.max_picks !== null
                    ? tier.max_picks
                    : Math.max(1, ...standings.map(s => s.picks.filter(p => p.tier_id === tier.tier_id).length))
                  return Array.from({ length: count }, (_, i) => ({
                    label: count > 1 ? `${tier.name}-${i + 1}` : tier.name,
                    tier_id: tier.tier_id,
                    idx: i,
                  }))
                })
            return (
          <div style={{ overflowX: 'auto' }}>
            <table className="table table-bordered table-striped">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  {pickColumns.map((col, i) => (
                    <th key={i}>{col.label}</th>
                  ))}
                  <th>Total</th>
                  {pool.tiebreaker_type === 'winning_score' && <th>TB Pred</th>}
                  <th>Paid</th>
                </tr>
              </thead>
              <tbody>
                {standings.map((s, idx) => {
                  const sortedPicks = [...s.picks].sort((a, b) => a.draft_position - b.draft_position)
                  const fmtScore = (v) => v === null || v === undefined ? '—' : v === 0 ? 'E' : v > 0 ? `+${v}` : String(v)
                  const cutHappenedRow = projected_cut && !projected_cut.is_projected
                  const isEffectivelyEliminated = !s.is_eliminated && cutHappenedRow &&
                    s.picks.some(p => p.counts !== false && (p.is_eliminated || Object.keys(p.rounds || {}).length < 3))
                  return (
                    <tr
                      key={`${s.user_id}-${s.entry_number}`}
                      style={{
                        ...(s.is_eliminated ? { background: '#f1f5f9', color: '#94a3b8' } : {}),
                        ...(s.user_id === current_user_id ? { background: s.is_eliminated ? '#f1f5f9' : '#eff6ff', borderLeft: '3px solid #3b82f6' } : {}),
                      }}>
                      <td>{s.is_eliminated ? '—' : idx + 1}</td>
                      <td>
                        <strong style={isEffectivelyEliminated ? { color: '#9ca3af' } : {}}>
                          {s.display_name || s.username}
                        </strong>
                        {s.is_eliminated && <span className="label label-danger" style={{ marginLeft: 6 }}>Eliminated</span>}
                        {isEffectivelyEliminated && <span style={{ marginLeft: 6, fontSize: '0.75em', color: '#9ca3af' }}>has cut pick</span>}
                      </td>
                      {pickColumns.map((col, i) => {
                        const pick = col.tier_id === null
                          ? sortedPicks[col.idx]
                          : s.picks.filter(p => p.tier_id === col.tier_id).sort((a, b) => a.draft_position - b.draft_position)[col.idx]
                        if (!pick) return <td key={i}>—</td>
                        const isBench = pick.counts === false
                        const isBelowCut = pick.is_eliminated ||
                          (projected_cut?.is_projected && !pick.is_eliminated && pick.total_value > projected_cut.score) ||
                          (cutHappenedRow && Object.keys(pick.rounds || {}).length < 3)
                        return (
                          <td key={i} style={{ ...(isBench ? { color: '#9ca3af' } : {}), ...(isBelowCut ? { background: '#fef3c7' } : {}) }}>
                            <div style={{ lineHeight: 1.3 }}>
                              <span style={pick.is_eliminated ? { textDecoration: 'line-through', color: '#94a3b8' } : {}}>
                                {pick.player_name}
                              </span>
                              {pick.is_eliminated ? (
                                <>
                                  <span className="label label-warning" style={{ marginLeft: 4, fontSize: 10 }}>CUT</span>
                                  {pool.dnf_handling === 'worst_score' && (
                                    <span style={{ marginLeft: 4 }}>
                                      <ScoreBadge val={pick.total_value}
                                        display={pick.total_value === 0 ? 'E' : pick.total_value > 0 ? `+${pick.total_value}` : String(pick.total_value)} />
                                    </span>
                                  )}
                                </>
                              ) : (
                                <span style={{ marginLeft: 4 }}><ScoreBadge val={pick.total_value} display={pick.total_display} /></span>
                              )}
                              {isBench && (
                                <span className="label label-default" style={{ marginLeft: 4, fontSize: 10 }}>BENCH</span>
                              )}
                              {!isBench && pool.tiebreaker_type === 'player' && pick.is_tiebreaker && (
                                <span className="label label-info" style={{ marginLeft: 4, fontSize: 10 }}>TB</span>
                              )}
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
                      {pool.tiebreaker_type === 'winning_score' && (
                        <td style={{ whiteSpace: 'nowrap' }}>
                          {s.tiebreaker_prediction !== null && s.tiebreaker_prediction !== undefined
                            ? fmtScore(s.tiebreaker_prediction)
                            : <span className="text-muted">—</span>}
                        </td>
                      )}
                      <td>{s.paid ? <span style={{ color: '#15803d' }}>$</span> : ''}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
            )
          })()}
        </div>
      )}

      {/* ── ACTIVE / COMPLETE: ESPN leaderboard ───────────────────────────── */}
      {(pool.status === 'active' || pool.status === 'complete') && espn_field.length > 0 && (() => {
        // Build espn_id → [display names] map (all pickers, not just one)
        const participantDisplayMap = {}
        participants.forEach(p => {
          participantDisplayMap[`${p.user_id}-${p.entry_number}`] = p.display_name || p.username
        })
        const pickerMap = {}
        picks.forEach(p => {
          if (!pickerMap[p.player_espn_id]) pickerMap[p.player_espn_id] = []
          const dn = participantDisplayMap[`${p.user_id}-${p.entry_number}`] || p.username
          if (!pickerMap[p.player_espn_id].includes(dn)) pickerMap[p.player_espn_id].push(dn)
        })
        const hasStatus = Object.keys(teeTimes).length > 0
        const lbField = lbPickedOnly
          ? espn_field.filter(p => pickerMap[p.espn_id])
          : espn_field

        let cutSeparatorAfterIdx = -1
        if (projected_cut?.is_projected && projected_cut.score !== null) {
          lbField.forEach((p, idx) => {
            if (!p.is_eliminated && p.total_value <= projected_cut.score)
              cutSeparatorAfterIdx = idx
          })
        } else if (projected_cut && !projected_cut.is_projected) {
          lbField.forEach((p, idx) => {
            if (Object.keys(p.rounds || {}).length >= 3)
              cutSeparatorAfterIdx = idx
          })
        }

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
                  {lbField.flatMap((player, idx) => {
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

                    const playerRow = (
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

                    if (cutSeparatorAfterIdx === idx) {
                      const colCount = 2 + (hasStatus ? 1 : 0) + (maxRounds > 0 ? maxRounds : 0)
                      const isProjected = projected_cut.is_projected
                      const separatorStyle = isProjected
                        ? { background: '#fef3c7', color: '#92400e', borderTop: '2px dashed #f59e0b', borderBottom: '2px dashed #f59e0b' }
                        : { background: '#f1f5f9', color: '#475569', borderTop: '2px solid #cbd5e1', borderBottom: '2px solid #cbd5e1' }
                      return [playerRow, (
                        <tr key="cut-line-separator">
                          <td colSpan={colCount} style={{
                            textAlign: 'center', fontWeight: 600, padding: '4px 8px', fontSize: 12,
                            ...separatorStyle,
                          }}>
                            {isProjected
                              ? `✂ PROJECTED CUT${projected_cut.display ? ` — ${projected_cut.display}` : ''}${projected_cut.cut_n ? ` (top ${projected_cut.cut_n})` : ''}`
                              : `The following players did not make the cut${projected_cut.display ? ` — ${projected_cut.display}` : ''}`
                            }
                          </td>
                        </tr>
                      )]
                    }

                    return [playerRow]
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })()}

      {/* ── Tiebreaker selector ────────────────────────────────────────────── */}
      {pool.status === 'open' && pool.tiebreaker_type === 'player' && current_entry_picks.length > 0 && (
        <div className="panel panel-default" style={{ maxWidth: 500, margin: '0 auto 20px' }}>
          <div className="panel-heading">
            <strong>Your Tiebreaker Pick{multiEntry ? ` — Entry ${activeEntry}` : ''}</strong>
          </div>
          <div className="panel-body">
            <p className="text-muted" style={{ fontSize: 13 }}>
              Select one golfer whose individual score will be used to break a tie.
            </p>
            {tbMsg && <div className="alert alert-info">{tbMsg}</div>}
            {current_entry_picks.map(pick => (
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
      {pool.status === 'open' && pool.tiebreaker_type === 'winning_score' && (() => {
        const myParticipant = participants.find(p => p.user_id === current_user_id && p.entry_number === activeEntry)
        if (!myParticipant) return null
        const myPred = myParticipant.tiebreaker_prediction
        return (
          <div className="panel panel-default" style={{ maxWidth: 500, margin: '0 auto 20px' }}>
            <div className="panel-heading"><strong>Your Tiebreaker Prediction</strong></div>
            <div className="panel-body">
              <p className="text-muted" style={{ fontSize: 13 }}>
                Predict the winning score relative to par (e.g. -12). If tied on total score,
                the player closest to the actual winning score wins the tiebreaker.
              </p>
              {myPred !== null && myPred !== undefined && (
                <p style={{ marginBottom: 8 }}>
                  Current prediction: <strong>{myPred >= 0 ? `+${myPred}` : myPred}</strong>
                </p>
              )}
              {tbMsg && <div className="alert alert-info">{tbMsg}</div>}
              <div className="input-group" style={{ maxWidth: 260 }}>
                <input type="number" className="form-control" placeholder="Score vs par (e.g. -12)"
                  value={winScoreInput}
                  onChange={e => setWinScoreInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && winScoreInput !== '' && handleSetWinningScoreTb(parseInt(winScoreInput))} />
                <span className="input-group-btn">
                  <button className="btn btn-info"
                    disabled={winScoreInput === ''}
                    onClick={() => handleSetWinningScoreTb(parseInt(winScoreInput))}>
                    Save
                  </button>
                </span>
              </div>
            </div>
          </div>
        )
      })()}
    </Layout>
  )
}
