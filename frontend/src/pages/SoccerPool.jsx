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
    ? <img src={logo} alt={name} title={name} style={{ width: size, height: size, objectFit: 'contain' }} />
    : <span title={name} style={{ fontSize: size * 0.6, lineHeight: 1 }}>⚽</span>
}

function PickButton({ label, active, correct, consolation, wrong, disabled, onClick }) {
  let bg = '#f3f4f6', color = '#374151', border = '1px solid #d1d5db', fw = 'normal'
  if (active && !correct && !consolation && !wrong) { bg = '#2563eb'; color = '#fff'; border = '1px solid #2563eb'; fw = '600' }
  if (correct) { bg = '#16a34a'; color = '#fff'; border = '1px solid #16a34a'; fw = '600' }
  if (consolation) { bg = '#d97706'; color = '#fff'; border = '1px solid #d97706'; fw = '600' }
  if (wrong) { bg = '#dc2626'; color = '#fff'; border = '1px solid #dc2626'; fw = '600' }
  if (disabled && !correct && !consolation && !wrong) { bg = '#f9fafb'; color = '#9ca3af' }
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

function MatchCard({ match, userPick, allPicks, members, onPick, poolId, pickFormat }) {
  const { match_id, home_name, home_abbr, home_logo, away_name, away_abbr, away_logo,
          match_date, round_type, status, home_score, away_score, result, is_locked, venue } = match

  const pickOpts = round_type === 'group'
    ? (pickFormat === 'winner_only' ? ['H', 'A'] : ['H', 'D', 'A'])
    : ['H', 'A']
  const showScore = status === 'final' || status === 'in_progress'
  const matchPicks = allPicks?.[match_id] || {}
  // In winner_only group stage, a draw gives consolation pts to all picks
  const isDrawConsolation = pickFormat === 'winner_only' && round_type === 'group' && result === 'D'

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
            <span title={home_name} style={{ fontWeight: 600, fontSize: 14 }}>{home_abbr || home_name}</span>
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
            <span title={away_name} style={{ fontWeight: 600, fontSize: 14 }}>{away_abbr || away_name}</span>
            <TeamLogo logo={away_logo} name={away_name} />
          </div>
        </div>

        {/* Pick buttons */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {pickOpts.map(opt => {
            const label = opt === 'H' ? (home_abbr || 'Home') : opt === 'A' ? (away_abbr || 'Away') : 'Draw'
            const isActive = userPick === opt
            const isConsolation = isDrawConsolation && isActive
            const isCorrect = result && isActive && result === opt && !isConsolation
            const isWrong = result && isActive && result !== opt && !isConsolation
            return (
              <PickButton
                key={opt}
                label={label}
                active={isActive}
                correct={isCorrect}
                consolation={isConsolation}
                wrong={isWrong}
                disabled={is_locked}
                onClick={() => !is_locked && onPick(match_id, opt)}
              />
            )
          })}
        </div>
      </div>

      {/* Date / venue / lock indicator */}
      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
        <div>
          {fmtDate(match_date)}
          {is_locked && !result && <span style={{ marginLeft: 8, color: '#f59e0b' }}>🔒 Locked</span>}
          {result && (
            <span style={{ marginLeft: 8, color: '#6b7280' }}>
              Final: {result === 'H' ? `${home_name} won` : result === 'A' ? `${away_name} won` : 'Draw'}
            </span>
          )}
        </div>
        {venue && <div>{venue}</div>}
      </div>

      {/* Other members' picks (shown once game is locked) */}
      {is_locked && Object.keys(matchPicks).length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {members.map(m => {
            const pick = matchPicks[m.user_id]
            if (!pick) return null
            const label = pick === 'H' ? (home_abbr || 'H') : pick === 'A' ? (away_abbr || 'A') : 'D'
            const memberConsolation = isDrawConsolation
            const isCorrect = result && pick === result && !memberConsolation
            const isWrong = result && pick !== result && !memberConsolation
            return (
              <span key={m.user_id} style={{
                fontSize: 11, padding: '1px 6px', borderRadius: 10,
                background: isCorrect ? '#dcfce7' : memberConsolation ? '#fef3c7' : isWrong ? '#fee2e2' : '#f3f4f6',
                color: isCorrect ? '#15803d' : memberConsolation ? '#92400e' : isWrong ? '#dc2626' : '#374151',
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

function PlayerPicksModal({ player, matches, allPicks, pool, onClose }) {
  const playerPickMap = {}
  Object.entries(allPicks || {}).forEach(([matchId, picks]) => {
    if (picks[player.user_id] != null) playerPickMap[parseInt(matchId)] = picks[player.user_id]
  })

  const lockedMatches = matches.filter(m => m.is_locked)
  const byGroup = {}, byRound = {}
  for (const m of lockedMatches) {
    if (m.round_type === 'group') {
      const g = m.group_letter || '?'
      if (!byGroup[g]) byGroup[g] = []
      byGroup[g].push(m)
    } else {
      if (!byRound[m.round_type]) byRound[m.round_type] = []
      byRound[m.round_type].push(m)
    }
  }
  const groupLetters = Object.keys(byGroup).sort()

  const renderRow = (m) => {
    const pick = playerPickMap[m.match_id]
    const isDrawConsolation = pool.pick_format === 'winner_only' && m.round_type === 'group' && m.result === 'D'
    const isCorrect = pick && m.result && pick === m.result && !isDrawConsolation
    const isConsolation = pick && isDrawConsolation
    const isWrong = pick && m.result && pick !== m.result && !isDrawConsolation
    const pickLabel = pick === 'H' ? (m.home_abbr || 'H') : pick === 'A' ? (m.away_abbr || 'A') : pick === 'D' ? 'D' : null
    let chipBg = '#e5e7eb', chipColor = '#374151'
    if (isCorrect)    { chipBg = '#16a34a'; chipColor = '#fff' }
    if (isConsolation){ chipBg = '#d97706'; chipColor = '#fff' }
    if (isWrong)      { chipBg = '#dc2626'; chipColor = '#fff' }
    return (
      <div key={m.match_id} style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0',
        borderBottom: '1px solid #f3f4f6', fontSize: 13,
      }}>
        <span style={{ flex: 1, color: '#374151' }}>
          {m.home_abbr || m.home_name} vs {m.away_abbr || m.away_name}
        </span>
        <span style={{ minWidth: 36, textAlign: 'center' }}>
          {pickLabel
            ? <span style={{ background: chipBg, color: chipColor, borderRadius: 4, padding: '2px 7px', fontWeight: 600, fontSize: 12 }}>{pickLabel}</span>
            : <span style={{ color: '#d1d5db' }}>—</span>
          }
        </span>
        <span style={{ minWidth: 80, textAlign: 'right', fontSize: 11, color: '#9ca3af' }}>
          {m.result === 'H' ? `${m.home_abbr || m.home_name} won`
            : m.result === 'A' ? `${m.away_abbr || m.away_name} won`
            : m.result === 'D' ? 'Draw'
            : m.status === 'in_progress' ? '🔴 Live'
            : ''}
        </span>
      </div>
    )
  }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 2000, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '40px 16px', overflowY: 'auto' }}
      onClick={onClose}
    >
      <div style={{ background: '#fff', borderRadius: 8, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>
          <strong style={{ fontSize: 15 }}>⚽ {player.username}'s Picks</strong>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#9ca3af', lineHeight: 1, padding: 0 }}>×</button>
        </div>
        <div style={{ padding: '12px 16px', maxHeight: '70vh', overflowY: 'auto' }}>
          {lockedMatches.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', padding: 24 }}>No matches have started yet.</p>
          ) : (
            <>
              {groupLetters.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Group Stage</div>
                  {groupLetters.map(letter => (
                    <div key={letter} style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', marginBottom: 4 }}>Group {letter}</div>
                      {byGroup[letter].map(renderRow)}
                    </div>
                  ))}
                </div>
              )}
              {ROUND_ORDER.filter(r => r !== 'group' && byRound[r]).map(round => (
                <div key={round} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{ROUND_LABEL[round]}</div>
                  {byRound[round].map(renderRow)}
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SoccerPool() {
  const { poolId } = useParams()
  const [data, setData] = useState(null)
  const [activeTab, setActiveTab] = useState('group')
  const [groupSort, setGroupSort] = useState('group')
  const [groupStatusFilter, setGroupStatusFilter] = useState('all')
  const [knockoutStatusFilter, setKnockoutStatusFilter] = useState('all')
  const [pickMsg, setPickMsg] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [tbInput, setTbInput] = useState('')
  const [tbMsg, setTbMsg] = useState('')
  const [viewingPlayer, setViewingPlayer] = useState(null)

  const load = useCallback(() => {
    fetch(`/api/soccer_pool?pool_id=${poolId}`)
      .then(r => r.json())
      .then(d => { if (!d.error) setData(d) })
  }, [poolId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const hasLive = data?.matches?.some(m => m.status === 'in_progress')
    if (!hasLive) return
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
  }, [data?.matches, load])

  useEffect(() => {
    if (data?.tiebreaker?.user_goals != null) {
      setTbInput(String(data.tiebreaker.user_goals))
    }
  }, [data?.tiebreaker?.user_goals])

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

  const handleTiebreaker = () => {
    const goals = parseInt(tbInput)
    if (isNaN(goals) || goals < 0) { setTbMsg('Enter a valid number'); return }
    fetch('/api/soccer_tiebreaker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: parseInt(poolId), goals }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setTbMsg(d.error); return }
        setTbMsg('Saved!')
        setTimeout(() => setTbMsg(''), 3000)
        load()
      })
  }

  if (!data) return <Layout><div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Loading...</div></Layout>

  const { pool, matches, user_picks, all_picks, members, standings, can_manage, tiebreaker } = data
  const paidMap = Object.fromEntries(members.map(m => [m.user_id, m.paid]))

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

        {/* Tiebreaker panel */}
        {pool.tiebreaker === 'goals' && (
          <div style={{
            background: tiebreaker?.locked ? '#f9fafb' : '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 8, padding: '10px 14px', marginBottom: 16,
            display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 10,
          }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>🎯 Tiebreaker: </span>
              <span style={{ fontSize: 13 }}>Predict total goals scored in the tournament</span>
              {!tiebreaker?.locked && (
                <div style={{ fontSize: 11, color: '#92400e', marginTop: 2 }}>
                  Your pick is private until the first match kicks off, then it locks.
                </div>
              )}
              {tiebreaker?.locked && tiebreaker?.actual_goals > 0 && (
                <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                  · Actual so far: <strong>{tiebreaker.actual_goals}</strong>
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                type="number" min={0}
                className="form-control input-sm"
                style={{ width: 72 }}
                value={tbInput}
                onChange={e => setTbInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !tiebreaker?.locked && handleTiebreaker()}
                disabled={tiebreaker?.locked}
                placeholder="Goals"
              />
              {!tiebreaker?.locked && (
                <button className="btn btn-warning btn-sm" onClick={handleTiebreaker}>Save</button>
              )}
              {tiebreaker?.locked && (
                <span style={{ fontSize: 12, color: '#9ca3af' }}>🔒 Locked</span>
              )}
              {tbMsg && (
                <span style={{ fontSize: 12, color: tbMsg === 'Saved!' ? '#16a34a' : '#dc2626' }}>{tbMsg}</span>
              )}
            </div>
          </div>
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
            {groupMatches.length === 0 ? (
              <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>
                Group stage matches not yet available. Admin needs to seed matches from ESPN.
              </div>
            ) : (
              <>
                {/* Sort + status filter toggles */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16, alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {[['group', 'By Group'], ['date', 'By Date']].map(([val, label]) => (
                      <button
                        key={val}
                        onClick={() => setGroupSort(val)}
                        style={{
                          padding: '4px 12px', fontSize: 12, border: '1px solid #d1d5db',
                          borderRadius: 4, cursor: 'pointer',
                          background: groupSort === val ? '#2563eb' : '#fff',
                          color: groupSort === val ? '#fff' : '#374151',
                          fontWeight: groupSort === val ? 600 : 'normal',
                        }}
                      >{label}</button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {[['all', 'All'], ['final', 'Completed'], ['upcoming', 'Remaining']].map(([val, label]) => (
                      <button
                        key={val}
                        onClick={() => setGroupStatusFilter(val)}
                        style={{
                          padding: '4px 12px', fontSize: 12, border: '1px solid #d1d5db',
                          borderRadius: 4, cursor: 'pointer',
                          background: groupStatusFilter === val ? '#059669' : '#fff',
                          color: groupStatusFilter === val ? '#fff' : '#374151',
                          fontWeight: groupStatusFilter === val ? 600 : 'normal',
                        }}
                      >{label}</button>
                    ))}
                  </div>
                </div>

                {(() => {
                  const filterMatch = (m) => {
                    if (groupStatusFilter === 'final') return m.status === 'final'
                    if (groupStatusFilter === 'upcoming') return m.status !== 'final'
                    return true
                  }

                  if (groupSort === 'group') {
                    return groupLetters.map(letter => {
                      const filtered = byGroup[letter].filter(filterMatch)
                      if (!filtered.length) return null
                      return (
                        <div key={letter} style={{ marginBottom: 24 }}>
                          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
                            Group {letter}
                          </div>
                          {filtered.map(m => (
                            <MatchCard
                              key={m.match_id}
                              match={m}
                              userPick={user_picks[m.match_id]}
                              allPicks={all_picks}
                              members={members}
                              onPick={handlePick}
                              poolId={poolId}
                              pickFormat={pool.pick_format}
                            />
                          ))}
                        </div>
                      )
                    })
                  }

                  const sorted = [...groupMatches].filter(filterMatch).sort((a, b) =>
                    (a.match_date || '').localeCompare(b.match_date || '')
                  )
                  const byDay = {}
                  for (const m of sorted) {
                    const day = m.match_date
                      ? new Date(m.match_date).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
                      : 'TBD'
                    if (!byDay[day]) byDay[day] = []
                    byDay[day].push(m)
                  }
                  return Object.entries(byDay).map(([day, dayMatches]) => (
                    <div key={day} style={{ marginBottom: 24 }}>
                      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
                        {day}
                      </div>
                      {dayMatches.map(m => (
                        <MatchCard
                          key={m.match_id}
                          match={m}
                          userPick={user_picks[m.match_id]}
                          allPicks={all_picks}
                          members={members}
                          onPick={handlePick}
                          poolId={poolId}
                          pickFormat={pool.pick_format}
                        />
                      ))}
                    </div>
                  ))
                })()}
              </>
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
              <>
                <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
                  {[['all', 'All'], ['final', 'Completed'], ['upcoming', 'Remaining']].map(([val, label]) => (
                    <button
                      key={val}
                      onClick={() => setKnockoutStatusFilter(val)}
                      style={{
                        padding: '4px 12px', fontSize: 12, border: '1px solid #d1d5db',
                        borderRadius: 4, cursor: 'pointer',
                        background: knockoutStatusFilter === val ? '#059669' : '#fff',
                        color: knockoutStatusFilter === val ? '#fff' : '#374151',
                        fontWeight: knockoutStatusFilter === val ? 600 : 'normal',
                      }}
                    >{label}</button>
                  ))}
                </div>
                {ROUND_ORDER.filter(r => r !== 'group' && byRound[r]).map(round => {
                  const filtered = byRound[round].filter(m => {
                    if (knockoutStatusFilter === 'final') return m.status === 'final'
                    if (knockoutStatusFilter === 'upcoming') return m.status !== 'final'
                    return true
                  })
                  if (!filtered.length) return null
                  return (
                    <div key={round} style={{ marginBottom: 24 }}>
                      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
                        {ROUND_LABEL[round] || round}
                      </div>
                      {filtered.map(m => (
                        <MatchCard
                          key={m.match_id}
                          match={m}
                          userPick={user_picks[m.match_id]}
                          allPicks={all_picks}
                          members={members}
                          onPick={handlePick}
                          poolId={poolId}
                          pickFormat={pool.pick_format}
                        />
                      ))}
                    </div>
                  )
                })}
              </>
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
                    <th>Accuracy</th>
                    {pool.tiebreaker === 'goals' && tiebreaker?.locked && <th title="Tiebreaker: predicted total goals">Goals 🎯</th>}
                  </tr>
                </thead>
                <tbody>
                  {standings.map(s => {
                    const isMe = s.user_id === data.current_user?.user_id
                    const tbDiff = tiebreaker?.locked && tiebreaker?.actual_goals > 0 && s.tiebreaker_goals != null
                      ? Math.abs(s.tiebreaker_goals - tiebreaker.actual_goals)
                      : null
                    return (
                      <tr key={s.user_id} style={{ fontWeight: isMe ? 700 : 'normal' }}>
                        <td>{s.rank}</td>
                        <td>
                          <span
                            onClick={() => setViewingPlayer({ user_id: s.user_id, username: s.username })}
                            style={{ cursor: 'pointer', color: '#2563eb', textDecoration: 'underline', textDecorationStyle: 'dotted' }}
                          >{s.username}</span>
                          {isMe && <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 6 }}>(you)</span>}
                          {paidMap[s.user_id]
                            ? <span style={{ fontSize: 10, background: '#dcfce7', color: '#15803d', borderRadius: 4, padding: '1px 5px', marginLeft: 6 }}>paid</span>
                            : <span style={{ fontSize: 10, background: '#fee2e2', color: '#dc2626', borderRadius: 4, padding: '1px 5px', marginLeft: 6 }}>unpaid</span>
                          }
                        </td>
                        <td>{s.total_points}</td>
                        <td>{s.correct_picks}</td>
                        <td style={{ color: '#9ca3af' }}>
                          {s.total_picks > 0 ? `${Math.round(s.correct_picks / s.total_picks * 100)}%` : '—'}
                        </td>
                        {pool.tiebreaker === 'goals' && tiebreaker?.locked && (
                          <td style={{ color: '#6b7280' }}>
                            {s.tiebreaker_goals != null ? s.tiebreaker_goals : <span style={{ color: '#d1d5db' }}>—</span>}
                            {tbDiff != null && (
                              <span style={{ fontSize: 11, color: tbDiff === 0 ? '#16a34a' : '#9ca3af', marginLeft: 4 }}>
                                ({tbDiff === 0 ? '✓' : `±${tbDiff}`})
                              </span>
                            )}
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
            {/* Points key */}
            <div style={{ marginTop: 16, fontSize: 12, color: '#9ca3af' }}>
              Points per round — Group: {pool.pts_group} | R32: {pool.pts_r32} | R16: {pool.pts_r16} | QF: {pool.pts_qf} | SF: {pool.pts_sf} | Final: {pool.pts_final}
              {pool.pick_format === 'winner_only' && (
                <span> | Group draw consolation: {pool.pts_group_draw}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {viewingPlayer && (
        <PlayerPicksModal
          player={viewingPlayer}
          matches={matches}
          allPicks={all_picks}
          pool={pool}
          onClose={() => setViewingPlayer(null)}
        />
      )}
    </Layout>
  )
}
