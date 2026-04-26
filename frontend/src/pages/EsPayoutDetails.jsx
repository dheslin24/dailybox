import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'

export default function EsPayoutDetails() {
  const [searchParams] = useSearchParams()
  const fee = searchParams.get('fee')
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!fee) return
    fetch(`/api/es_payout_details?fee=${fee}`)
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [fee])

  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>Detailed View of Payouts</p></h1>
      <h5>
        <p>I mean.. TW's email CLEARLY described the rules. But for those who can't read a lot of words, this table should help</p>
        <p>0-0 is considered the first score</p>
      </h5>
      <table align="center" className="table table-striped" cellPadding="10">
        <thead>
          <tr>
            <th>Number of Scores</th><th>Every Score Total</th><th>Touch Reverse</th>
            <th>Touch Final</th><th>Reverse Final</th><th>Final</th>
          </tr>
        </thead>
        <tbody>
          {data.payouts.map(p => (
            <tr key={p.scores}>
              <td style={{fontSize:'20px'}}>{p.scores}</td>
              <td style={{fontSize:'20px'}}>{p.es_total}</td>
              <td style={{fontSize:'20px'}}>{p.touch_rev}</td>
              <td style={{fontSize:'20px'}}>{p.touch_fin}</td>
              <td style={{fontSize:'20px'}}>{p.rev_final}</td>
              <td style={{fontSize:'20px'}}>{p.final}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  )
}
