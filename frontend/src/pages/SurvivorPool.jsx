import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function SurvivorPool() {
  const session = useSession()
  const navigate = useNavigate()
  const [userPools, setUserPools] = useState(null)
  const [form, setForm] = useState({ pool_id: '', pool_name: '', pool_password: '' })
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/survivor_pool')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setUserPools(d.user_pools) })
  }, [])

  const set = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }))

  const handleJoin = (e) => {
    e.preventDefault()
    setError(null)
    fetch('/api/join_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
      .then(res => res.json())
      .then(d => {
        if (d.success) navigate(`/survivor_teams_selected?pool_id=${d.pool_id}`)
        else setError(d.error)
      })
  }

  return (
    <Layout>
      <div style={{ maxWidth: '600px', margin: '80px auto', background: '#fff', padding: '40px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', textAlign: 'center' }}>
        <h1>Survivor Pool</h1>
        <form onSubmit={handleJoin}>
          <div style={{ fontSize: '1.3em', color: '#888', marginTop: '24px' }}>Enter pool ID or pool name to join</div>
          <div style={{ marginTop: '24px' }}>
            <input type="text" placeholder="Pool ID" style={{ width: '80%', padding: '10px', marginBottom: '12px', fontSize: '1em' }} value={form.pool_id} onChange={set('pool_id')} />
          </div>
          <div>
            <input type="text" placeholder="Pool Name" style={{ width: '80%', padding: '10px', marginBottom: '12px', fontSize: '1em' }} value={form.pool_name} onChange={set('pool_name')} />
          </div>
          <div>
            <input type="password" placeholder="Pool Password" style={{ width: '80%', padding: '10px', marginBottom: '18px', fontSize: '1em' }} value={form.pool_password} onChange={set('pool_password')} />
          </div>
          <button type="submit" style={{ padding: '10px 28px', fontSize: '1.1em' }}>Join Pool</button>
        </form>
        {error && <p style={{ color: 'red', marginTop: '12px' }}>{error}</p>}

        {userPools && userPools.length > 0 && (
          <div style={{ marginTop: '32px' }}>
            <h2>Click link to jump to pool you already belong to:</h2>
            <table style={{ width: '100%', marginTop: '16px', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f0f0f0' }}>
                  <th style={{ padding: '8px', border: '1px solid #ddd' }}>Pool Name</th>
                  <th style={{ padding: '8px', border: '1px solid #ddd' }}>Pool ID</th>
                </tr>
              </thead>
              <tbody>
                {userPools.map(p => (
                  <tr key={p.pool_id}>
                    <td style={{ padding: '8px', border: '1px solid #ddd' }}>
                      <a href={`/app/survivor_teams_selected?pool_id=${p.pool_id}`}>{p.pool_name}</a>
                    </td>
                    <td style={{ padding: '8px', border: '1px solid #ddd' }}>
                      <a href={`/app/survivor_teams_selected?pool_id=${p.pool_id}`}>{p.pool_id}</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
