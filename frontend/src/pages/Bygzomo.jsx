import { useEffect, useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function Bygzomo() {
  const session = useSession()
  const [tables, setTables] = useState([])
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/bygzomo')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } if (res.status === 403) { window.location.href = '/'; return null } return res.json() })
      .then(d => { if (d) setTables(d.tables) })
  }, [])

  if (session && session.is_admin !== 1) {
    window.location.href = '/'
    return null
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError(null)
    setResult(null)
    fetch('/api/bygzomo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
      .then(res => res.json())
      .then(d => {
        if (d.error) setError(d.error)
        else setResult(d.result)
      })
  }

  return (
    <Layout>
      {session?.is_admin === 1 && <h3><p style={{ color: 'green', fontWeight: 'bold' }}>Only admins can see this</p></h3>}
      <form onSubmit={handleSubmit}>
        <fieldset>
          <div className="form-group">
            <label htmlFor="query">Enter query:</label><br />
            <textarea id="query" rows="5" cols="50" value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          <div className="form-group">
            <button className="btn btn-default" type="submit">Submit Query</button>
          </div>
        </fieldset>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {result && (
        <>
          <h3>Result:</h3>
          <table align="center" cellPadding="6" style={{ borderCollapse: 'collapse' }}>
            <tbody>
              {result.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} style={{ border: '1px solid #ccc', padding: '4px 8px' }}>{String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {result.length === 0 && <p>Query executed (no rows returned).</p>}
        </>
      )}

      {tables.length > 0 && (
        <>
          <h3>Tables:</h3>
          <ul>
            {tables.map(t => <li key={t}>{t}</li>)}
          </ul>
        </>
      )}
    </Layout>
  )
}
