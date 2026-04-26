import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function LiveScores() {
  const [data, setData] = useState(null)
  const [picks, setPicks] = useState({})
  const [submitted, setSubmitted] = useState(false)

  const load = () => {
    fetch('/api/live_scores')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => {
        if (d) {
          setData(d)
          setPicks(d.picks || {})
        }
      })
  }

  useEffect(load, [])

  const handleTeamClick = (espnId, abbr, locked) => {
    if (locked) { alert('Too late - game is locked'); return }
    setPicks(prev => ({ ...prev, [String(espnId)]: abbr.toUpperCase() }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/select_bowl_games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ picks }),
    })
      .then(res => res.json())
      .then(d => { if (d.success) { setSubmitted(true); window.location.href = '/app/view_all_picks' } })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>
  if (submitted) return <Layout><p>Picks submitted!</p></Layout>

  const { games } = data
  const now = new Date(data.now)

  return (
    <Layout>
      <h1><p>Live Scores</p></h1>
      <a href="/app/live_scores" onClick={e => { e.preventDefault(); load() }}>Refresh</a>
      <br />
      <h4>
        <form onSubmit={handleSubmit}>
          <input className="pick" type="submit" value="Submit Picks" />
          <table align="center" cellPadding="10">
            <thead>
              <tr><th>Game</th><th>H/A</th><th>Team</th><th>Score</th><th>Pick</th></tr>
            </thead>
            <tbody>
              {Object.entries(games).map(([gid, g]) => {
                const locked = new Date(g.datetime) <= now
                const espnId = String(g.espn_id)
                const userPick = picks[espnId] || 'TBD'
                const rows = []

                if (g.headline) {
                  rows.push(<tr key={`h-${gid}`}><td colSpan={5} className="headline" style={{ fontWeight: 'bold', fontSize: 'large' }}>{g.headline}</td></tr>)
                }
                rows.push(<tr key={`d-${gid}`}><td colSpan={5} className="headline">{g.date}</td></tr>)

                g.competitors.forEach(([homeAway, name, score], i) => {
                  const abbr = g.abbreviations[homeAway]
                  if (!locked) {
                    rows.push(
                      <tr key={`${gid}-${i}`}>
                        {i === 0 && <td rowSpan={2} className="ptd" style={{ width: '60px' }}>{gid}</td>}
                        <td className="ptd" style={{ width: '60px' }}>{homeAway}</td>
                        <td className="team" style={{ width: '250px', textAlign: 'left', cursor: 'pointer' }} onClick={() => handleTeamClick(g.espn_id, abbr, false)}>{name}</td>
                        <td className="ptd" style={{ width: '60px' }}>{score}</td>
                        {i === 0 && <td rowSpan={2} className="pick"><input className="pick" type="text" readOnly value={userPick} style={{ width: '60px' }} /></td>}
                      </tr>
                    )
                  } else {
                    rows.push(
                      <tr key={`${gid}-${i}`}>
                        {i === 0 && <td rowSpan={2} className="locked_ptd" style={{ width: '60px' }}>{gid}</td>}
                        <td className="locked_ptd" style={{ width: '60px' }}>{homeAway}</td>
                        <td className="locked_team" style={{ width: '200px', textAlign: 'left' }}>{name}</td>
                        <td className="locked_ptd" style={{ width: '60px' }}>{score}</td>
                        {i === 0 && <td rowSpan={2} className="pick">{userPick}</td>}
                      </tr>
                    )
                  }
                })
                rows.push(<tr key={`sep-${gid}`}><td colSpan={5} style={{ backgroundColor: 'black' }}></td></tr>)
                return rows
              })}
            </tbody>
          </table>
          <input className="pick" type="submit" value="Submit Picks" />
        </form>
      </h4>
    </Layout>
  )
}
