import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

export default function CreateAlias() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const boxid = searchParams.get('boxid')
  const boxnum = searchParams.get('boxnum')

  const [data, setData] = useState(null)
  const [selectedAlias, setSelectedAlias] = useState('')
  const [newAlias, setNewAlias] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!boxid || !boxnum) return
    fetch(`/api/create_alias?boxid=${boxid}&boxnum=${boxnum}`)
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [boxid, boxnum])

  const submit = (payload) => {
    fetch('/api/assign_alias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(res => res.json())
      .then(d => {
        if (d.success) navigate('/my_games')
        else setError(d.error || 'Error assigning alias')
      })
  }

  const handleExisting = (e) => {
    e.preventDefault()
    const alias = data.user_aliases.find(a => String(a.userid) === selectedAlias)
    submit({ boxid, boxnum: parseInt(boxnum), existing_alias: alias, user_aliases: data.user_aliases })
  }

  const handleNew = (e) => {
    e.preventDefault()
    submit({ boxid, boxnum: parseInt(boxnum), new_alias: newAlias, user_aliases: data.user_aliases })
  }

  if (!boxid || !boxnum) return <Layout><p>Missing boxid or boxnum parameters.</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <p>
        If you fill out this form, you will change what shows up on this boxid / boxnum.<br />
        You are still on the hook for it - it's just a label and/or image change.<br />
        Basically - you use this if you took the box for someone else, and want it displayed as such.
      </p>
      <h3>
        <p>BOXID (the ID of the whole box): {data.boxid}</p>
        <p>BOX NUMBER (the number within the grid): {data.boxnum}</p>
      </h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {data.user_aliases.length > 0 && (
        <>
          <form onSubmit={handleExisting}>
            <label>Choose an existing label for this box</label><br />
            <select value={selectedAlias} onChange={e => setSelectedAlias(e.target.value)}>
              <option value="">-- select --</option>
              {data.user_aliases.map(a => (
                <option key={a.userid} value={String(a.userid)}>{a.username}</option>
              ))}
            </select>
            <input type="submit" />
          </form>
          <br /><p>--- OR ---</p>
        </>
      )}

      <label>Create a new label</label>
      <form onSubmit={handleNew}>
        <fieldset>
          <div className="form-group">
            <input
              autoComplete="on"
              autoFocus
              className="form-control"
              placeholder="Enter New Label"
              type="text"
              value={newAlias}
              onChange={e => setNewAlias(e.target.value)}
            />
          </div>
        </fieldset>
        <input type="submit" />
      </form>
    </Layout>
  )
}
