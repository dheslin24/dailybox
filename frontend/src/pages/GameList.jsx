import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function GameList() {
  const [games, setGames] = useState(null)

  useEffect(() => {
    fetch('/api/game_list')
      .then(res => res.json())
      .then(d => setGames(d.games))
  }, [])

  if (!games) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>Daily Box Game List</p></h1>
      <h5>
        <p>These games go off with random numbers once all spots are filled</p>
        <p>DAILY BOX is not live yet - but feel free to mess around</p>
      </h5>
      <a href="/app/completed_games">View Completed Games</a><br />
      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>Game ID</th>
            <th>Box Name</th>
            <th>Entry Fee</th>
            <th>Payout Type</th>
            <th>Available Entries</th>
          </tr>
        </thead>
        <tbody>
          {games.map(g => (
            <tr key={g.boxid}>
              <td className="team" onClick={() => window.location.href = `/app/display_box?boxid=${g.boxid}`} style={{cursor:'pointer'}}>{g.boxid}</td>
              <td>{g.box_name}</td>
              <td>{g.fee}</td>
              <td>{g.pay_type}</td>
              <td>{g.available}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  )
}
