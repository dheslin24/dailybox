import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

const RANGES = [[1, 6], [7, 10], [11, 12], [13, 13]]

export default function PickemGameList() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [picks, setPicks] = useState({})
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    fetch('/api/pickem_game_list')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
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
        if (d.success) {
          setSubmitted(true)
          window.location.href = '/pickem_all_picks'
        }
      })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const { games } = data

  const renderRows = (start, end) => {
    const rows = []
    for (let i = start; i <= end; i++) {
      const g = games[String(i)]
      if (!g) continue
      const locked = g.locked
      const tdClass = locked ? 'locked_ptd' : 'ptd'
      const teamClass = locked ? 'locked_team' : 'team'
      const isSuperbowl = i === 13
      const spread = isSuperbowl ? games['13']?.spread : g.spread

      rows.push(
        <tr key={i}>
          <td className={tdClass}>{i}</td>
          <td className={teamClass} onClick={() => handleTeamClick(i, g.fav, locked)} style={{ cursor: 'pointer' }}>{g.fav}</td>
          <td className={tdClass}>{spread}</td>
          <td className={teamClass} onClick={() => handleTeamClick(i, g.dog, locked)} style={{ cursor: 'pointer' }}>{g.dog}</td>
          <td className="pick">
            <input className="pick" type="text" readOnly value={picks[String(i)] || ''} style={{ width: '80px' }} />
          </td>
        </tr>
      )

      if (i === 13 && g.spread !== 0) {
        rows.push(
          <tr key="tb">
            <td className={tdClass} colSpan={4} style={{ textAlign: 'right' }}>
              Enter Superbowl Total Points Tie Breaker Here:
            </td>
            <td className="pick">
              <input
                className="pick"
                type="text"
                value={picks['tb'] || ''}
                onChange={e => setPicks(prev => ({ ...prev, tb: e.target.value }))}
                readOnly={!!locked}
                style={{ backgroundColor: 'white', width: '80px' }}
              />
            </td>
          </tr>
        )
      }
    }
    return rows
  }

  const isFirstRoundLocked = games['1'] && games['1'].locked && games['1'].fav === 'TBD'

  return (
    <Layout>
      <h1>
        <p>Playoff Pickem Pool</p>
      </h1>
      Pick all 13 playoff games against the spread.<br />
      Best record wins. Click on team in table to select.<br />
      Final spreads will use Friday's NY Post.
      <br /><br />
      <a target="_blank" rel="noopener noreferrer" href="https://nypost.com/odds/">Link to NY POST Odds</a>

      <h4>
        <form onSubmit={handleSubmit}>
          {RANGES.map(([start, end]) => (
            <table key={start} align="center">
              {start === 1 && (
                <thead>
                  <tr>
                    <th>Game ID</th>
                    <th>Fav</th>
                    <th>Spread</th>
                    <th>Dog</th>
                    <th style={{ borderLeftWidth: 'thick' }}>Pick</th>
                  </tr>
                </thead>
              )}
              <tbody>
                {renderRows(start, end)}
              </tbody>
            </table>
          ))}
          <input className="pick" type="submit" value="Submit Picks" />
        </form>
      </h4>

      <img src="https://www.wmse.org/wp-content/uploads/2017/12/ralph.gif" alt="" />
    </Layout>
  )
}
