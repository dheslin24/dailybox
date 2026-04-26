import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

function SurvivorNav({ poolId, season, session }) {
  return (
    <div style={{ marginBottom: '20px', fontSize: '0.95em' }}>
      <a href="/app/survivor_pool">Main Survivor Page</a>
      {poolId && <> | <a href={`/app/survivor_pool_picks?pool_id=${poolId}&season=${season}`}>View All Pool Picks</a></>}
      {session?.is_admin === 1 && <> | <a href="/app/sv_create_pool">Create Survivor Pool</a></>}
    </div>
  )
}

export default function SurvivorPoolPicks() {
  const [searchParams] = useSearchParams()
  const session = useSession()
  const poolId = searchParams.get('pool_id')
  const season = searchParams.get('season') || '2025'
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!poolId) return
    fetch(`/api/survivor_pool_picks?pool_id=${poolId}&season=${season}`)
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [poolId, season])

  if (!poolId) return <Layout><p>Missing pool_id parameter.</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  const { users, weeks, picks, current_userid } = data

  const cellStyle = (result) => {
    if (result === 'win') return { background: '#d4f8d4', padding: '10px', borderBottom: '1px solid #eee' }
    if (result === 'lose') return { background: '#f8d4d4', padding: '10px', borderBottom: '1px solid #eee' }
    return { padding: '10px', borderBottom: '1px solid #eee' }
  }

  return (
    <Layout>
      <SurvivorNav poolId={poolId} season={season} session={session} />
      <div style={{ maxWidth: '900px', margin: '40px auto', background: '#fff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h2>Survivor Pool Picks</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '18px' }}>
          <thead>
            <tr>
              <th style={{ padding: '10px', borderBottom: '1px solid #eee', background: '#f0f0f0', textAlign: 'left' }}>User</th>
              {weeks.map(w => (
                <th key={w} style={{ padding: '10px', borderBottom: '1px solid #eee', background: '#f0f0f0', textAlign: 'left' }}>Week {w}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.user_id} style={user.user_id === current_userid ? { background: '#e6f7ff' } : {}}>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{user.username}</td>
                {weeks.map(w => {
                  const key = `${user.user_id}_${w}`
                  const pick = picks[key]
                  const showPick = user.user_id === current_userid || (pick && pick.locked)
                  return (
                    <td key={w} style={cellStyle(pick?.result)}>
                      {showPick && pick?.logo
                        ? <img src={pick.logo} alt={`${pick.team} logo`} style={{ height: '32px', verticalAlign: 'middle' }} />
                        : showPick && pick ? pick.team
                        : !showPick && pick ? <span style={{ color: '#aaa' }}>Locked</span>
                        : null
                      }
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
