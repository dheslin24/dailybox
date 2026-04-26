import { useEffect, useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function PickemPaymentStatus() {
  const session = useSession()
  const [data, setData] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    fetch('/api/pickem_payment_status')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }, [])

  const markPaid = (userid) => {
    const body = new URLSearchParams({ userid, paid: 'True' })
    fetch('/pickem_mark_paid', { method: 'POST', body })
      .then(() => {
        fetch('/api/pickem_payment_status')
          .then(res => res.json())
          .then(d => { if (d) setData(d) })
      })
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const isAdmin = session && data.admins.includes(session.userid)

  return (
    <Layout>
      <h1><p>Payment Status for all Users (public shaming)</p></h1>
      <p>Total users in pool: {data.total_users}</p>
      <p>Total Prize Pool: {data.prize_pool}</p>
      <img src="https://static.simpsonswiki.com/images/d/dd/Rain_man.png" alt="" />
      <br />

      <h4>
        <table align="center" className="user_table" cellPadding="10">
          <thead>
            <tr>
              <th>userid</th>
              <th>username</th>
              <th>paid?</th>
              {isAdmin && <th>mark paid</th>}
            </tr>
          </thead>
          <tbody>
            {data.display_list.map(u => (
              <tr key={u.userid}>
                <td className="payment">{u.userid}</td>
                <td className="payment">{u.username}</td>
                <td className="payment">{u.status}</td>
                {isAdmin && (
                  <td>
                    <button onClick={() => markPaid(u.userid)} className="btn btn-sm btn-default">
                      Mark Paid
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </h4>
      {msg && <p style={{ color: 'green' }}>{msg}</p>}
    </Layout>
  )
}
