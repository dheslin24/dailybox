import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function MyGames() {
  const [data, setData] = useState(null)
  const [showActive, setShowActive] = useState(true)

  useEffect(() => {
    fetch('/api/my_games')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>My Games</p></h1>

      <div>
        <input type="radio" id="Active" checked={showActive} onChange={() => setShowActive(true)} />
        <label htmlFor="Active"> Active</label>
        <input type="radio" id="Complete" checked={!showActive} onChange={() => setShowActive(false)} />
        <label htmlFor="Complete"> Complete</label>
      </div>
      <br />

      {showActive ? (
        <>
          <p>Total Active Picks: {data.total}</p>
          <table align="center" cellPadding="10">
            <thead>
              <tr>
                <th>Game ID</th>
                <th>Box Name</th>
                <th>Box Number</th>
                <th>Name Alias</th>
                <th>Entry Fee</th>
                <th>Payout Type</th>
                <th>Home #</th>
                <th>Away #</th>
                <th>Available Entries</th>
              </tr>
            </thead>
            <tbody>
              {data.active_games.map(g => (
                <tr key={`${g.boxid}-${g.box_num}`}>
                  <td className="team" onClick={() => window.location.href = `/app/display_box?boxid=${g.boxid}`} style={{cursor:'pointer'}}>{g.boxid}</td>
                  <td>{g.box_name}</td>
                  <td>{g.box_num}</td>
                  <td>{g.alias || 'Change box label'}</td>
                  <td>{g.fee}</td>
                  <td>{g.pay_type}</td>
                  <td>{g.home_num}</td>
                  <td>{g.away_num}</td>
                  <td>{data.available[String(g.boxid)]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <table align="center" cellPadding="10">
          <thead>
            <tr>
              <th>Game ID</th>
              <th>Box Type</th>
              <th>Box Name</th>
              <th>Box Number</th>
              <th>Alias</th>
              <th>Entry Fee</th>
              <th>Payout Type</th>
              <th>Winner</th>
            </tr>
          </thead>
          <tbody>
            {data.completed_games.map(g => (
              <tr key={`${g.boxid}-${g.box_num}`}>
                <td className="team" onClick={() => window.location.href = `/app/display_box?boxid=${g.boxid}`} style={{cursor:'pointer'}}>{g.boxid}</td>
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
      )}
    </Layout>
  )
}
