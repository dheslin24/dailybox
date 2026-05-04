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

  const cellBg = (locked) => locked ? '#f3f4f6' : undefined
  const teamStyle = (locked) => ({
    textAlign: 'center',
    backgroundColor: cellBg(locked),
    cursor: locked ? 'default' : 'pointer',
  })
  const plainStyle = (locked) => ({
    textAlign: 'center',
    backgroundColor: cellBg(locked),
  })

  const rows = []
  for (const i of gameIds) {
    const g = games[String(i)]
    if (!g) continue
    const locked = g.locked

    rows.push(
      <tr key={i}>
        <td style={plainStyle(locked)}>{i}</td>
        <td
          style={teamStyle(locked)}
          onClick={() => handleTeamClick(i, g.fav, locked)}
        >
          {g.fav}
        </td>
        <td style={plainStyle(locked)}>{g.spread}</td>
        <td
          style={teamStyle(locked)}
          onClick={() => handleTeamClick(i, g.dog, locked)}
        >
          {g.dog}
        </td>
        <td style={{ textAlign: 'center', borderLeftWidth: 'thick', fontWeight: 600 }}>
          <input
            type="text"
            readOnly
            value={picks[String(i)] || ''}
            style={{ width: 60, textAlign: 'center', fontSize: 16, border: 0, backgroundColor: 'transparent' }}
          />
        </td>
      </tr>
    )

    if (i === 13 && g.spread !== 0) {
      rows.push(
        <tr key="tb">
          <td colSpan={4} style={{ textAlign: 'right', backgroundColor: cellBg(locked) }}>
            Enter Superbowl Total Points Tie Breaker Here:
          </td>
          <td style={{ textAlign: 'center', borderLeftWidth: 'thick', fontWeight: 600 }}>
            <input
              type="text"
              value={picks['tb'] || ''}
              onChange={e => setPicks(prev => ({ ...prev, tb: e.target.value }))}
              readOnly={!!locked}
              style={{ width: 60, textAlign: 'center', fontSize: 16, border: 0, backgroundColor: locked ? '#f3f4f6' : 'transparent' }}
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
          <table className="table table-bordered table-condensed table-striped table-hover" style={{ width: 'auto', margin: '0 auto' }}>
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
