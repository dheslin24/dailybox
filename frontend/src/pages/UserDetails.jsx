import { useEffect, useState } from 'react'
import Layout from '../components/Layout'

export default function UserDetails() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/user_details')
      .then(res => {
        if (res.status === 401) throw new Error('not_logged_in')
        if (!res.ok) throw new Error('server_error')
        return res.json()
      })
      .then(setData)
      .catch(err => {
        if (err.message === 'not_logged_in') {
          window.location.href = '/app/login'
        } else {
          setError('Failed to load user details.')
        }
      })
  }, [])

  if (error) return <Layout><p>{error}</p></Layout>
  if (!data) return <Layout><p>Loading...</p></Layout>

  const { user, aliases, userid } = data

  return (
    <Layout>
      <h1>User Details</h1>

      <table align="center" cellPadding="10">
        <tbody>
          <tr><td>Username</td><td>{user.username}</td></tr>
          <tr><td>First Name</td><td>{user.first_name}</td></tr>
          <tr><td>Last Name</td><td>{user.last_name}</td></tr>
          <tr><td>Email</td><td>{user.email}</td></tr>
          <tr><td>Mobile</td><td>{user.mobile}</td></tr>
        </tbody>
      </table>

      <br />
      <a href="/reset_password">Click here to reset password</a>

      <p>These image(s) below will be displayed in all selected boxes for that username</p>

      <table align="center" cellPadding="10">
        <thead>
          <tr>
            <th>Username</th>
            <th>Image</th>
            <th>Upload Image</th>
            <th>Remove Image</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{user.username}</td>
            <td>
              {user.image
                ? <img src={`/static/${user.image}`} height="60" width="60" alt="" />
                : null}
            </td>
            <td><a href={`/upload_file?userid=${userid}`}>Click here to upload a new image</a></td>
            <td><a href={`/remove_image?userid=${userid}`}>Click here to display only username</a></td>
          </tr>
          {aliases.map(alias => (
            <tr key={alias.userid}>
              <td>{alias.username}</td>
              <td>
                {alias.image
                  ? <img src={`/static/${alias.image}`} height="60" width="60" alt="" />
                  : null}
            </td>
              <td><a href={`/upload_file?userid=${alias.userid}`}>Click here to upload a new image</a></td>
              <td><a href={`/remove_image?userid=${alias.userid}`}>Click here to display only username</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  )
}
