import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

const STATUS_OPTIONS = ['setup', 'open', 'locked', 'final']

export default function HorseRacingAdmin() {
  const [races, setRaces] = useState([])
  const [users, setUsers] = useState([])
  const [selectedRace, setSelectedRace] = useState(null)
  const [poolData, setPoolData] = useState(null)
  const [msg, setMsg] = useState({ text: '', ok: true })

  const [raceName, setRaceName] = useState('')
  const [raceDate, setRaceDate] = useState('')
  const [postPos, setPostPos] = useState('')
  const [horseName, setHorseName] = useState('')
  const [draftOrder, setDraftOrder] = useState(Array(20).fill(''))

  const flash = (text, ok = true) => { setMsg({ text, ok }); setTimeout(() => setMsg({ text: '', ok: true }), 4000) }

  const loadRaces = () =>
    fetch('/api/hr_races').then(r => r.json()).then(d => setRaces(d.races || []))

  const loadUsers = () =>
    fetch('/api/hr_users').then(r => r.json()).then(d => setUsers(d.users || []))

  const loadPool = (raceId) =>
    fetch(`/api/hr_pool?race_id=${raceId}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) return
        setPoolData(d)
        // Pre-fill draft order dropdowns from saved data
        const order = Array(20).fill('')
        d.draft_order.forEach(slot => {
          if (slot.pick_order >= 1 && slot.pick_order <= 20)
            order[slot.pick_order - 1] = String(slot.user_id)
        })
        setDraftOrder(order)
      })

  useEffect(() => { loadRaces(); loadUsers() }, [])

  const selectRace = (race) => { setSelectedRace(race); loadPool(race.race_id) }

  const post = (url, body) =>
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(r => r.json())

  const initDb = () =>
    post('/api/hr_init_db', {}).then(d => flash(d.success ? 'DB tables ready!' : d.error, !!d.success))

  const createRace = () => {
    if (!raceName.trim()) return
    post('/api/hr_create_race', { name: raceName.trim(), race_date: raceDate })
      .then(d => {
        if (d.success) { flash(`Race created (ID ${d.race_id})`); setRaceName(''); setRaceDate(''); loadRaces() }
        else flash(d.error, false)
      })
  }

  const addHorse = () => {
    if (!horseName.trim() || !selectedRace) return
    post('/api/hr_add_horse', { race_id: selectedRace.race_id, post_position: postPos ? parseInt(postPos) : null, horse_name: horseName.trim() })
      .then(d => {
        if (d.success) { flash('Horse added'); setPostPos(''); setHorseName(''); loadPool(selectedRace.race_id) }
        else flash(d.error, false)
      })
  }

  const deleteHorse = (entryId) =>
    post('/api/hr_delete_horse', { entry_id: entryId })
      .then(d => { if (d.success) loadPool(selectedRace.race_id); else flash(d.error, false) })

  const saveDraftOrder = () => {
    const order = draftOrder.filter(u => u !== '').map(Number)
    const seen = new Set()
    for (const id of order) {
      if (seen.has(id)) { flash('Duplicate user in draft order — please fix', false); return }
      seen.add(id)
    }
    post('/api/hr_set_draft_order', { race_id: selectedRace.race_id, order })
      .then(d => { flash(d.success ? 'Draft order saved!' : d.error, !!d.success); if (d.success) loadPool(selectedRace.race_id) })
  }

  const setStatus = (status) =>
    post('/api/hr_set_race_status', { race_id: selectedRace.race_id, status })
      .then(d => {
        if (d.success) { flash(`Status → ${status}`); loadRaces(); loadPool(selectedRace.race_id) }
        else flash(d.error, false)
      })

  const markWinner = (entryId, horseName) => {
    if (!window.confirm(`Mark "${horseName}" as the winner?`)) return
    post('/api/hr_mark_winner', { race_id: selectedRace.race_id, entry_id: entryId })
      .then(d => { flash(d.success ? `🏆 ${horseName} marked as winner!` : d.error, !!d.success); if (d.success) loadPool(selectedRace.race_id) })
  }

  return (
    <Layout>
      <h2>Horse Racing Admin</h2>

      {msg.text && (
        <div className={`alert alert-${msg.ok ? 'success' : 'danger'}`}>{msg.text}</div>
      )}

      {/* DB init */}
      <p>
        <button className="btn btn-xs btn-default" onClick={initDb}>
          Initialize DB Tables (first time only)
        </button>
      </p>

      {/* Create race */}
      <div className="panel panel-default">
        <div className="panel-heading"><strong>Create Race</strong></div>
        <div className="panel-body">
          <div className="form-inline">
            <input className="form-control" placeholder="Race name (e.g. Kentucky Derby 2026)"
              value={raceName} onChange={e => setRaceName(e.target.value)}
              style={{ width: 280, marginRight: 8 }} />
            <input className="form-control" type="date" value={raceDate}
              onChange={e => setRaceDate(e.target.value)} style={{ marginRight: 8 }} />
            <button className="btn btn-primary" onClick={createRace}>Create</button>
          </div>
        </div>
      </div>

      {/* Race selector */}
      {races.length > 0 && (
        <div className="panel panel-default">
          <div className="panel-heading"><strong>Manage Race</strong></div>
          <div className="panel-body">
            {races.map(r => (
              <button key={r.race_id}
                className={`btn btn-sm ${selectedRace?.race_id === r.race_id ? 'btn-primary' : 'btn-default'}`}
                style={{ marginRight: 6, marginBottom: 4 }}
                onClick={() => selectRace(r)}>
                {r.name} <span className="label label-default">{r.status}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Race management */}
      {selectedRace && poolData && (
        <>
          <h3>{selectedRace.name}</h3>

          {/* Status */}
          <div style={{ marginBottom: 20 }}>
            <strong>Status: </strong>
            {STATUS_OPTIONS.map(s => (
              <button key={s}
                className={`btn btn-sm ${poolData.race.status === s ? 'btn-primary' : 'btn-default'}`}
                style={{ marginRight: 4 }}
                onClick={() => setStatus(s)}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          <div className="row">
            {/* ── Horses ───────────────────────────────────────────────── */}
            <div className="col-md-4">
              <div className="panel panel-default">
                <div className="panel-heading">
                  <strong>Horses ({poolData.entries.length})</strong>
                </div>
                <div className="panel-body">
                  <div className="form-inline" style={{ marginBottom: 10 }}>
                    <input className="form-control input-sm" placeholder="Post #"
                      value={postPos} onChange={e => setPostPos(e.target.value)}
                      style={{ width: 55, marginRight: 4 }} />
                    <input className="form-control input-sm" placeholder="Horse name"
                      value={horseName} onChange={e => setHorseName(e.target.value)}
                      style={{ width: 130, marginRight: 4 }}
                      onKeyDown={e => e.key === 'Enter' && addHorse()} />
                    <button className="btn btn-sm btn-success" onClick={addHorse}>Add</button>
                  </div>
                  <table className="table table-condensed" style={{ fontSize: 12 }}>
                    <tbody>
                      {poolData.entries.map(e => (
                        <tr key={e.entry_id} style={{ background: e.is_winner ? '#ffd700' : undefined }}>
                          <td style={{ width: 28 }}>{e.post_position ? `#${e.post_position}` : ''}</td>
                          <td>{e.horse_name}{e.is_winner ? ' 🏆' : ''}</td>
                          <td style={{ width: 28 }}>
                            {!e.picked_by && (
                              <button className="btn btn-xs btn-danger"
                                onClick={() => deleteHorse(e.entry_id)}>×</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* ── Draft order ───────────────────────────────────────────── */}
            <div className="col-md-4">
              <div className="panel panel-default">
                <div className="panel-heading"><strong>Draft Order</strong></div>
                <div className="panel-body">
                  {Array.from({ length: 20 }, (_, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', marginBottom: 3 }}>
                      <span style={{ width: 22, textAlign: 'right', marginRight: 6, color: '#888', fontSize: 12 }}>
                        {i + 1}.
                      </span>
                      <select className="form-control input-sm" style={{ width: 165 }}
                        value={draftOrder[i]}
                        onChange={e => {
                          const updated = [...draftOrder]
                          updated[i] = e.target.value
                          setDraftOrder(updated)
                        }}>
                        <option value="">— empty —</option>
                        {users.map(u => (
                          <option key={u.userid} value={u.userid}>
                            {u.username}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                  <button className="btn btn-primary btn-sm" style={{ marginTop: 8 }}
                    onClick={saveDraftOrder}>
                    Save Draft Order
                  </button>
                </div>
              </div>
            </div>

            {/* ── Mark winner ───────────────────────────────────────────── */}
            <div className="col-md-4">
              <div className="panel panel-default">
                <div className="panel-heading"><strong>Mark Winner</strong></div>
                <div className="panel-body">
                  <p className="text-muted" style={{ fontSize: 12 }}>Click the winning horse after the race.</p>
                  {poolData.entries.map(e => (
                    <div key={e.entry_id} style={{ marginBottom: 4 }}>
                      <button
                        className={`btn btn-sm btn-block ${e.is_winner ? 'btn-warning' : 'btn-default'}`}
                        onClick={() => markWinner(e.entry_id, e.horse_name)}>
                        {e.post_position ? `#${e.post_position} ` : ''}{e.horse_name}
                        {e.is_winner ? ' 🏆' : ''}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Current picks summary */}
          {poolData.draft_order.length > 0 && (
            <div className="panel panel-default">
              <div className="panel-heading"><strong>Draft Board</strong></div>
              <div className="panel-body">
                <table className="table table-condensed table-striped" style={{ fontSize: 13 }}>
                  <thead>
                    <tr><th>#</th><th>User</th><th>Pick</th></tr>
                  </thead>
                  <tbody>
                    {poolData.draft_order.map(d => {
                      const isOnClock = poolData.race.status === 'open' && poolData.on_clock?.user_id === d.user_id
                      return (
                        <tr key={d.pick_order} style={{ background: isOnClock ? '#fff3cd' : undefined, fontWeight: isOnClock ? 'bold' : undefined }}>
                          <td>{d.pick_order}</td>
                          <td>{d.username}{isOnClock ? ' ⏰' : ''}</td>
                          <td>{d.horse_name || '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </Layout>
  )
}
