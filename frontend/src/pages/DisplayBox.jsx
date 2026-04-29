import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'

const WINNER_TYPES = new Set(['current_winner', 'final_winner', 'q1_winner', 'q2_winner', 'q3_winner', 'q4_winner', 'winning_q1', 'winning_q2', 'winning_q3', 'winning_q4', 'every_score_winner', 'every_minute_winner'])

function cellClass(cell, currentUserId) {
  const isWinner = WINNER_TYPES.has(cell.winner_type)
  const isMine = cell.userid === currentUserId || cell.alias === currentUserId
  if (isWinner) return isMine ? 'my_winning_box' : 'winning_box'
  if (isMine) return 'user_box'
  if (cell.name !== 'Available ') return 'taken_box'
  return 'box'
}

function AwayTeamCell({ rowIdx, away, awayTeam, teamScores }) {
  const logoUrl = teamScores[away]?.logo || ''
  const showLogo = away !== 'TBD' && logoUrl && (
    (away.length === 3 && (rowIdx === 2 || rowIdx === 6)) ||
    (away.length !== 3 && (rowIdx === 3 || rowIdx === 6))
  )
  return (
    <td className={away} style={{ borderBottom: '2px solid black' }}>
      <strong style={{ fontSize: '30px' }}>
        {showLogo ? <img src={logoUrl} width={50} height={50} alt={away} /> : awayTeam[String(rowIdx)]}
      </strong>
    </td>
  )
}

function ScoresTable({ scores, home, away, ptype }) {
  if (!scores || scores.length === 0) return null
  const isMinute = ptype === 8
  return (
    <div className="col-lg-4 col-md-6 col-xs-12">
      <p className="text-center">Live IN-Game Updates (auto-refreshes every 30s)</p>
      {ptype === 3 && (
        <p className="text-center">Curious about how payouts work?? Click <a href={`/app/es_payout_details`}>here</a></p>
      )}
      <table className="table table-striped" style={{ paddingTop: 30, tableLayout: 'fixed' }}>
        <thead>
          <tr>
            <th style={{ width: 5 }}>{isMinute ? 'Min' : '#'}</th>
            <th style={{ width: 10 }}>{home}</th>
            <th style={{ width: 10 }}>{away}</th>
            <th style={{ width: 50 }}>Desc</th>
            <th style={{ width: 30 }}>Winner</th>
            <th style={{ width: 10 }}>Box</th>
          </tr>
        </thead>
        <tbody>
          {scores.map((score, i) => {
            const sn = score[0]
            const username = String(score[score.length - 2]).slice(0, 10)
            const box = parseInt(score[score.length - 1]) + 1
            if (sn === 100) {
              const s = { backgroundColor: 'blue', color: 'white' }
              return (
                <tr key={i}>
                  <td style={s}>RF</td>
                  {score.slice(1, -2).map((f, j) => <td key={j} style={s}>{f}</td>)}
                  <td style={s}>{username}</td>
                  <td style={s}>{box}</td>
                </tr>
              )
            }
            if (sn === 101) {
              const s = { backgroundColor: 'lightblue' }
              return (
                <tr key={i}>
                  <td style={s}>RFT</td><td style={s}>n/a</td><td style={s}>n/a</td>
                  {score.slice(3, -2).map((f, j) => <td key={j} style={s}>{f}</td>)}
                  <td style={s}>{username}</td>
                  <td style={s}>{box}</td>
                </tr>
              )
            }
            if (sn === 200) {
              const s = { backgroundColor: 'darkgreen', color: 'white' }
              return (
                <tr key={i}>
                  <td style={s}>F</td>
                  {score.slice(1, -2).map((f, j) => <td key={j} style={s}>{f}</td>)}
                  <td style={s}>{username}</td>
                  <td style={s}>{box}</td>
                </tr>
              )
            }
            if (sn === 201) {
              const s = { backgroundColor: 'lightgreen' }
              return (
                <tr key={i}>
                  <td style={s}>FT</td><td style={s}>n/a</td><td style={s}>n/a</td>
                  {score.slice(3, -2).map((f, j) => <td key={j} style={s}>{f}</td>)}
                  <td style={s}>{username}</td>
                  <td style={s}>{box}</td>
                </tr>
              )
            }
            return (
              <tr key={i}>
                {score.slice(0, -2).map((f, j) => <td key={j}>{f === null ? 'n/a' : f}</td>)}
                <td>{username}</td>
                <td>{box}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function DisplayBox() {
  const [searchParams] = useSearchParams()
  const boxid = searchParams.get('boxid')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    if (!boxid) return
    fetch(`/api/display_box?boxid=${boxid}`)
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) { if (d.error) setError(d.error); else setData(d) } })
  }, [boxid])

  useEffect(load, [load])

  useEffect(() => {
    const id = setInterval(load, 30000)
    return () => clearInterval(id)
  }, [load])

  const handleBoxClick = (boxNum) => {
    fetch('/api/select_box', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ boxid, box_num: boxNum }),
    })
      .then(res => res.json())
      .then(d => { if (d.error) alert(d.error); else load() })
  }

  if (!boxid) return <Layout><p>No boxid specified.</p></Layout>
  if (error) return <Layout><p style={{ color: 'red' }}>{error}</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  const { box_name, fee, avail, payout, final_payout, rev_payout, pay_type, ptype,
    kickoff_time, game_clock, num_selection, private_game_payment_link, current_user_box_count,
    home, away, away_team, team_scores, x, y, grid, scores, images, current_userid, box_type } = data

  const ts = team_scores || {}
  const homeScores = ts[home] || {}
  const awayScores = ts[away] || {}
  const homeQtr = homeScores.qtr_scores || {}
  const awayQtr = awayScores.qtr_scores || {}
  const hasOT = homeQtr['5'] !== undefined || awayQtr['5'] !== undefined
  const hasScores = scores && scores.length > 0

  const colClass = hasScores ? 'col-lg-8 col-md-12 col-xs-12' : 'col-md-12'

  return (
    <Layout>
      <div className="row">
        <div className={colClass}>
          <h2><p className="text-center">{box_name}</p></h2>

          {(boxid === '46' || boxid === '7') && (
            <p className="text-center">
              <a href={`/app/es_payout_details?fee=${fee}`}>Click here for detailed payout table</a>
            </p>
          )}

          <h3><p className="text-center">{kickoff_time}</p></h3>
          <h4>
            <p className="text-center">
              Entry Fee: {fee} &nbsp; Boxes Available: {avail}<br />
              Number of Boxes You Own: {current_user_box_count}
            </p>
          </h4>
          <p className="text-center">{payout}</p>

          {ptype === 8 && game_clock && (
            <h4><p className="text-center">Game Clock: {game_clock}</p></h4>
          )}

          <table style={{ tableLayout: 'fixed' }} align="center">
            <thead>
              <tr>
                <td className="BYG">BYG</td>
                <th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th>
                {hasOT && <th>OT</th>}
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className={away}>{away}</td>
                <td>{awayQtr['1']}</td><td>{awayQtr['2']}</td><td>{awayQtr['3']}</td><td>{awayQtr['4']}</td>
                {hasOT && <td>{awayQtr['5']}</td>}
                <td>{awayScores.current_score}</td>
              </tr>
              <tr>
                <td className={home}>{home}</td>
                <td>{homeQtr['1']}</td><td>{homeQtr['2']}</td><td>{homeQtr['3']}</td><td>{homeQtr['4']}</td>
                {hasOT && <td>{homeQtr['5']}</td>}
                <td>{homeScores.current_score}</td>
              </tr>
            </tbody>
          </table>

          {avail !== 0 ? (
            <h5><p className="text-center">Click your selection again to 'undo' pick.</p></h5>
          ) : (
            ptype !== 8 && hasScores && (
              <>
                <h3>
                  <p className="text-center">
                    Current Final Payout: <span style={{ color: 'darkgreen' }}><strong>{final_payout}</strong></span>
                    &nbsp;&nbsp; Current Reverse Final Payout: <span style={{ color: 'darkgreen' }}><strong>{rev_payout}</strong></span>
                  </p>
                </h3>
                <h5><p className="text-center">
                  Touch Reverse: <span style={{ color: 'darkgreen' }}><strong>{fee}x4</strong></span>
                  &nbsp; Touch Final: <span style={{ color: 'darkgreen' }}><strong>{fee}x4</strong></span>
                </p></h5>
              </>
            )
          )}

          <h4><p className="text-center">{num_selection}</p></h4>

          {boxid === '4' ? (
            <img src="/static/cannellacrest.png" style={{ display: 'block', marginLeft: 'auto', marginRight: 'auto' }} alt="" />
          ) : (
            <img src="/static/will_just_one.gif" style={{ display: 'block', marginLeft: 'auto', marginRight: 'auto' }} alt="" />
          )}
        </div>

        {hasScores && <div className="col-lg-4 col-md-12 col-xs-12"></div>}
      </div>

      <div className="row">
        <div className={colClass}>
          {private_game_payment_link && (
            <p className="text-center">
              <a href={`/app/payment_status?boxid=${boxid}&priv=true`}>{private_game_payment_link}</a>
            </p>
          )}
          <table id="grid" className="box_table" align="center" style={{ tableLayout: 'fixed' }}>
            <thead>
              <tr>
                <td className="BYG" colSpan={2} style={{ borderBottom: 'solid blue' }}>
                  <strong style={{ fontSize: 30 }}>BYG</strong>
                </td>
                {home !== 'TBD' ? (
                  <td className={home} colSpan={10} style={{ borderBottom: '2px solid black' }}>
                    <strong style={{ fontSize: 30, letterSpacing: 5 }}>
                      {ts[home]?.logo && <img src={ts[home].logo} width={50} height={50} alt={home} />}
                      {' '}{home.slice(0, 3)}{' '}
                      {ts[home]?.logo && <img src={ts[home].logo} width={50} height={50} alt={home} />}
                    </strong>
                  </td>
                ) : (
                  <td className={home} colSpan={10} style={{ borderBottom: '2px solid black' }}>
                    <strong style={{ fontSize: 30, letterSpacing: 5 }}>{home.slice(0, 3)}</strong>
                  </td>
                )}
              </tr>
              <tr>
                <td className="BYG" colSpan={2} style={{ borderBottom: '1px solid black' }}>Box: {boxid}</td>
                {Object.keys(x).map(n => (
                  <td key={n} className={home}>
                    <strong style={{ fontSize: 30 }}>{x[n]}</strong>
                  </td>
                ))}
              </tr>
            </thead>
            <tbody>
              {grid.map((rowCells, rowIdx) => (
                <tr key={rowIdx}>
                  <AwayTeamCell rowIdx={rowIdx} away={away} awayTeam={away_team} teamScores={ts} />
                  <td className={away} style={{ borderBottom: '2px solid black' }}>
                    <strong style={{ fontSize: 30 }}>{y[String(rowIdx)]}</strong>
                  </td>
                  {rowCells.map((cell) => {
                    const cls = cellClass(cell, current_userid)
                    const hasImage = images[String(cell.userid)]
                    return (
                      <td
                        key={cell.box_num}
                        className={cls}
                        onClick={() => handleBoxClick(cell.box_num)}
                        style={{ cursor: 'pointer' }}
                      >
                        <p className="corner" style={cls === 'box' ? { color: 'black' } : undefined}>
                          {cell.box_num + 1}
                        </p>
                        {cell.winner_type ? (
                          <span>{cell.winner_label}<br /><br /></span>
                        ) : hasImage ? (
                          <>
                            <img src={`/static/${images[String(cell.userid)]}`} height={60} width={60} alt="" />
                            {cls === 'taken_box' && <span className="CellComment">{cell.name}</span>}
                          </>
                        ) : (
                          cell.name.slice(0, 10)
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <ScoresTable scores={scores} home={home} away={away} ptype={ptype} />
      </div>
    </Layout>
  )
}
