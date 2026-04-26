import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function DisplayPickemGames() {
  const [data, setData] = useState(null)
  const [picks, setPicks] = useState({})
  const [tiebreak, setTiebreak] = useState('')
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    fetch('/api/display_pickem_games')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => {
        if (d) {
          setData(d)
          setPicks(d.picks || {})
          setTiebreak(d.tiebreak || '')
        }
      })
  }, [])

  const handleTeamClick = (espnId, abbr, locked) => {
    if (locked) { alert('Too late - game is locked'); return }
    setPicks(prev => ({ ...prev, [String(espnId)]: abbr.toUpperCase() }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/select_bowl_games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ picks, tiebreak }),
    })
      .then(res => res.json())
      .then(d => { if (d.success) { setSubmitted(true); window.location.href = '/view_all_picks' } })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>
  if (submitted) return <Layout><p>Picks submitted!</p></Layout>

  const { games } = data
  const now = new Date(data.now)
  const SUPERBOWL_ID = 401772988

  return (
    <Layout>
      <h1><p>Playoff Games</p></h1>
      <p>Click team name to select. Be sure to click submit when done.</p>
      <h4>
        <form onSubmit={handleSubmit}>
          <input className="pick" type="submit" value="Submit Picks" /><br />
          <img src="https://www.wmse.org/wp-content/uploads/2017/12/ralph.gif" alt="" /><br />
          <table align="center" cellPadding="10">
            <thead>
              <tr>
                <th>Line</th><th>Team</th><th>Score</th><th>Pick</th><th>W/L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(games).map(([gid, g]) => {
                const locked = new Date(g.datetime) <= now
                const espnId = String(g.espn_id)
                const userPick = picks[espnId] || 'TBD'
                const status = g.status?.status || ''
                const isCxl = status === 'Canceled'
                const isPpd = status === 'Postponed'

                const rows = []

                if (g.headline) {
                  rows.push(<tr key={`h-${gid}`}><td colSpan={5} className="headline" style={{ borderBottomColor: '#B5C9B5', fontWeight: 'bold', fontSize: 'large' }}>{g.headline}</td></tr>)
                }
                if (g.venue) {
                  rows.push(<tr key={`v-${gid}`}><td colSpan={5} className="headline">{g.venue} {g.location}</td></tr>)
                }
                if (isCxl) {
                  rows.push(<tr key={`d-${gid}`}><td colSpan={5} className="headline">{g.espn_id} - Canceled</td></tr>)
                } else if (locked && status !== 'Final') {
                  rows.push(<tr key={`d-${gid}`}><td colSpan={5} className="headline">{g.date} -- {g.status?.detail || status}</td></tr>)
                } else {
                  rows.push(<tr key={`d-${gid}`}><td colSpan={5} className="headline">{g.date}{status === 'Final' ? ' -- Final' : ''}</td></tr>)
                }

                const teamsReversed = [...g.competitors].reverse()
                teamsReversed.forEach(([homeAway, name, score], i) => {
                  const abbr = g.abbreviations[homeAway]
                  const isFav = Array.isArray(g.line) && g.line[0] === abbr
                  const isEven = Array.isArray(g.line) && g.line[0] === 'EVEN'
                  const lineDisplay = isFav ? g.line[1] : isEven ? 'EVEN' : ''

                  let wl = ''
                  if (!isCxl && !isPpd && locked) {
                    if (status !== 'Final') {
                      wl = g.current_winner === userPick ? 'Winning' : g.current_winner === 'PUSH' ? 'Pushing' : 'Losing'
                    } else {
                      wl = g.current_winner === userPick ? 'Win' : g.current_winner === 'PUSH' ? 'Push' : 'Loss'
                    }
                  }

                  if (!locked) {
                    rows.push(
                      <tr key={`${gid}-${i}`}>
                        <td className="ptd" style={{ width: '60px' }}>{lineDisplay}</td>
                        <td className="team" style={{ width: '250px', textAlign: 'left', cursor: 'pointer' }} onClick={() => handleTeamClick(g.espn_id, abbr, false)}>{name}</td>
                        <td className="ptd" style={{ width: '60px' }}>{score}</td>
                        {i === 0 && <td rowSpan={2} className="pick"><input className="pick" type="text" readOnly value={userPick} style={{ width: '60px' }} /></td>}
                        {i === 0 && <td rowSpan={2} className="pick"></td>}
                      </tr>
                    )
                  } else {
                    rows.push(
                      <tr key={`${gid}-${i}`}>
                        <td className="locked_ptd" style={{ width: '60px' }}>{lineDisplay}</td>
                        <td className="locked_team" style={{ width: '200px', textAlign: 'left' }}>{name}</td>
                        <td className="locked_ptd" style={{ width: '60px' }}>{score}</td>
                        {i === 0 && <td rowSpan={2} className="pick">{isCxl ? "CXL'd" : isPpd ? "PPD" : userPick}</td>}
                        {i === 0 && <td rowSpan={2} className="pick">{wl}</td>}
                      </tr>
                    )
                  }
                })

                rows.push(<tr key={`sep-${gid}`}><td colSpan={5} style={{ backgroundColor: 'black' }}></td></tr>)
                return rows
              })}

              {String(SUPERBOWL_ID) in games && (() => {
                const sbGame = games[String(SUPERBOWL_ID)]
                const sbLocked = new Date(sbGame.datetime) <= now
                return (
                  <tr key="tb">
                    <td colSpan={4} className="pick">Tie Breaker: Superbowl Overall Score</td>
                    <td>
                      <input className="pick" type="text" value={tiebreak} onChange={e => setTiebreak(e.target.value)}
                        readOnly={sbLocked} style={{ backgroundColor: 'white', width: '30px' }} />
                    </td>
                  </tr>
                )
              })()}
            </tbody>
          </table>
          <input className="pick" type="submit" value="Submit Picks" />
        </form>
      </h4>
    </Layout>
  )
}
