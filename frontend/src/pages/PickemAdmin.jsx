import { useEffect, useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function PickemAdmin() {
  const session = useSession()
  const [data, setData] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    fetch('/api/pickem_admin')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  if (session && session.is_admin !== 1) {
    window.location.href = '/pickem_admin'
    return null
  }

  const postForm = (url, formEl) => {
    const body = new URLSearchParams(new FormData(formEl))
    fetch(url, { method: 'POST', body })
      .then(() => setMsg('Done — redirecting...'))
      .then(() => { window.location.href = '/app/pickem_admin' })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <br />
      <a href="/enter_pickem_scores">Enter Scores for Playoff Pickem Games</a>
      <br /><br />

      <p>Create new Pickem Game below</p>
      <form onSubmit={e => { e.preventDefault(); postForm('/create_pickem_game', e.target) }}>
        <label>Season</label>{' '}
        <input type="text" name="season" size="10" defaultValue={data.season} />
        {' '}<label>Game Name</label>{' '}
        <select name="game_name">
          {data.game_name_list.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        {' '}<label>Fav</label>{' '}
        <input type="text" name="fav" size="10" />
        {' '}<label>Spread</label>{' '}
        <input type="text" name="spread" size="10" />
        {' '}<label>Dog</label>{' '}
        <input type="text" name="dog" size="10" />
        {' '}<input type="submit" />
      </form>
      <br /><br />

      <p>Lock/Unlock game below</p>
      <form onSubmit={e => { e.preventDefault(); postForm('/lock_pickem_game', e.target) }}>
        <label>Game Name</label>{' '}
        <select name="game_name">
          {data.game_group_list.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        {' '}<label>Lock</label>{' '}
        <input type="radio" name="lock" value="1" style={{ padding: '50px' }} />
        {' ---- '}
        <label>Unlock</label>{' '}
        <input type="radio" name="lock" value="0" />
        {' '}<input type="submit" />
      </form>
      <br /><br />

      <form onSubmit={e => { e.preventDefault(); postForm('/pickem_mark_paid', e.target) }}>
        <label>userid</label>{' '}
        <input type="text" name="userid" style={{ width: '50px' }} />
        {' '}<button type="submit">Mark Paid</button>
      </form>
      <br /><br />

      <form onSubmit={e => { e.preventDefault(); postForm('/pickem_enable_user', e.target) }}>
        <label>userid: </label>{' '}
        <input type="text" name="userid" style={{ width: '50px' }} />
        {' '}<button type="submit">Enable for Pickem</button>
      </form>

      {msg && <p style={{ color: 'green', marginTop: '12px' }}>{msg}</p>}
    </Layout>
  )
}
