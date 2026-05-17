import { useState } from 'react'
import Layout from '../components/Layout'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    fetch('/api/forgot_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
      .then(res => res.json())
      .then(d => {
        setLoading(false)
        if (d.ok) setSent(true)
        else setError(d.error || 'Something went wrong')
      })
      .catch(() => { setLoading(false); setError('Network error') })
  }

  if (sent) {
    return (
      <Layout>
        <h2>Check your email</h2>
        <p>If an account with that address exists, we sent a password reset link. It expires in 1 hour.</p>
        <a href="/app/login">Back to login</a>
      </Layout>
    )
  }

  return (
    <Layout>
      <h2>Forgot Password</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <input
            autoFocus
            className="form-control"
            placeholder="Email address"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <div className="form-group">
          <button className="btn btn-default" type="submit" disabled={loading || !email}>
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>
          {' '}
          <a href="/app/login">Back to login</a>
        </div>
      </form>
    </Layout>
  )
}
