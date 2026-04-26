import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

function SurvivorNav({ poolId, session }) {
  return (
    <div style={{ marginBottom: '20px', fontSize: '0.95em' }}>
      <a href="/app/survivor_pool">Main Survivor Page</a>
      {poolId && <> | <a href={`/app/survivor_pool_picks?pool_id=${poolId}`}>View All Pool Picks</a></>}
      {session?.is_admin === 1 && <> | <a href="/app/sv_create_pool">Create Survivor Pool</a></>}
    </div>
  )
}

export default function SurvivorTeamsSelected() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const poolId = searchParams.get('pool_id')
  const season = searchParams.get('season') || '2025'

  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!poolId) return
    fetch(`/api/survivor_teams_selected?pool_id=${poolId}&season=${season}`)
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [poolId, season])

  if (!poolId) return <Layout><p>Missing pool_id parameter.</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <SurvivorNav poolId={poolId} />
      <div style={{ maxWidth: '600px', margin: '0 auto', background: '#fff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h2 style={{ textAlign: 'center' }}>Survivor Picks</h2>
        {data.pool_name && <div style={{ textAlign: 'center', fontSize: '1.1em', marginBottom: '12px', color: '#333', fontWeight: 'bold' }}>{data.pool_name}</div>}
        {error && <div style={{ color: '#c00', textAlign: 'center', marginBottom: '12px' }}>{error}</div>}
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '18px' }}>
          <thead>
            <tr><th style={{ padding: '10px', borderBottom: '1px solid #eee', background: '#f0f0f0', textAlign: 'left' }}>Week</th><th style={{ padding: '10px', borderBottom: '1px solid #eee', background: '#f0f0f0', textAlign: 'left' }}>Pick</th><th></th></tr>
          </thead>
          <tbody>
            {Array.from({ length: 18 }, (_, i) => i + 1).map(week => {
              const pick = data.picks.find(p => p.week === week)
              return (
                <tr key={week}>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee', fontSize: '1.2em' }}>{week}</td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee', fontSize: '1.4em', fontWeight: 'bold' }}>
                    {pick ? (
                      <>
                        {pick.team}
                        {pick.logo && <img src={pick.logo} alt={`${pick.team} logo`} style={{ height: '70px', verticalAlign: 'middle', marginLeft: '16px' }} />}
                      </>
                    ) : (
                      <button onClick={() => navigate(`/survivor_week_display?week=${week}&pool_id=${poolId}&season=${season}`)} style={{ padding: '6px 16px', fontSize: '1em' }}>
                        Pick for Week {week}
                      </button>
                    )}
                  </td>
                  <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                    {pick && (
                      <button
                        onClick={() => navigate(`/survivor_week_display?week=${week}&pool_id=${poolId}&season=${season}`)}
                        disabled={pick.locked}
                        style={{ padding: '6px 16px', fontSize: '1em', ...(pick.locked ? { background: '#eee', color: '#aaa', cursor: 'not-allowed' } : {}) }}
                      >
                        Change Pick
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
