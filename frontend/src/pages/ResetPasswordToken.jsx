import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

export default function ResetPasswordToken() {
  const token = new URLSearchParams(window.location.search).get('token') || ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  if (!token) {
    return (
      <Layout>
        <div className="alert alert-danger">Invalid or missing reset token. <a href="/app/forgot_password">Request a new one.</a></div>
      </Layout>
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    setError(null)
    setLoading(true)
    fetch('/api/reset_password_token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    })
      .then(res => res.json())
      .then(d => {
        setLoading(false)
        if (d.ok) navigate('/login')
        else setError(d.error || 'Something went wrong')
      })
      .catch(() => { setLoading(false); setError('Network error') })
  }

  return (
    <Layout>
      <h2>Set New Password</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <input
            autoFocus
            className="form-control"
            placeholder="New password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
        </div>
        <div className="form-group">
          <input
            className="form-control"
            placeholder="Confirm new password"
            type="password"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
          />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <div className="form-group">
          <button className="btn btn-default" type="submit" disabled={loading || !password || !confirm}>
            {loading ? 'Saving...' : 'Set Password'}
          </button>
        </div>
      </form>
    </Layout>
  )
}
