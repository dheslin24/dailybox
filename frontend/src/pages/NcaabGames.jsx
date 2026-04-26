import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function NcaabGames() {
  const [events, setEvents] = useState(null)

  useEffect(() => {
    fetch('/api/ncaab_games')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setEvents(d.events) })
  }, [])

  if (!events) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>NCAAB Games</p></h1>
      <table align="center" cellPadding="10">
        <thead>
          <tr><th>Game</th><th>Date</th><th>Team</th><th>Score</th></tr>
        </thead>
        <tbody>
          {events.map(e => (
            e.competitors.map((c, i) => (
              <tr key={`${e.id}-${i}`}>
                {i === 0 && <td rowSpan={e.competitors.length}>{e.name}</td>}
                {i === 0 && <td rowSpan={e.competitors.length}>{e.date}</td>}
                <td>{c.abbr}</td>
                <td>{c.score}</td>
              </tr>
            ))
          ))}
        </tbody>
      </table>
    </Layout>
  )
}
