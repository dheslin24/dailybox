import { useState } from 'react'
import Layout from '../components/Layout'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
      .then(res => res.json())
      .then(d => {
        setLoading(false)
        if (d.success) {
          window.location.href = '/app/landing_page'
        } else {
          setError(d.error || 'Login failed')
        }
      })
      .catch(() => { setLoading(false); setError('Network error') })
  }

  return (
    <Layout>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <div className="form-group">
            <input
              autoComplete="off"
              autoFocus
              className="form-control"
              placeholder="Username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
            />
          </div>
          <div className="form-group">
            <input
              className="form-control"
              placeholder="Password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <button className="btn btn-default" type="submit" disabled={loading}>
              {loading ? 'Logging in...' : 'Log In'}
            </button>
          </div>
        </fieldset>
      </form>

      <p>
        <h3>
          Gobbler, Nutcracker, Every Score pools, playoff pickem, you name it...<br />
          Brought to you by BYGaming...
        </h3>
      </p>
      <img src="https://64.media.tumblr.com/4009e5a651f408dd772d3a959e34bb47/tumblr_mjvtz65CL61s8s5dto1_500.jpg" alt="" />
    </Layout>
  )
}
