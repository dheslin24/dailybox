import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
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

export default function SurvivorWeekDisplay() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const session = useSession()
  const week = searchParams.get('week') || '1'
  const season = searchParams.get('season') || '2025'
  const poolId = searchParams.get('pool_id')

  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch(`/api/survivor_week_display?week=${week}&season=${season}&pool_id=${poolId}`)
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [week, season, poolId])

  const handleTeamClick = (team, logo, locked) => {
    if (locked) return
    setSelected({ team, logo })
    setError(null)
  }

  const handleSubmit = () => {
    setSubmitting(true)
    fetch('/api/submit_team', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team: selected.team, logo: selected.logo, week, pool_id: poolId, season }),
    })
      .then(res => res.json())
      .then(d => {
        setSubmitting(false)
        if (d.success) navigate(`/survivor_teams_selected?pool_id=${poolId}&season=${season}`)
        else setError(d.error)
      })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const { games, used_teams } = data

  const teamButton = (team, logo, locked) => {
    const usedWeek = used_teams[team]
    const isDisabled = locked || !!usedWeek
    const color = isDisabled ? '#aaa' : '#007bff'
    return (
      <button
        onClick={() => !isDisabled && handleTeamClick(team, logo, locked)}
        disabled={isDisabled}
        style={{ background: 'none', border: 'none', padding: 0, color, cursor: isDisabled ? 'not-allowed' : 'pointer', textDecoration: isDisabled ? 'none' : 'underline', verticalAlign: 'middle', fontSize: 'inherit' }}
      >
        {logo && <img src={logo} alt={`${team} logo`} style={{ height: '32px', verticalAlign: 'middle', marginRight: '8px' }} />}
        {team}
        {usedWeek && <span style={{ color: '#aaa', marginLeft: '10px', fontSize: '0.98em' }}>Used week {usedWeek}</span>}
        {!usedWeek && locked && <span style={{ color: '#aaa', marginLeft: '10px', fontSize: '0.98em' }}>Locked</span>}
      </button>
    )
  }

  return (
    <Layout>
      <SurvivorNav poolId={poolId} season={season} session={session} />

      {selected && (
        <div style={{ position: 'absolute', top: '32px', right: '48px', background: '#fff', padding: '18px 32px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.10)', textAlign: 'center', zIndex: 100 }}>
          <div style={{ fontSize: '1.2em', fontWeight: 'bold', marginBottom: '10px' }}>Team selected for week {week}</div>
          <div>{selected.team}</div>
          {selected.logo && <img src={selected.logo} alt={`${selected.team} logo`} style={{ height: '80px', marginTop: '8px' }} />}
          {error && <p style={{ color: 'red', marginTop: '8px' }}>{error}</p>}
          <div style={{ marginTop: '12px' }}>
            <button onClick={handleSubmit} disabled={submitting} style={{ padding: '8px 18px', fontSize: '1em', marginRight: '8px' }}>Submit</button>
            <button onClick={() => setSelected(null)} style={{ padding: '8px 18px', fontSize: '1em', background: '#eee', color: '#333', border: '1px solid #ccc' }}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ maxWidth: '800px', margin: '0 auto', background: '#fff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h2>Survivor Week Games</h2>
        {games && games.length > 0 ? games.map((game, idx) => (
          <div key={idx} style={{ borderBottom: '1px solid #eee', padding: '16px 0' }}>
            <div style={{ marginBottom: '6px', color: '#555' }}>{game.display_datetime}</div>
            <div style={{ marginBottom: '6px' }}>
              <strong>Home:</strong> {teamButton(game.home_team, game.home_logo, game.locked)}
            </div>
            <div style={{ marginBottom: '6px' }}>
              <strong>Away:</strong> {teamButton(game.away_team, game.away_logo, game.locked)}
            </div>
            <div style={{ color: '#555' }}><strong>Line:</strong> {game.odds_details}</div>
          </div>
        )) : <p>No games found for this week.</p>}
      </div>
    </Layout>
  )
}
