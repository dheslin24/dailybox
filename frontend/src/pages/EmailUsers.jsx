import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function EmailUsers() {
  const [users, setUsers]         = useState([])
  const [filter, setFilter]       = useState('')
  const [selected, setSelected]   = useState(new Set())
  const [sortCol, setSortCol]     = useState('username')
  const [sortDir, setSortDir]     = useState('asc')
  const [subject, setSubject]     = useState('')
  const [body, setBody]           = useState('')
  const [status, setStatus]       = useState(null)
  const [loading, setLoading]     = useState(false)

  useEffect(() => {
    fetch('/api/admin_users').then(r => r.json()).then(d => setUsers(d.users || []))
  }, [])

  const cols = ['username', 'first_name', 'last_name', 'email']
  const q = filter.toLowerCase()
  const filtered = q
    ? users.filter(u => cols.some(c => (u[c] || '').toLowerCase().includes(q)))
    : users
  const sorted = [...filtered].sort((a, b) => {
    const av = (a[sortCol] || '').toLowerCase()
    const bv = (b[sortCol] || '').toLowerCase()
    return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
  })

  const handleSortClick = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('asc') }
  }
  const sortIcon = (col) => sortCol !== col ? ' ↕' : sortDir === 'asc' ? ' ↑' : ' ↓'

  const toggleUser = (userid) => setSelected(s => {
    const n = new Set(s)
    n.has(userid) ? n.delete(userid) : n.add(userid)
    return n
  })
  const selectAllFiltered = () => setSelected(s => {
    const n = new Set(s)
    sorted.forEach(u => n.add(u.userid))
    return n
  })
  const clearAll = () => setSelected(new Set())

  const selectedEmails = users.filter(u => selected.has(u.userid) && u.email).map(u => u.email)

  const handleSend = (e) => {
    e.preventDefault()
    if (!selectedEmails.length) { setStatus({ type: 'danger', msg: 'No recipients selected (or selected users have no email)' }); return }
    setStatus(null)
    setLoading(true)
    fetch('/api/send_bygemail', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rcpts: selectedEmails, subject, body }),
    })
      .then(r => r.json())
      .then(d => {
        setLoading(false)
        if (d.ok) { setStatus({ type: 'success', msg: `Sent to ${d.sent} recipient(s)` }); setSubject(''); setBody(''); clearAll() }
        else setStatus({ type: 'danger', msg: d.error || 'Send failed' })
      })
      .catch(() => { setLoading(false); setStatus({ type: 'danger', msg: 'Network error' }) })
  }

  const thStyle = { cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }

  return (
    <Layout>
      <h2>Email Users</h2>

      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          className="form-control input-sm"
          style={{ maxWidth: 280 }}
          placeholder="Filter by name, username, or email…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
        <button className="btn btn-xs btn-default" onClick={selectAllFiltered}>Select all filtered ({sorted.length})</button>
        <button className="btn btn-xs btn-default" onClick={clearAll}>Clear all</button>
        <span style={{ fontSize: '0.9em', color: '#6b7280' }}>{selected.size} selected</span>
      </div>

      <div style={{ overflowX: 'auto', maxHeight: 340, overflowY: 'auto', marginBottom: 20, border: '1px solid #ddd' }}>
        <table className="table table-condensed table-bordered table-hover" style={{ marginBottom: 0 }}>
          <thead style={{ position: 'sticky', top: 0, background: '#fff' }}>
            <tr>
              <th style={{ width: 36 }}></th>
              {[['username','Username'],['first_name','First'],['last_name','Last'],['email','Email']].map(([col, label]) => (
                <th key={col} style={thStyle} onClick={() => handleSortClick(col)}>{label}{sortIcon(col)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(u => (
              <tr
                key={u.userid}
                style={{ cursor: 'pointer', background: selected.has(u.userid) ? '#eff6ff' : undefined }}
                onClick={() => toggleUser(u.userid)}
              >
                <td style={{ textAlign: 'center' }}>
                  <input type="checkbox" checked={selected.has(u.userid)} onChange={() => toggleUser(u.userid)} onClick={e => e.stopPropagation()} />
                </td>
                <td>{u.username}</td>
                <td>{u.first_name}</td>
                <td>{u.last_name}</td>
                <td style={{ color: u.email ? undefined : '#9ca3af' }}>{u.email || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleSend}>
        <div className="form-group">
          <label>Subject</label>
          <input className="form-control" type="text" value={subject} onChange={e => setSubject(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Body</label>
          <textarea className="form-control" rows={6} value={body} onChange={e => setBody(e.target.value)} />
        </div>
        {status && <div className={`alert alert-${status.type}`}>{status.msg}</div>}
        <button className="btn btn-primary" type="submit" disabled={loading || !selected.size || !subject || !body}>
          {loading ? 'Sending…' : `Send to ${selectedEmails.length} recipient(s)`}
        </button>
      </form>
    </Layout>
  )
}
