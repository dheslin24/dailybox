import { useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function SvCreatePool() {
  const session = useSession()
  const [poolName, setPoolName] = useState('')
  const [poolPassword, setPoolPassword] = useState('')
  const [result, setResult] = useState(null)

  if (session && session.is_admin !== 1) {
    window.location.href = '/survivor_pool'
    return null
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/sv_create_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_name: poolName, pool_password: poolPassword }),
    })
      .then(res => res.json())
      .then(setResult)
  }

  return (
    <Layout>
      <div style={{maxWidth:'500px', margin:'80px auto', background:'#fff', padding:'32px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.08)', textAlign:'center'}}>
        <h1>Create a New Survivor Pool</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Pool Name</label>
            <input type="text" className="form-control" value={poolName} onChange={e => setPoolName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Pool Password</label>
            <input type="password" className="form-control" value={poolPassword} onChange={e => setPoolPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary">Create Pool</button>
        </form>
        {result?.error && <p style={{color:'#c00', marginTop:'12px'}}>{result.error}</p>}
        {result?.success && (
          <div style={{color:'#080', marginTop:'12px'}}>
            <p>Pool "{result.pool_name}" created successfully.</p>
            <p>Pool ID: {result.pool_id}</p>
          </div>
        )}
      </div>
    </Layout>
  )
}
