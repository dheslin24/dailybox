import { useState } from 'react'
import Layout from '../components/Layout'

export default function EmailUsers() {
  const [rcpt, setRcpt] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setStatus(null)
    setLoading(true)
    fetch('/api/send_bygemail', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rcpt, subject, body }),
    })
      .then(res => res.json())
      .then(d => {
        setLoading(false)
        if (d.ok) {
          setStatus({ type: 'success', msg: `Email sent to ${rcpt}` })
          setRcpt(''); setSubject(''); setBody('')
        } else {
          setStatus({ type: 'danger', msg: d.error || 'Send failed' })
        }
      })
      .catch(() => { setLoading(false); setStatus({ type: 'danger', msg: 'Network error' }) })
  }

  return (
    <Layout>
      <h2>Send Email</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>To (email address)</label>
          <input
            className="form-control"
            type="email"
            value={rcpt}
            onChange={e => setRcpt(e.target.value)}
            placeholder="recipient@example.com"
          />
        </div>
        <div className="form-group">
          <label>Subject</label>
          <input
            className="form-control"
            type="text"
            value={subject}
            onChange={e => setSubject(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Body</label>
          <textarea
            className="form-control"
            rows={6}
            value={body}
            onChange={e => setBody(e.target.value)}
          />
        </div>
        {status && <div className={`alert alert-${status.type}`}>{status.msg}</div>}
        <button className="btn btn-primary" type="submit" disabled={loading || !rcpt || !subject || !body}>
          {loading ? 'Sending...' : 'Send Email'}
        </button>
      </form>
    </Layout>
  )
}
