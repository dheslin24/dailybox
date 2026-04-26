import { useState } from 'react'
import Layout from '../components/Layout'

export default function EnterPickemScores() {
  const [form, setForm] = useState({ gameid: '', fav: '', dog: '' })
  const [result, setResult] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    fetch('/api/enter_pickem_scores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gameid: form.gameid, fav: form.fav, dog: form.dog }),
    })
      .then(res => res.json())
      .then(d => {
        setResult(d)
        if (d.success) setForm({ gameid: '', fav: '', dog: '' })
      })
  }

  const set = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }))

  return (
    <Layout>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <div className="form-group">
            <input autoComplete="off" autoFocus className="form-control" name="gameid" placeholder="gameid" type="text" size="5" value={form.gameid} onChange={set('gameid')} />
            <br />
            <input className="form-control" name="fav" placeholder="fav score" type="text" size="5" value={form.fav} onChange={set('fav')} />
            <input className="form-control" name="dog" placeholder="dog score" type="text" size="5" value={form.dog} onChange={set('dog')} />
            <br />
            <button className="btn btn-default" type="submit">Submit</button>
          </div>
        </fieldset>
      </form>
      {result?.error && <p style={{ color: 'red', marginTop: '12px' }}>{result.error}</p>}
      {result?.success && <p style={{ color: 'green', marginTop: '12px' }}>Score entered successfully.</p>}
    </Layout>
  )
}
