import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'

const STATUS_LABEL = { setup: 'Setup', open: 'Open — picks are live!', locked: 'Locked', final: 'Final' }

export default function HorseRacingPool() {
  const [searchParams, setSearchParams] = useSearchParams()
  const raceId = searchParams.get('race_id')

  const [races, setRaces] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [picking, setPicking] = useState(false)

  // Load race list when no race selected
  useEffect(() => {
    if (raceId) return
    fetch('/api/hr_races')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setRaces(d.races) })
  }, [raceId])

  // Load pool data when race selected
  const load = useCallback(() => {
    if (!raceId) return
    fetch(`/api/hr_pool?race_id=${raceId}`)
      .then(res => {
        if (res.status === 401) { window.location.href = '/app/login'; return null }
        return res.json()
      })
      .then(d => {
        if (!d) return
        if (d.error) setError(d.error)
        else setData(d)
      })
  }, [raceId])

  useEffect(load, [load])

  // Auto-refresh every 15s while open
  useEffect(() => {
    if (!data || data.race.status === 'final' || data.race.status === 'setup') return
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load, data])

  const pickHorse = (entryId) => {
    if (picking) return
    setPicking(true)
    fetch('/api/hr_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ race_id: parseInt(raceId), entry_id: entryId }),
    })
      .then(res => res.json())
      .then(d => {
        setPicking(false)
        if (d.error) alert(d.error)
        else load()
      })
      .catch(() => setPicking(false))
  }

  // ── Race list ──────────────────────────────────────────────────────────────
  if (!raceId) {
    if (!races) return <Layout><p>Loading...</p></Layout>
    if (races.length === 0) return <Layout><p>You are not currently in any horse racing pools.</p></Layout>
    if (races.length === 1) {
      setSearchParams({ race_id: races[0].race_id })
      return null
    }
    return (
      <Layout>
        <h2>Horse Racing Pools</h2>
        {races.map(r => (
          <div key={r.race_id} style={{ marginBottom: 8 }}>
            <a href={`/app/horse_racing?race_id=${r.race_id}`}>
              <strong>{r.name}</strong>
            </a>
            {r.race_date && <span className="text-muted"> — {r.race_date}</span>}
            <span className="label label-default" style={{ marginLeft: 8 }}>{r.status}</span>
          </div>
        ))}
      </Layout>
    )
  }

  if (error) return <Layout><p style={{ color: 'red' }}>{error}</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  const { race, entries, draft_order, on_clock, is_on_clock, current_user_pick, winner } = data

  return (
    <Layout>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>{race.name}</h2>
        <span className="text-muted">{race.race_date}</span>
        <span style={{ marginLeft: 12, fontWeight: 'bold' }}>{STATUS_LABEL[race.status] || race.status}</span>
      </div>

      {/* Winner banner */}
      {winner && (
        <div style={{ background: '#ffd700', border: '2px solid #b8860b', borderRadius: 8, padding: '12px 20px', marginBottom: 20, textAlign: 'center' }}>
          <h3 style={{ margin: 0 }}>🏆 {winner.horse_name} wins! — picked by <strong>{winner.username}</strong></h3>
        </div>
      )}

      {/* On the clock banner */}
      {race.status === 'open' && on_clock && (
        <div style={{
          background: is_on_clock ? '#d4edda' : '#fff3cd',
          border: `2px solid ${is_on_clock ? '#28a745' : '#ffc107'}`,
          borderRadius: 8, padding: '10px 16px', marginBottom: 16, textAlign: 'center',
        }}>
          {is_on_clock
            ? <strong>🎉 It's your pick! Select a horse below.</strong>
            : <span>On the clock: <strong>{on_clock.username}</strong> (pick #{on_clock.pick_order})</span>
          }
        </div>
      )}

      {race.status === 'locked' && (
        <div className="alert alert-warning" style={{ marginBottom: 16 }}>
          Picks are locked — waiting for race day!
        </div>
      )}

      {/* User's current pick */}
      {current_user_pick && (
        <div style={{ background: '#cce5ff', border: '1px solid #004085', borderRadius: 6, padding: '8px 14px', marginBottom: 16 }}>
          Your pick: <strong>
            {entries.find(e => e.entry_id === current_user_pick.entry_id)?.post_position
              ? `#${entries.find(e => e.entry_id === current_user_pick.entry_id).post_position} `
              : ''}
            {current_user_pick.horse_name}
          </strong>
        </div>
      )}

      <div className="row">
        {/* ── Horse field ─────────────────────────────────────────────────── */}
        <div className="col-md-7">
          <h4>The Field ({entries.length} horses)</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {entries.map(e => {
              const isMine = current_user_pick?.entry_id === e.entry_id
              const isTaken = !!e.picked_by
              const canPick = race.status === 'open' && is_on_clock && !isTaken && !current_user_pick

              let bg = '#f8f9fa', border = '1px solid #ccc', cursor = 'default'
              if (e.is_winner)  { bg = '#ffd700'; border = '2px solid #b8860b' }
              else if (isMine)  { bg = '#cce5ff'; border = '2px solid #0066cc' }
              else if (isTaken) { bg = '#e9ecef' }
              else if (canPick) { bg = '#d4edda'; border = '1px solid #28a745'; cursor = 'pointer' }

              return (
                <div
                  key={e.entry_id}
                  onClick={() => canPick && pickHorse(e.entry_id)}
                  style={{
                    width: 148, padding: '8px 10px', borderRadius: 6,
                    background: bg, border, cursor,
                    opacity: isTaken && !isMine && !e.is_winner ? 0.55 : 1,
                    transition: 'opacity 0.15s',
                  }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: 13 }}>
                    {e.post_position ? `#${e.post_position} ` : ''}{e.horse_name}
                  </div>
                  <div style={{ fontSize: 11, marginTop: 3, color: '#555' }}>
                    {e.is_winner && '🏆 Winner'}
                    {!e.is_winner && isMine && '✓ Your pick'}
                    {!e.is_winner && !isMine && isTaken && e.picked_by_name}
                    {!isTaken && canPick && <span style={{ color: '#28a745' }}>Click to pick</span>}
                    {!isTaken && !canPick && race.status === 'open' && <span style={{ color: '#999' }}>Available</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Draft board ──────────────────────────────────────────────────── */}
        <div className="col-md-5">
          <h4>Draft Board</h4>
          <table className="table table-condensed table-striped" style={{ fontSize: 13 }}>
            <thead>
              <tr><th style={{ width: 30 }}>#</th><th>Picker</th><th>Horse</th></tr>
            </thead>
            <tbody>
              {draft_order.map(d => {
                const isOnClock = race.status === 'open' && on_clock?.user_id === d.user_id
                return (
                  <tr key={d.pick_order} style={{
                    background: isOnClock ? '#fff3cd' : undefined,
                    fontWeight: isOnClock ? 'bold' : undefined,
                  }}>
                    <td>{d.pick_order}</td>
                    <td>{d.username}{isOnClock ? ' ⏰' : ''}</td>
                    <td>{d.horse_name || (isOnClock ? '...' : '—')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  )
}
