import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Layout from '../components/Layout'

const ROUND_LABEL = {
  group: 'Group Stage', r32: 'Round of 32', r16: 'Round of 16',
  qf: 'Quarterfinals', sf: 'Semifinals', '3rd': 'Third Place', final: 'Final',
}
const ROUND_ORDER = ['group', 'r32', 'r16', 'qf', 'sf', '3rd', 'final']

function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

function TeamLogo({ logo, name, size = 28 }) {
  return logo
    ? <img src={logo} alt={name} style={{ width: size, height: size, objectFit: 'contain' }} />
    : <span style={{ fontSize: size * 0.6, lineHeight: 1 }}>⚽</span>
}

function PickButton({ label, active, correct, wrong, disabled, onClick }) {
  let bg = '#f3f4f6', color = '#374151', border = '1px solid #d1d5db', fw = 'normal'
  if (active && !correct && !wrong) { bg = '#2563eb'; color = '#fff'; border = '1px solid #2563eb'; fw = '600' }
  if (correct) { bg = '#16a34a'; color = '#fff'; border = '1px solid #16a34a'; fw = '600' }
  if (wrong) { bg = '#dc2626'; color = '#fff'; border = '1px solid #dc2626'; fw = '600' }
  if (disabled && !correct && !wrong) { bg = '#f9fafb'; color = '#9ca3af' }
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        padding: '4px 10px', border, borderRadius: 4, background: bg, color,
        fontWeight: fw, fontSize: 13, cursor: disabled ? 'default' : 'pointer',
        minWidth: 44,
      }}
    >{label}</button>
  )
}

function MatchCard({ match, userPick, allPicks, members, onPick, poolId }) {
  const { match_id, home_name, home_abbr, home_logo, away_name, away_abbr, away_logo,
          match_date, round_type, status, home_score, away_score, result, is_locked } = match

  const pickOpts = round_type === 'group' ? ['H', 'D', 'A'] : ['H', 'A']
  const showScore = status === 'final' || status === 'in_progress'
  const matchPicks = allPicks?.[match_id] || {}

  return (
    <div style={{
      border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 14px',
      background: is_locked ? '#fafafa' : '#fff', marginBottom: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>

        {/* Teams */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <TeamLogo logo={home_logo} name={home_name} />
            <span style={{ fontWeight: 600, fontSize: 14 }}>{home_abbr || home_name}</span>
          </div>
          <div style={{ textAlign: 'center', minWidth: 48 }}>
            {showScore
              ? <span style={{ fontWeight: 700, fontSize: 16 }}>{home_score ?? 0} – {away_score ?? 0}</span>
              : <span style={{ color: '#9ca3af', fontSize: 12 }}>vs</span>
            }
            {status === 'in_progress' && (
              <div style={{ fontSize: 10, color: '#f59e0b', fontWeight: 600, marginTop: 1 }}>LIVE</div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{away_abbr || away_name}</span>
            <TeamLogo logo={away_logo} name={away_name} />
          </div>
        </div>

        {/* Pick buttons */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {pickOpts.map(opt => {
            const label = opt === 'H' ? (home_abbr || 'Home') : opt === 'A' ? (away_abbr || 'Away') : 'Draw'
            const isActive = userPick === opt
            const isCorrect = result && isActive && result === opt
            const isWrong = result && isActive && result !== opt
            return (
              <PickButton
                key={opt}
                label={label}
                active={isActive}
                correct={isCorrect}
                wrong={isWrong}
                disabled={is_locked}
                onClick={() => !is_locked && onPick(match_id, opt)}
              />
            )
          })}
        </div>
      </div>

      {/* Date / lock indicator */}
      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
        {fmtDate(match_date)}
        {is_locked && !result && <span style={{ marginLeft: 8, color: '#f59e0b' }}>🔒 Locked</span>}
        {result && (
          <span style={{ marginLeft: 8, color: '#6b7280' }}>
            Final: {result === 'H' ? `${home_name} won` : result === 'A' ? `${away_name} won` : 'Draw'}
          </span>
        )}
      </div>

      {/* Other members' picks (shown once game is locked) */}
      {is_locked && Object.keys(matchPicks).length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {members.map(m => {
            const pick = matchPicks[m.user_id]
            if (!pick) return null
            const label = pick === 'H' ? (home_abbr || 'H') : pick === 'A' ? (away_abbr || 'A') : 'D'
            const isCorrect = result && pick === result
            const isWrong = result && pick !== result
            return (
              <span key={m.user_id} style={{
                fontSize: 11, padding: '1px 6px', borderRadius: 10,
                background: isCorrect ? '#dcfce7' : isWrong ? '#fee2e2' : '#f3f4f6',
                color: isCorrect ? '#15803d' : isWrong ? '#dc2626' : '#374151',
              }}>
                {m.username}: {label}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function SoccerPool() {
  const { poolId } = useParams()
  const [data, setData] = useState(null)
  const [activeTab, setActiveTab] = useState('group')
  const [pickMsg, setPickMsg] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(() => {
    fetch(`/api/soccer_pool?pool_id=${poolId}`)
      .then(r => r.json())
      .then(d => { if (!d.error) setData(d) })
  }, [poolId])

  useEffect(() => { load() }, [load])

  const handlePick = (matchId, pick) => {
    fetch('/api/soccer_pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: parseInt(poolId), match_id: matchId, pick }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setPickMsg(d.error); setTimeout(() => setPickMsg(''), 4000); return }
        setData(prev => ({ ...prev, user_picks: { ...prev.user_picks, [matchId]: pick } }))
      })
  }

  const handleRefresh = () => {
    setRefreshing(true)
    fetch('/api/soccer_refresh_matches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: parseInt(poolId) }),
    })
      .then(r => r.json())
      .then(() => { load(); setRefreshing(false) })
      .catch(() => setRefreshing(false))
  }

  if (!data) return <Layout><div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Loading...</div></Layout>

  const { pool, matches, user_picks, all_picks, members, standings, can_manage } = data

  // Separate group stage from knockout
  const groupMatches = matches.filter(m => m.round_type === 'group')
  const knockoutMatches = matches.filter(m => m.round_type !== 'group')

  // Group stage: organized by group letter
  const byGroup = {}
  for (const m of groupMatches) {
    const g = m.group_letter || '?'
    if (!byGroup[g]) byGroup[g] = []
    byGroup[g].push(m)
  }
  const groupLetters = Object.keys(byGroup).sort()

  // Knockout: organized by round
  const byRound = {}
  for (const m of knockoutMatches) {
    if (!byRound[m.round_type]) byRound[m.round_type] = []
    byRound[m.round_type].push(m)
  }

  const tabStyle = (t) => ({
    padding: '8px 20px', border: 'none', borderBottom: activeTab === t ? '2px solid #2563eb' : '2px solid transparent',
    background: 'none', fontWeight: activeTab === t ? 600 : 'normal',
    color: activeTab === t ? '#2563eb' : '#6b7280', cursor: 'pointer', fontSize: 14,
  })

  return (
    <Layout>
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '20px 16px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 2 }}>
              <a href="/app/soccer_pools" style={{ color: '#6b7280' }}>⚽ World Cup Pools</a> ›
            </div>
            <h2 style={{ margin: 0 }}>{pool.name}</h2>
            {pool.fee && <div style={{ fontSize: 13, color: '#6b7280' }}>Fee: {pool.fee}</div>}
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {can_manage && (
              <button className="btn btn-xs btn-default" onClick={handleRefresh} disabled={refreshing}>
                {refreshing ? 'Refreshing...' : '↻ Refresh Scores'}
              </button>
            )}
            {can_manage && (
              <a href="/app/soccer_admin" className="btn btn-xs btn-primary">Admin</a>
            )}
          </div>
        </div>

        {pickMsg && (
          <div className="alert alert-danger" style={{ marginBottom: 12 }}>{pickMsg}</div>
        )}

        {/* Tabs */}
        <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: 16, display: 'flex' }}>
          <button style={tabStyle('group')} onClick={() => setActiveTab('group')}>Group Stage</button>
          {knockoutMatches.length > 0 && (
            <button style={tabStyle('knockout')} onClick={() => setActiveTab('knockout')}>Knockout</button>
          )}
          <button style={tabStyle('standings')} onClick={() => setActiveTab('standings')}>
            Standings ({members.length})
          </button>
        </div>

        {/* Group Stage Tab */}
        {activeTab === 'group' && (
          <div>
            {matches.filter(m => m.round_type === 'group').length === 0 ? (
              <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>
                Group stage matches not yet available. Admin needs to seed matches from ESPN.
              </div>
            ) : (
              groupLetters.map(letter => (
                <div key={letter} style={{ marginBottom: 24 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
                    Group {letter}
                  </div>
                  {byGroup[letter].map(m => (
                    <MatchCard
                      key={m.match_id}
                      match={m}
                      userPick={user_picks[m.match_id]}
                      allPicks={all_picks}
                      members={members}
                      onPick={handlePick}
                      poolId={poolId}
                    />
                  ))}
                </div>
              ))
            )}
          </div>
        )}

        {/* Knockout Tab */}
        {activeTab === 'knockout' && (
          <div>
            {knockoutMatches.length === 0 ? (
              <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>
                Knockout round matches will appear here as the tournament progresses.
              </div>
            ) : (
              ROUND_ORDER.filter(r => r !== 'group' && byRound[r]).map(round => (
                <div key={round} style={{ marginBottom: 24 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
                    {ROUND_LABEL[round] || round}
                  </div>
                  {byRound[round].map(m => (
                    <MatchCard
                      key={m.match_id}
                      match={m}
                      userPick={user_picks[m.match_id]}
                      allPicks={all_picks}
                      members={members}
                      onPick={handlePick}
                      poolId={poolId}
                    />
                  ))}
                </div>
              ))
            )}
          </div>
        )}

        {/* Standings Tab */}
        {activeTab === 'standings' && (
          <div>
            {standings.length === 0 ? (
              <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>
                Standings will appear once games have been played.
              </div>
            ) : (
              <table className="table table-striped table-hover" style={{ fontSize: 14 }}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Points</th>
                    <th>Correct</th>
                    <th>Picked</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map(s => (
                    <tr key={s.user_id} style={{ fontWeight: s.user_id === data.current_user?.user_id ? 700 : 'normal' }}>
                      <td>{s.rank}</td>
                      <td>
                        {s.username}
                        {s.user_id === data.current_user?.user_id && (
                          <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 6 }}>(you)</span>
                        )}
                      </td>
                      <td>{s.total_points}</td>
                      <td>{s.correct_picks}</td>
                      <td style={{ color: '#9ca3af' }}>{s.total_picks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {/* Points key */}
            <div style={{ marginTop: 16, fontSize: 12, color: '#9ca3af' }}>
              Points per round — Group: {pool.pts_group} | R32: {pool.pts_r32} | R16: {pool.pts_r16} | QF: {pool.pts_qf} | SF: {pool.pts_sf} | Final: {pool.pts_final}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
