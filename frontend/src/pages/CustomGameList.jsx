import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function CustomGameList() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/api/custom_game_list')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>Super Bowl Boxes</p></h1>
      Click on game ID in green to join<br />
      <a href="/app/completed_games">View Completed Games</a><br />
      {data.no_active_games_string && <h1>{data.no_active_games_string}</h1>}
      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>Game ID</th><th>Box Name</th><th>Entry Fee</th><th>Payout Type</th><th>Available Entries</th>
          </tr>
        </thead>
        <tbody>
          {data.games.map(g => (
            <tr key={g.boxid}>
              <td className="team" style={{cursor:'pointer'}} onClick={() => window.location.href = `/app/display_box?boxid=${g.boxid}`}>{g.boxid}</td>
              <td>{g.box_name}</td><td>{g.fee}</td><td>{g.pay_type}</td><td>{g.available}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  )
}
