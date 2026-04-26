import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

export default function MyCompletedGames() {
  const navigate = useNavigate()
  const [games, setGames] = useState(null)

  useEffect(() => {
    fetch('/api/my_games')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setGames(d.completed_games) })
  }, [])

  if (!games) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>My Completed Games</p></h1>
      <div style={{ marginBottom: '12px' }}>
        <button onClick={() => navigate('/my_games')} className="btn btn-default">Active</button>
        {' '}
        <button className="btn btn-default" disabled>Complete</button>
      </div>
      <h4>
        <table align="center" cellPadding="10">
          <thead>
            <tr>
              <th>Game ID</th>
              <th>Box Type</th>
              <th>Box Name</th>
              <th>Box Number</th>
              <th>Name Alias</th>
              <th>Entry Fee</th>
              <th>Payout Type</th>
              <th>Winner</th>
            </tr>
          </thead>
          <tbody>
            {games.map((g, i) => (
              <tr key={i}>
                <td>{g.boxid}</td>
                <td>{g.box_type}</td>
                <td>{g.box_name}</td>
                <td>{g.box_num}</td>
                <td>{g.alias}</td>
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
