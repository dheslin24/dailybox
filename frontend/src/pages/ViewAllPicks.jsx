import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function ViewAllPicks() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/api/view_all_picks')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  if (!data) return <Layout><p>Loading...</p></Layout>

  const { games, picks, locked_games, user_dict, tb_dict, now, last_line_time,
    eliminated_list, winner, tb_log, annual, current_userid, current_username, is_admin } = data

  const gameIds = Object.keys(games)
  const now_dt = new Date(now)

  const gameStatus = (g) => g.status?.status || ''
  const isCurrentGame = (g) => new Date(g.datetime) <= now_dt && gameStatus(g) !== 'Final' && gameStatus(g) !== 'Canceled' && gameStatus(g) !== 'Postponed'

  const pickCellClass = (userId, espnId, pick) => {
    const g = games[String(espnId)]
    if (!g || !pick || pick === 'hidden') return ''
    const isCurrent = userId === current_userid
    const gWinner = g.winner
    if (gWinner === 'TBD' || gWinner === 'PUSH') return ''
    if (pick === gWinner) return isCurrent ? 'winner_cu' : 'winner'
    return isCurrent ? 'loser_cu' : 'loser'
  }

  return (
    <Layout>
      <h1><p>All Users Picks</p></h1>
      {!winner.length && (
        <>
          {is_admin === 1 && (
            <h3><p style={{ color: 'green', fontWeight: 'bold' }}>
              Only admins can see this! Last line update: {last_line_time}
            </p></h3>
          )}
          <p>{Object.keys(picks).length} users in the pool. Total prize pool is {Object.keys(picks).length * 50}.</p>
          <p>User picks remain hidden until game locks at scheduled kickoff</p>
          <p>Spreads not final until 1 hr before scheduled kickoff</p>
          <p>In-Progress games are in <em style={{ background: 'navy', color: 'white' }}>BLUE</em> - Win/Loss reflects current score</p>
        </>
      )}
      {eliminated_list.length > 0 && (
        <p>If your name is in <em style={{ color: 'maroon' }}>RED</em>, as of this moment you are DONE!</p>
      )}
      {!winner.length && <a href="/app/display_pickem_games">Jump to enter your picks</a>}
      <br />

      {winner.length > 0 && winner.map(w => (
        <h2 key={w} style={{ color: 'green', fontWeight: 'bold' }}>👑 {user_dict[String(w)]?.username} 👑</h2>
      ))}

      {tb_log.length > 0 && (
        <>
          Tie Break Details:<br />
          <p style={{ color: 'maroon', margin: 0 }}>{tb_log[0]}</p>
          {tb_log.slice(1, 2).map((l, i) => <p key={i} style={{ color: 'green', margin: 0 }}>{l}</p>)}
          {tb_log.slice(2).map((l, i) => <p key={i + 2} style={{ color: 'maroon', margin: 0 }}>{l}</p>)}
        </>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table className="pickem_table" align="center" style={{ fontSize: '12px' }}>
          <thead>
            <tr>
              <th rowSpan={3} colSpan={2} style={{ width: '200px', backgroundColor: 'gray' }}>{annual}th Annual<br />Playoff Pickem</th>
              {gameIds.map(gid => {
                const g = games[gid]
                const inProg = isCurrentGame(g)
                const thClass = inProg ? 'current_user' : ''
                const isCxl = gameStatus(g) === 'Canceled' || gameStatus(g) === 'Postponed'
                return (
                  <th key={gid} className={thClass} style={{ fontSize: '9px', ...(isCxl ? { backgroundColor: 'gray' } : {}) }}>
                    {g.abbreviations?.AWAY} at {g.abbreviations?.HOME}
                  </th>
                )
              })}
              <th rowSpan={4} style={{ backgroundColor: 'gray' }}>T<br />B</th>
              <th rowSpan={4} style={{ backgroundColor: 'gray' }}>W<br />I<br />N<br />S</th>
            </tr>
            <tr>
              {gameIds.map(gid => {
                const g = games[gid]
                const st = gameStatus(g)
                const inProg = isCurrentGame(g)
                if (st === 'Canceled') return <th key={gid} style={{ fontSize: '8px', backgroundColor: 'gray', whiteSpace: 'nowrap' }}>Canceled</th>
                if (st === 'Postponed') return <th key={gid} style={{ fontSize: '8px', backgroundColor: 'gray', whiteSpace: 'nowrap' }}>Postponed</th>
                const lineStr = Array.isArray(g.line) ? g.line.join(' ') : (g.line || 'TBD')
                return <th key={gid} className={inProg ? 'current_user' : ''} style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>{lineStr}</th>
              })}
            </tr>
            <tr>
              {gameIds.map(gid => {
                const g = games[gid]
                const st = gameStatus(g)
                const inProg = isCurrentGame(g)
                if (st === 'Canceled' || st === 'Postponed') return <th key={gid} style={{ fontSize: '8px', backgroundColor: 'gray' }}>{st}</th>
                if (st === 'Final') return <th key={gid} style={{ fontSize: '9px' }}>Final</th>
                if (inProg) return <th key={gid} className="current_user" style={{ fontSize: '9px' }}>Q{g.status?.quarter}<br />{g.status?.displayClock}</th>
                return <th key={gid} style={{ fontSize: '9px' }}>{g.date_short}</th>
              })}
            </tr>
            <tr>
              <th style={{ fontSize: '12px', backgroundColor: 'gray' }}>Wins</th>
              <th style={{ fontSize: '12px', whiteSpace: 'nowrap', backgroundColor: 'white', color: 'darkblue' }}>Live Scoring</th>
              {gameIds.map(gid => {
                const g = games[gid]
                const st = gameStatus(g)
                const inProg = isCurrentGame(g)
                if (st === 'Canceled') return <th key={gid} style={{ fontSize: '8px', backgroundColor: 'gray', whiteSpace: 'nowrap' }}>Canceled</th>
                if (st === 'Postponed') return <th key={gid} style={{ fontSize: '8px', backgroundColor: 'gray', whiteSpace: 'nowrap' }}>Postponed</th>
                const scores = `${g.competitors?.[1]?.[2] ?? ''} - ${g.competitors?.[0]?.[2] ?? ''}`
                return <th key={gid} className={inProg ? 'current_user' : ''} style={{ fontSize: '12px', whiteSpace: 'nowrap', backgroundColor: 'white', color: 'darkblue' }}>{scores}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {Object.entries(picks).sort((a, b) => (b[1]['wins'] || 0) - (a[1]['wins'] || 0)).map(([userId, userPicks]) => {
              const uid = parseInt(userId)
              const uinfo = user_dict[String(uid)] || {}
              const username = uinfo.username || userId
              const isCurrent = uid === current_userid
              const isWinner = winner.includes(uid)
              const isElim = eliminated_list.includes(uid)
              const wins = userPicks['wins'] || 0

              let nameTd
              if (isWinner) {
                nameTd = <td className="winning_user" style={{ whiteSpace: 'nowrap', textAlign: 'left' }}>{username} 👑</td>
              } else if (isCurrent && isElim) {
                nameTd = <td className="current_user_elim" style={{ whiteSpace: 'nowrap', textAlign: 'left' }}>{username}</td>
              } else if (isCurrent) {
                nameTd = <td className="current_user" style={{ whiteSpace: 'nowrap', textAlign: 'left' }}>{username}</td>
              } else if (isElim) {
                nameTd = <td className="eliminated" style={{ whiteSpace: 'nowrap', textAlign: 'left' }}>{username}</td>
              } else {
                nameTd = <td style={{ whiteSpace: 'nowrap', textAlign: 'left' }}>{username}</td>
              }

              return (
                <tr key={userId}>
                  <td style={{ fontSize: '12px', backgroundColor: isCurrent ? undefined : 'gray' }} className={isCurrent ? 'current_user' : ''}>{wins}</td>
                  {nameTd}
                  {gameIds.map(gid => {
                    const g = games[gid]
                    const espnId = g.espn_id
                    const st = gameStatus(g)
                    const isCxl = st === 'Canceled' || st === 'Postponed'
                    const pick = userPicks[String(espnId)]
                    const isLocked = locked_games.includes(espnId) && !isCurrent

                    if (isCxl) return <td key={gid} style={{ backgroundColor: isCurrent ? 'gray' : 'darkgray' }}></td>
                    if (isLocked) return <td key={gid}>{pick ? 'XXX' : ''}</td>

                    return <td key={gid} className={pickCellClass(uid, espnId, pick) || (isCurrent ? 'current_user' : '')} style={{ whiteSpace: 'nowrap' }}>{pick}</td>
                  })}
                  {isCurrent
                    ? <><td className="current_user">{tb_dict[String(uid)]}</td><td className="current_user">{wins}</td></>
                    : <><td style={{ fontSize: '12px', backgroundColor: 'gray' }}>{tb_dict[String(uid)]}</td><td style={{ fontSize: '12px', backgroundColor: 'gray' }}>{wins}</td></>
                  }
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
