import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Layout from '../components/Layout'

export default function CurrentWinners() {
  const { boxid } = useParams()
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch(`/api/current_winners/${boxid}`)
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [boxid])

  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>Score Type</th><th>Home</th><th>Away</th><th>Box</th><th>Winner</th>
          </tr>
        </thead>
        <tbody>
          {data.scores.map((s, i) => (
            <tr key={i}>
              <td>{s.score_type}</td><td>{s.x_score}</td><td>{s.y_score}</td><td>{s.winning_box}</td><td>{s.winner}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <a href={`/app/display_box?boxid=${data.boxid}`}>Back to BOX</a>
    </Layout>
  )
}
