import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function PickemGameList() {
  const [data, setData] = useState(null)
  const [picks, setPicks] = useState({})

  useEffect(() => {
    fetch('/api/pickem_game_list')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => {
        if (d) {
          setData(d)
          setPicks(d.user_picks || {})
        }
      })
  }, [])

  const handleTeamClick = (gameId, team, locked) => {
    if (locked) {
      alert('Too late - game is locked')
      return
    }
    setPicks(prev => ({ ...prev, [String(gameId)]: team.toUpperCase() }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/select_pickem_games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(picks),
    })
      .then(res => res.json())
      .then(d => {
        if (d.success) window.location.href = '/app/pickem_all_picks'
      })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const { games } = data
  const gameIds = Object.keys(games).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b)

  const rows = []
  for (const i of gameIds) {
    const g = games[String(i)]
    if (!g) continue
    const locked = g.locked
    const tdClass = locked ? 'locked_ptd' : 'ptd'
    const teamClass = locked ? 'locked_team' : 'team'

    rows.push(
      <tr key={i}>
        <td className={tdClass} style={{ textAlign: 'center' }}>{i}</td>
        <td
          className={teamClass}
          onClick={() => handleTeamClick(i, g.fav, locked)}
          style={{ textAlign: 'center', cursor: locked ? 'default' : 'pointer' }}
        >
          {g.fav}
        </td>
        <td className={tdClass} style={{ textAlign: 'center' }}>{g.spread}</td>
        <td
          className={teamClass}
          onClick={() => handleTeamClick(i, g.dog, locked)}
          style={{ textAlign: 'center', cursor: locked ? 'default' : 'pointer' }}
        >
          {g.dog}
        </td>
        <td className="pick" style={{ textAlign: 'center' }}>
          <input className="pick" type="text" readOnly value={picks[String(i)] || ''} />
        </td>
      </tr>
    )

    if (i === 13 && g.spread !== 0) {
      rows.push(
        <tr key="tb">
          <td className={tdClass} colSpan={4} style={{ textAlign: 'right' }}>
            Enter Superbowl Total Points Tie Breaker Here:
          </td>
          <td className="pick" style={{ textAlign: 'center' }}>
            <input
              className="pick"
              type="text"
              value={picks['tb'] || ''}
              onChange={e => setPicks(prev => ({ ...prev, tb: e.target.value }))}
              readOnly={!!locked}
              style={{ backgroundColor: locked ? '#ccc' : 'white' }}
            />
          </td>
        </tr>
      )
    }
  }

  return (
    <Layout>
      <h1>Playoff Pickem Pool</h1>
      <p>
        Pick all 13 playoff games against the spread. Best record wins.<br />
        Click on a team name to select your pick.<br />
        Final spreads will use Friday's NY Post.
      </p>
      <p>
        <a target="_blank" rel="noopener noreferrer" href="https://nypost.com/odds/">
          Link to NY Post Odds
        </a>
      </p>

      <form onSubmit={handleSubmit}>
        <div style={{ overflowX: 'auto' }}>
          <table className="table table-bordered table-condensed" style={{ width: 'auto', margin: '0 auto' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'center' }}>Game</th>
                <th style={{ textAlign: 'center' }}>Favorite</th>
                <th style={{ textAlign: 'center' }}>Spread</th>
                <th style={{ textAlign: 'center' }}>Underdog</th>
                <th style={{ textAlign: 'center', borderLeftWidth: 'thick' }}>Pick</th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <input className="pick" type="submit" value="Submit Picks" />
        </div>
      </form>

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <img src="https://www.wmse.org/wp-content/uploads/2017/12/ralph.gif" alt="" />
      </div>
    </Layout>
  )
}
