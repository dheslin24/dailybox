import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function CompletedPrivateGames() {
  const [games, setGames] = useState(null)

  useEffect(() => {
    fetch('/api/completed_private_games')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setGames(d.games) })
  }, [])

  if (!games) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>Completed Games</p></h1>
      <h4>
        <table align="center" cellPadding="10">
          <thead>
            <tr>
              <th>Game ID</th>
              <th>Box Name</th>
              <th>Entry Fee</th>
              <th>Payout Type</th>
              <th>Winner</th>
            </tr>
          </thead>
          <tbody>
            {games.map(g => (
              <tr key={g.boxid}>
                <td className="team" style={{ cursor: 'pointer' }} onClick={() => { window.location.href = `/display_box?boxid=${g.boxid}` }}>{g.boxid}</td>
                <td>{g.box_name}</td>
                <td>{g.fee}</td>
                <td>{g.pay_type}</td>
                <td>{g.winner}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </h4>
    </Layout>
  )
}
