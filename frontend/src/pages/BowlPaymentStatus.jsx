import { useEffect, useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function BowlPaymentStatus() {
  const session = useSession()
  const [data, setData] = useState(null)
  const [addUserId, setAddUserId] = useState('')

  const load = () => {
    fetch('/api/bowl_payment_status')
      .then(res => { if (res.status === 401) { window.location.href = '/app/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }

  useEffect(load, [])

  const postForm = (url, fields) => {
    const body = new URLSearchParams(fields)
    fetch(url, { method: 'POST', body }).then(load)
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const isAdmin = session && data.admins.includes(session.userid)

  return (
    <Layout>
      <h1><p>PICKEM Payment Status for all Users (public shaming)</p></h1>
      <p>Total users in pool: {data.total_users}</p>
      <p>Total Prize Pool: {data.prize_pool}</p>
      {isAdmin && (
        <p>Only Admins see this below, and only Admins see the last 3 columns<br />
          If PAID DH is thumbs up, means DH was paid but has not yet been xfr'd to TW</p>
      )}
      <img src="https://static.simpsonswiki.com/images/d/dd/Rain_man.png" alt="" />

      {isAdmin && (
        <>
          <br /><br />
          <form onSubmit={e => { e.preventDefault(); postForm('/add_bowl_user', { userid: addUserId }); setAddUserId('') }}>
            <label>Add new active user by userid</label>{' '}
            <input type="text" name="userid" size="5" value={addUserId} onChange={e => setAddUserId(e.target.value)} />
            {' '}<input type="submit" />
          </form>
          <h4>
            <table align="center" className="user_table" cellPadding="10">
              <thead>
                <tr><th>userid</th><th>username</th><th>paid?</th><th>paid DH?</th><th>mark paid</th><th>DH mark paid</th><th>name</th></tr>
              </thead>
              <tbody>
                {data.display_list.map(u => (
                  <tr key={u.userid}>
                    <td className="payment">{u.userid}</td>
                    <td className="payment">{u.username}</td>
                    <td className="payment">{u.paid}</td>
                    <td className="payment">{u.paid_dh}</td>
                    <td><button className="btn btn-sm btn-default" onClick={() => postForm('/bowl_mark_paid', { userid: u.userid, paid: 'True' })}>Mark Paid</button></td>
                    <td><button className="btn btn-sm btn-default" onClick={() => postForm('/bowl_mark_paid_dh', { userid: u.userid, paid_dh: 'True' })}>DH Mark Paid</button></td>
                    <td className="payment">{data.user_dict[u.userid]?.first_name} {data.user_dict[u.userid]?.last_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </h4>
        </>
      )}

      {!isAdmin && (
        <h4>
          <table align="center" className="user_table" cellPadding="10">
            <thead>
              <tr><th>userid</th><th>username</th><th>paid?</th></tr>
            </thead>
            <tbody>
              {data.display_list.map(u => (
                <tr key={u.userid}>
                  <td className="payment">{u.userid}</td>
                  <td className="payment">{u.username}</td>
                  <td className="payment">{u.paid}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </h4>
      )}
    </Layout>
  )
}
