import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

const GAME_LABELS = ['WC 1','WC 2','WC 3','WC 4','WC 5','WC 6','DIV 7','DIV 8','DIV 9','DIV 10','Conf 11','Conf 12','Super Bowl']

export default function PickemAllPicks() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/api/pickem_all_picks')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  if (!data) return <Layout><p>Loading...</p></Layout>

  const { game_details, user_picks, game_dict, current_username, tb_dict, winning_user, tie_break_log, winner, eliminated_list } = data

  const pickCell = (username, gameId) => {
    const pick = user_picks[username]?.picks[String(gameId)] || ''
    const gameWinner = game_dict[String(gameId)]?.winner || 'TBD'
    const isCurrent = username === current_username

    let cls = ''
    if (pick === 'hidden') {
      cls = ''
    } else if (pick && pick === gameWinner) {
      cls = isCurrent ? 'winner_cu' : 'winner'
    } else if (gameWinner === 'TBD') {
      cls = isCurrent ? 'current_user' : ''
    } else if (pick) {
      cls = isCurrent ? 'loser_cu' : 'loser'
    }

    return <td key={gameId} className={cls}>{pick === 'hidden' ? '' : pick}</td>
  }

  const usernameCell = (username) => {
    const isWinner = winner.includes(username)
    const isElim = eliminated_list.includes(username)
    const isCurrent = username === current_username

    if (isWinner) return <td className="winning_user" style={{ textAlign: 'left', borderRight: '5px solid black' }}>👑 {username}</td>
    if (isCurrent && isElim) return <td className="current_user_elim" style={{ textAlign: 'left', borderRight: '5px solid black' }}>{username}</td>
    if (isCurrent) return <td className="current_user" style={{ textAlign: 'left', borderRight: '5px solid black' }}>{username}</td>
    if (isElim) return <td className="eliminated" style={{ textAlign: 'left', borderRight: '5px solid black' }}>{username}</td>
    return <td style={{ fontSize: '14px', fontWeight: 'bold', textAlign: 'left', borderRight: '5px solid black' }}>{username}</td>
  }

  return (
    <Layout>
      <h1><p>Playoff Pickem - All Games</p></h1>
      <p>User picks remain hidden until game locks</p>
      <p>Spreads will lock 1 hour before scheduled kickoff</p>
      {eliminated_list.length > 0 && <p>If your name is in <em style={{ color: 'red' }}>RED</em>, see you next year...</p>}
      <p>HOME team in CAPS</p>
      <a href="/app/pickem_game_list">Jump to enter your picks</a>
      <br />

      {winning_user && <h2 style={{ color: 'green', fontWeight: 'bold' }}>{winning_user}</h2>}
      {tie_break_log.length > 0 && (
        <>
          Tie Break Details:<br />
          {tie_break_log.slice(0, 1).map((log, i) => <p key={i} style={{ color: 'green', margin: 0, padding: 0 }}>{log}</p>)}
          {tie_break_log.slice(1).map((log, i) => <p key={i + 1} style={{ color: 'red', margin: 0, padding: 0 }}>{log}</p>)}
        </>
      )}

      <h4>
        <table className="pickem_table" align="center">
          <thead>
            <tr>
              <th rowSpan={2} style={{ width: '250px', borderRight: '5px solid black' }}>Username</th>
              {GAME_LABELS.map((label, i) => (
                <th key={i}>{label.split(' ').map((w, j) => <span key={j}>{w}<br /></span>)}</th>
              ))}
              <th rowSpan={3} style={{ borderLeft: '5px solid black' }}>SB Tie Break</th>
              <th rowSpan={3}>Wins</th>
            </tr>
            <tr>
              {game_details.map((detail, i) => (
                <th key={i} className="all_picks" style={{ width: '200px', fontSize: '12px' }}>{detail}</th>
              ))}
            </tr>
            <tr>
              <th style={{ fontSize: '12px', textAlign: 'right', backgroundColor: 'black', color: 'white' }}>Winner:</th>
              {[1,2,3,4,5,6,7,8,9,10,11,12,13].map(n => (
                <th key={n} style={{ fontSize: '12px', backgroundColor: 'black', color: 'white' }}>{game_dict[String(n)]?.winner}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.keys(user_picks).map(username => (
              <tr key={username}>
                {usernameCell(username)}
                {[1,2,3,4,5,6,7,8,9,10,11,12,13].map(n => pickCell(username, n))}
                {username === current_username
                  ? <><td className="current_user" style={{ borderLeft: '5px solid black' }}>{tb_dict[username]}</td><td className="current_user">{user_picks[username].win_count}</td></>
                  : <><td style={{ borderLeft: '5px solid black' }}>{tb_dict[username]}</td><td style={{ fontSize: '16px', fontWeight: 'bold' }}>{user_picks[username].win_count}</td></>
                }
              </tr>
            ))}
          </tbody>
        </table>
      </h4>
    </Layout>
  )
}
