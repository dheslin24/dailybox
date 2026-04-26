import { useState, useEffect, useRef } from 'react'
import Layout from '../components/Layout'

const HCAPTCHA_SITE_KEY = '91f9316f-66bc-4bfa-8a88-8b8a05ac22e8'

export default function Register() {
  const [form, setForm] = useState({
    username: '', password: '', password_confirm: '',
    email: '', first_name: '', last_name: '', mobile: '',
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const widgetIdRef = useRef(null)

  useEffect(() => {
    if (document.getElementById('hcaptcha-script')) return
    const script = document.createElement('script')
    script.id = 'hcaptcha-script'
    script.src = 'https://js.hcaptcha.com/1/api.js'
    script.async = true
    script.defer = true
    document.head.appendChild(script)

    script.onload = () => {
      if (window.hcaptcha && widgetIdRef.current === null) {
        widgetIdRef.current = window.hcaptcha.render('hcaptcha-widget', {
          sitekey: HCAPTCHA_SITE_KEY,
        })
      }
    }
  }, [])

  const set = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    setError(null)

    const captcha_token = window.hcaptcha?.getResponse(widgetIdRef.current) || ''
    if (!captcha_token) {
      setError('Please complete the captcha')
      return
    }

    setLoading(true)
    fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, captcha_token }),
    })
      .then(res => res.json())
      .then(d => {
        setLoading(false)
        if (d.success) {
          window.location.href = '/app/landing_page'
        } else {
          setError(d.error || 'Registration failed')
          window.hcaptcha?.reset(widgetIdRef.current)
        }
      })
      .catch(() => { setLoading(false); setError('Network error') })
  }

  return (
    <Layout>
      <form onSubmit={handleSubmit} id="registerForm">
        <fieldset>
          <div className="form-group">
            <input autoComplete="off" autoFocus className="form-control" placeholder="Username" type="text" value={form.username} onChange={set('username')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="Password" type="password" value={form.password} onChange={set('password')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="Confirm Password" type="password" value={form.password_confirm} onChange={set('password_confirm')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="Email" type="text" value={form.email} onChange={set('email')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="First Name" type="text" value={form.first_name} onChange={set('first_name')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="Last Name" type="text" value={form.last_name} onChange={set('last_name')} />
          </div>
          <div className="form-group">
            <input className="form-control" placeholder="Mobile Number" type="text" value={form.mobile} onChange={set('mobile')} />
          </div>

          <div id="hcaptcha-widget" style={{ marginBottom: 12 }}></div>

          {error && <div className="alert alert-danger">{error}</div>}
          <div className="form-group">
            <button className="btn btn-default" type="submit" disabled={loading}>
              {loading ? 'Registering...' : 'Register'}
            </button>
          </div>
        </fieldset>
      </form>
      <div style={{ float: 'right' }}>
        This site is protected by hCaptcha and its{' '}
        <a href="https://hcaptcha.com/privacy">Privacy Policy</a> and{' '}
        <a href="https://hcaptcha.com/terms">Terms of Service</a> apply.
      </div>
    </Layout>
  )
}
