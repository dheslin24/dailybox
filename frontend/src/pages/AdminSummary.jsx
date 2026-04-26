import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function AdminSummary() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/admin_summary')
      .then(res => { if (res.status === 401) { window.location.href = '/login'; return null } return res.json() })
      .then(d => { if (d) setData(d) })
      .catch(() => setError('Failed to load.'))
  }, [])

  if (error) return <Layout><p>{error}</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <h1><p>Admin Summary of all Users</p></h1>
      <p>Update a user's paid amount</p>
      <p>Total BOXES given out so far: {data.total_max}</p>

      <form action="/admin_summary" method="POST">
        <input className="form-control" name="userid" placeholder="userid" type="text" size="5" />
        <input className="form-control" name="amt_paid" placeholder="$amt" type="text" size="5" />
        <button type="submit">Update Amt Paid</button>
      </form>
      <form action="/add_boxes_for_user" method="POST">
        <input className="form-control" name="userid" placeholder="userid" type="text" size="5" />
        <input className="form-control" name="boxes" placeholder="boxes" type="text" size="5" />
        <button type="submit">Update Max Boxes</button>
      </form>

      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>userid</th><th>username</th><th>first name</th><th>last name</th>
            <th>last updated</th><th>email</th><th>mobile</th><th>is admin?</th>
            <th>alias of userid</th><th># active boxes</th><th>max boxes</th>
            <th>total fees</th><th>amt paid</th>
          </tr>
        </thead>
        <tbody>
          {data.users.map(u => {
            const id = String(u.userid)
            return (
              <tr key={u.userid}>
                <td>{u.userid}</td><td>{u.username}</td><td>{u.first_name}</td><td>{u.last_name}</td>
                <td>{u.last_update}</td><td>{u.email}</td><td>{u.mobile}</td><td>{u.is_admin}</td>
                <td>{u.alias_of_userid}</td>
                <td>{data.box_counts[id] ?? 0}</td>
                <td>{data.max_boxes[id] ?? 0}</td>
                <td className="active_user">{data.fees[id] ?? 0}</td>
                <td>{data.paid[id] ?? 0}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Layout>
  )
}
