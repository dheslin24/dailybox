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
  const [adminPickUserId, setAdminPickUserId] = useState('')
  const [adminPickEntryId, setAdminPickEntryId] = useState('')
  const [metaEntryId, setMetaEntryId] = useState('')
  const [metaOdds, setMetaOdds] = useState('')
  const [metaJockey, setMetaJockey] = useState('')
  const [metaTrainer, setMetaTrainer] = useState('')
  const [csvFile, setCsvFile] = useState(null)

  const flash = (text, ok = true) => { setMsg({ text, ok }); setTimeout(() => setMsg({ text: '', ok: true }), 4000) }

  const loadRaces = () =>
    fetch('/api/hr_races').then(r => r.json()).then(d => setRaces(d.races || []))

  const loadUsers = () =>
    fetch('/api/hr_users').then(r => r.json()).then(d => setUsers(d.users || []))

  const loadPool = (raceId) =>
    fetch(`/api/hr_pool?race_id=${raceId}`)
      .then(r => r.text())
      .then(text => {
        let d
        try { d = JSON.parse(text) } catch (e) {
          flash(`Non-JSON response: ${text.slice(0, 300)}`, false); return
        }
        if (d.error) { flash(d.error, false); return }
        setPoolData(d)
        const order = Array(20).fill('')
        d.draft_order.forEach(slot => {
          if (slot.pick_order >= 1 && slot.pick_order <= 20)
            order[slot.pick_order - 1] = String(slot.user_id)
        })
        setDraftOrder(order)
      })
      .catch(e => flash(`Load failed: ${e.message}`, false))

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
    const order = draftOrder
      .map((u, i) => u !== '' ? { pick_order: i + 1, user_id: Number(u) } : null)
      .filter(Boolean)
    const seen = new Set()
    for (const { user_id } of order) {
      if (seen.has(user_id)) { flash('Duplicate user in draft order — please fix', false); return }
      seen.add(user_id)
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

  const selectMetaEntry = (entryId) => {
    setMetaEntryId(entryId)
    const e = poolData?.entries.find(e => e.entry_id === Number(entryId))
    setMetaOdds(e?.odds || '')
    setMetaJockey(e?.jockey || '')
    setMetaTrainer(e?.trainer || '')
  }

  const saveHorseMeta = () => {
    if (!metaEntryId) return
    post('/api/hr_set_horse_meta', {
      race_id: selectedRace.race_id,
      entry_id: Number(metaEntryId),
      odds: metaOdds,
      jockey: metaJockey,
      trainer: metaTrainer,
    }).then(d => {
      if (d.success) { flash('Horse info saved'); loadPool(selectedRace.race_id) }
      else flash(d.error, false)
    })
  }

  const importCsv = () => {
    if (!csvFile || !selectedRace) return
    const fd = new FormData()
    fd.append('race_id', selectedRace.race_id)
    fd.append('file', csvFile)
    fetch('/api/hr_import_horses', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          flash(`Imported ${d.added} horse${d.added !== 1 ? 's' : ''}`)
          setCsvFile(null)
          loadPool(selectedRace.race_id)
        } else {
          flash(d.error, false)
        }
      })
  }

  const adminToggle = (url, body) =>
    post(url, body).then(d => { if (d.success) loadPool(selectedRace.race_id); else flash(d.error, false) })

  const toggleScratched = (entryId, currentScratched) =>
    adminToggle('/api/hr_scratch_horse', { entry_id: entryId, scratched: !currentScratched })

  const togglePaid = (userId, currentPaid) =>
    adminToggle('/api/hr_set_paid', { race_id: selectedRace.race_id, user_id: userId, paid: !currentPaid })

  const adminSetPick = () => {
    if (!adminPickUserId || !adminPickEntryId) return
    const user = poolData.draft_order.find(d => d.user_id === Number(adminPickUserId))
    const entry = poolData.entries.find(e => e.entry_id === Number(adminPickEntryId))
    if (!window.confirm(`Set ${user?.username}'s pick to "${entry?.horse_name}"?`)) return
    post('/api/hr_admin_set_pick', {
      race_id: selectedRace.race_id,
      user_id: Number(adminPickUserId),
      entry_id: Number(adminPickEntryId),
    }).then(d => {
      if (d.success) {
        flash(`Pick set: ${user?.username} → ${entry?.horse_name}`)
        setAdminPickUserId('')
        setAdminPickEntryId('')
        loadPool(selectedRace.race_id)
      } else {
        flash(d.error, false)
      }
    })
  }

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
                  <div className="form-inline" style={{ marginBottom: 6 }}>
                    <input className="form-control input-sm" placeholder="Post #"
                      value={postPos} onChange={e => setPostPos(e.target.value)}
                      style={{ width: 55, marginRight: 4 }} />
                    <input className="form-control input-sm" placeholder="Horse name"
                      value={horseName} onChange={e => setHorseName(e.target.value)}
                      style={{ width: 130, marginRight: 4 }}
                      onKeyDown={e => e.key === 'Enter' && addHorse()} />
                    <button className="btn btn-sm btn-success" onClick={addHorse}>Add</button>
                  </div>
                  <div style={{ borderTop: '1px solid #eee', paddingTop: 8, marginBottom: 10 }}>
                    <div className="form-inline">
                      <input type="file" accept=".csv"
                        style={{ marginRight: 6, fontSize: 12 }}
                        onChange={e => setCsvFile(e.target.files[0] || null)} />
                      <button className="btn btn-sm btn-default"
                        disabled={!csvFile}
                        onClick={importCsv}>
                        Import CSV
                      </button>
                    </div>
                    <p className="text-muted" style={{ fontSize: 11, marginTop: 4, marginBottom: 0 }}>
                      Columns: horse name, post #, odds, jockey, trainer
                    </p>
                  </div>
                  <table className="table table-condensed table-modern" style={{ fontSize: 12 }}>
                    <tbody>
                      {poolData.entries.map(e => (
                        <tr key={e.entry_id} style={{ background: e.is_winner ? '#ffd700' : e.scratched ? '#f5f5f5' : undefined }}>
                          <td style={{ width: 28 }}>{e.post_position ? `#${e.post_position}` : ''}</td>
                          <td style={{ textDecoration: e.scratched ? 'line-through' : undefined, color: e.scratched ? '#999' : undefined }}>
                            {e.horse_name}{e.is_winner ? ' 🏆' : ''}
                          </td>
                          <td style={{ width: 60, whiteSpace: 'nowrap' }}>
                            <button
                              className={`btn btn-xs ${e.scratched ? 'btn-warning' : 'btn-default'}`}
                              style={{ marginRight: 2 }}
                              onClick={() => toggleScratched(e.entry_id, e.scratched)}>
                              {e.scratched ? '↺ Unscr' : 'Scratch'}
                            </button>
                            {!e.picked_by && !e.scratched && (
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

          {/* Horse metadata */}
          <div className="panel panel-default">
            <div className="panel-heading"><strong>Horse Info (Odds / Jockey / Trainer)</strong></div>
            <div className="panel-body">
              <div className="form-inline" style={{ marginBottom: 8 }}>
                <select className="form-control input-sm" style={{ marginRight: 8, minWidth: 180 }}
                  value={metaEntryId} onChange={e => selectMetaEntry(e.target.value)}>
                  <option value="">— select horse —</option>
                  {poolData.entries.map(e => (
                    <option key={e.entry_id} value={e.entry_id}>
                      {e.post_position ? `#${e.post_position} ` : ''}{e.horse_name}
                    </option>
                  ))}
                </select>
              </div>
              {metaEntryId && (
                <div className="form-inline">
                  <input className="form-control input-sm" placeholder="Odds (e.g. 5/2)"
                    value={metaOdds} onChange={e => setMetaOdds(e.target.value)}
                    style={{ width: 100, marginRight: 6 }} />
                  <input className="form-control input-sm" placeholder="Jockey"
                    value={metaJockey} onChange={e => setMetaJockey(e.target.value)}
                    style={{ width: 150, marginRight: 6 }} />
                  <input className="form-control input-sm" placeholder="Trainer"
                    value={metaTrainer} onChange={e => setMetaTrainer(e.target.value)}
                    style={{ width: 150, marginRight: 6 }} />
                  <button className="btn btn-sm btn-primary" onClick={saveHorseMeta}>Save</button>
                </div>
              )}
            </div>
          </div>

          {/* Admin override pick */}
          {poolData.race.status === 'open' && poolData.draft_order.length > 0 && (
            <div className="panel panel-warning">
              <div className="panel-heading"><strong>Admin Override Pick</strong></div>
              <div className="panel-body">
                <div className="form-inline">
                  <select className="form-control input-sm" style={{ marginRight: 8, minWidth: 140 }}
                    value={adminPickUserId} onChange={e => setAdminPickUserId(e.target.value)}>
                    <option value="">— select user —</option>
                    {poolData.draft_order.map(d => (
                      <option key={d.user_id} value={d.user_id}>
                        {d.username}{d.has_picked ? ' (has pick)' : ''}
                      </option>
                    ))}
                  </select>
                  <select className="form-control input-sm" style={{ marginRight: 8, minWidth: 180 }}
                    value={adminPickEntryId} onChange={e => setAdminPickEntryId(e.target.value)}>
                    <option value="">— select horse —</option>
                    {poolData.entries.filter(e => !e.picked_by && !e.scratched).map(e => (
                      <option key={e.entry_id} value={e.entry_id}>
                        {e.post_position ? `#${e.post_position} ` : ''}{e.horse_name}
                      </option>
                    ))}
                  </select>
                  <button className="btn btn-sm btn-warning"
                    disabled={!adminPickUserId || !adminPickEntryId}
                    onClick={adminSetPick}>
                    Set Pick
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Current picks summary */}
          {poolData.draft_order.length > 0 && (
            <div className="panel panel-default">
              <div className="panel-heading"><strong>Draft Board</strong></div>
              <div className="panel-body">
                <table className="table table-condensed table-modern" style={{ fontSize: 13 }}>
                  <thead>
                    <tr><th>#</th><th>User</th><th>Pick</th><th>Paid</th></tr>
                  </thead>
                  <tbody>
                    {poolData.draft_order.map(d => {
                      const isOnClock = poolData.race.status === 'open' && poolData.on_clock?.user_id === d.user_id
                      return (
                        <tr key={d.pick_order} style={{ background: isOnClock ? '#fff3cd' : undefined, fontWeight: isOnClock ? 'bold' : undefined }}>
                          <td>{d.pick_order}</td>
                          <td>{d.username}{isOnClock ? ' ⏰' : ''}</td>
                          <td>{d.horse_name || '—'}</td>
                          <td>
                            <button
                              className={`btn btn-xs ${d.paid ? 'btn-success' : 'btn-default'}`}
                              onClick={() => togglePaid(d.user_id, d.paid)}>
                              {d.paid ? '✓ Paid' : 'Unpaid'}
                            </button>
                          </td>
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
