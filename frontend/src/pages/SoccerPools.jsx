import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { useSession } from '../SessionContext'

export default function SoccerPools() {
  const session = useSession()
  const navigate = useNavigate()
  const [pools, setPools] = useState(null)
  const [joinCode, setJoinCode] = useState('')
  const [joinMsg, setJoinMsg] = useState('')
  const canAdmin = session?.is_admin === 1 || session?.has_soccer_grant || session?.has_soccer_deputy

  const loadPools = () =>
    fetch('/api/soccer_pools').then(r => r.json()).then(setPools)

  useEffect(() => { loadPools() }, [])

  const handleJoin = () => {
    const code = joinCode.trim().toUpperCase()
    if (!code) return
    fetch('/api/soccer_join_pool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invite_code: code }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setJoinMsg(d.error); return }
        setJoinMsg(`Joined "${d.pool_name}"!`)
        setJoinCode('')
        loadPools()
        navigate(`/soccer_pool/${d.pool_id}`)
      })
  }

  return (
    <Layout>
      <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <h2 style={{ margin: 0 }}>⚽ World Cup 2026 Pools</h2>
          {canAdmin && (
            <a href="/app/soccer_admin" className="btn btn-sm btn-primary">Admin</a>
          )}
        </div>

        {/* Join by invite code */}
        <div style={{ background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: 6, padding: 16, marginBottom: 24 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Join a Pool</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="form-control"
              style={{ maxWidth: 160, letterSpacing: 2, textTransform: 'uppercase', fontWeight: 600 }}
              placeholder="Invite code"
              maxLength={8}
              value={joinCode}
              onChange={e => setJoinCode(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && handleJoin()}
            />
            <button className="btn btn-success" onClick={handleJoin}>Join</button>
          </div>
          {joinMsg && <div style={{ marginTop: 8, color: joinMsg.includes('Joined') ? '#15803d' : '#dc2626' }}>{joinMsg}</div>}
        </div>

        {/* Pool list */}
        {pools === null ? (
          <div style={{ color: '#6b7280' }}>Loading...</div>
        ) : pools.length === 0 ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>⚽</div>
            <div>You haven't joined any pools yet.</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>Enter an invite code above to get started.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {pools.map(pool => (
              <a
                key={pool.pool_id}
                href={`/app/soccer_pool/${pool.pool_id}`}
                style={{ textDecoration: 'none' }}
              >
                <div style={{
                  border: '1px solid #dee2e6', borderRadius: 8, padding: '14px 18px',
                  background: '#fff', cursor: 'pointer',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  transition: 'border-color 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = '#3b82f6'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = '#dee2e6'}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 16, color: '#111' }}>{pool.name}</div>
                    {pool.fee && <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>Fee: {pool.fee}</div>}
                    <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                      Points: {pool.pts_group}/{pool.pts_r32}/{pool.pts_r16}/{pool.pts_qf}/{pool.pts_sf}/{pool.pts_final}
                      <span style={{ marginLeft: 6, color: '#9ca3af' }}>(group/R32/R16/QF/SF/Final)</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`label label-${pool.status === 'open' ? 'success' : pool.status === 'active' ? 'primary' : 'default'}`}>
                      {pool.status}
                    </span>
                    <span style={{ color: '#9ca3af', fontSize: 18 }}>›</span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
