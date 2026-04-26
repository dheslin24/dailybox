import { useState } from 'react'
import Layout from '../components/Layout'

export default function PrivatePswd() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/private_pswd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
      .then(res => res.json())
      .then(d => {
        if (d.success) {
          window.location.href = '/app/private_game_list'
        } else {
          setError(d.error)
        }
      })
  }

  return (
    <Layout>
      <h2><p style={{color:'maroon'}}>{error}</p></h2>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <div className="form-group">
            <input className="form-control" placeholder="Enter Code for Pool" type="password"
              value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <div className="form-group">
            <button className="btn btn-default" type="submit">Submit</button>
          </div>
        </fieldset>
      </form>
      <h4>
        <p>You will only need to do this once. Once you have successfully registered for a pool,</p>
        <p>they will be available to you via the 'Access Existing Private Pools' link.</p>
        <img src="https://i.ytimg.com/vi/W7rSYzbpA8k/hqdefault.jpg" alt="" />
        <br /><br />
        <p>Don't have a code and want to create your own pool?</p>
        <p>If you don't know TW or DH, not likely (at least this year)..</p>
        <p>But if not... reach out and be a beta tester... will talk</p>
      </h4>
    </Layout>
  )
}
