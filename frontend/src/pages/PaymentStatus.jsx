import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function PaymentStatus() {
  const [data, setData] = useState(null)
  const [sortMethod, setSortMethod] = useState('user')

  const load = (sort) => {
    fetch(`/api/payment_status?sort_method=${sort}`)
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
  }

  useEffect(() => { load(sortMethod) }, [])

  const handleSort = (val) => {
    setSortMethod(val)
    load(val)
  }

  if (!data) return <Layout><p>Loading...</p></Layout>

  const isAdmin = data.admins.includes(data.current_userid)

  return (
    <Layout>
      <h1><p>Payment Status for all Users (public shaming)</p></h1>
      <p>Sort By:</p>
      <div>
        <input type="radio" id="sort_user" checked={sortMethod === 'user'} onChange={() => handleSort('user')} />
        <label htmlFor="sort_user"> Username</label>
        <input type="radio" id="sort_id" checked={sortMethod === 'id'} onChange={() => handleSort('id')} />
        <label htmlFor="sort_id"> ID</label>
        <input type="radio" id="sort_pay" checked={sortMethod === 'pay_status'} onChange={() => handleSort('pay_status')} />
        <label htmlFor="sort_pay"> Payment Status</label>
      </div>

      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>userid</th>
            <th>username</th>
            <th># active boxes</th>
            <th>total fees</th>
            <th>amt paid</th>
            {isAdmin && <><th>paid in full?</th><th>mark paid</th><th>name</th></>}
          </tr>
        </thead>
        <tbody>
          {data.users.map(u => {
            const id = String(u.userid)
            return (
              <tr key={u.userid}>
                <td>{u.userid}</td>
                <td>{u.username}</td>
                <td>{data.box_counts[id] ?? 0}</td>
                <td>{data.fees[id] ?? 0}</td>
                <td>{data.paid[id] ?? 0}</td>
                {isAdmin && (
                  <>
                    <td>{data.emoji[id]}</td>
                    <td>
                      <form action="/mark_paid" method="POST">
                        <input type="hidden" name="userid" value={u.userid} />
                        <input type="hidden" name="paid" value="True" />
                        <input type="hidden" name="sort_method" value={sortMethod} />
                        <input type="hidden" name="fees" value={data.fees[id] ?? 0} />
                        <input type="hidden" name="amt_paid" value={data.paid[id] ?? 0} />
                        <input type="submit" value="Mark Paid" />
                      </form>
                    </td>
                    <td>{data.user_details[id]?.first_name} {data.user_details[id]?.last_name}</td>
                  </>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </Layout>
  )
}
