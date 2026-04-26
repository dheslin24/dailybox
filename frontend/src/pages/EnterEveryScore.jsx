import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function EnterEveryScore() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = () =>
    fetch('/api/enter_every_score')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) { if (d.error) setError(d.error); else setData(d) } })

  useEffect(() => { load() }, [])

  const submit = (payload) =>
    fetch('/api/enter_every_score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(res => res.json()).then(d => setData(d))

  const deleteScore = (score_id) =>
    fetch('/delete_score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `score_id=${score_id}`,
    }).then(() => load())

  const handleManual = (e) => {
    e.preventDefault()
    const f = e.target
    submit({ score_num: f.score_num.value, home: f.home.value, away: f.away.value })
    f.reset()
  }

  if (error) return <Layout><p>{error}</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  const { home_team, away_team, box_list, check_results, scores } = data

  return (
    <Layout>
      <p>Enter Scores for BOXID(s): {box_list.join(', ')}</p>
      <p>Sanity Checks</p>
      {check_results.map((msg, i) => <p key={i}>{msg}</p>)}

      <form onSubmit={handleManual}>
        <div className="form-group">
          <input className="form-control" name="score_num" placeholder="score number" type="text" size="5" /><br />
          <input className="form-control" name="home" placeholder={home_team} type="text" size="5" />
          <input className="form-control" name="away" placeholder={away_team} type="text" size="5" /><br />
          <button type="submit">Submit</button>
        </div>
      </form>

      <div className="form-group">
        {[1, 2, 3, 6].map(v => (
          <button key={v} className="btn btn-default" style={{margin:'2px'}} onClick={() => submit({ HOME_BUTTON: v })}>{home_team} {v}</button>
        ))}<br /><br />
        {[1, 2, 3, 6].map(v => (
          <button key={v} className="btn btn-default" style={{margin:'2px'}} onClick={() => submit({ AWAY_BUTTON: v })}>{away_team} {v}</button>
        ))}
      </div>

      <p>Delete a specific score ID</p>
      <div className="form-group">
        <input id="del_score_id" className="form-control" placeholder="score id" type="text" size="5" />
        <button onClick={() => { const v = document.getElementById('del_score_id').value; if(v) deleteScore(v) }}>Delete</button>
      </div>

      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>BoxID</th><th>Score ID</th><th>Score Num</th><th>{home_team}</th><th>{away_team}</th>
            <th>Desc</th><th>Box</th><th>Winner</th><th>First</th><th>Last</th>
          </tr>
        </thead>
        <tbody>
          {scores.map(s => (
            <tr key={s.score_id}>
              <td>{s.boxid}</td><td>{s.score_id}</td><td>{s.score_num}</td>
              <td>{s.home}</td><td>{s.away}</td><td>{s.desc}</td><td>{s.box}</td>
              <td>{s.username}</td><td>{s.first_name}</td><td>{s.last_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <a href="/app/end_game">Click here to end game and calculate final/reverse final/touch</a>
    </Layout>
  )
}
