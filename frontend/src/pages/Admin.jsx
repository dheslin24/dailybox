import { useEffect, useState } from 'react'
import { useSession } from '../SessionContext'
import Layout from '../components/Layout'

export default function Admin() {
  const session = useSession()
  const [payoutTypes, setPayoutTypes] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (session === null) return
    if (!session.logged_in) { window.location.href = '/login'; return }
    if (session.is_admin !== 1) { setError("Sorry, you're not an admin"); return }

    fetch('/api/admin')
      .then(res => res.json())
      .then(data => setPayoutTypes(data.payout_types))
      .catch(() => setError('Failed to load admin data.'))
  }, [session])

  if (error) return <Layout><p>{error}</p></Layout>
  if (session === null || payoutTypes.length === 0) return <Layout><p>Loading...</p></Layout>

  return (
    <Layout>
      <br />
      <a href="/admin_summary">Admin Summary for all Users</a><br /><br />
      <a href="/sv_create_pool">Create New Survivor Pool</a><br /><br />
      <a href="/enter_custom_scores">Enter Custom Game Scores</a><br /><br />
      <a href="/enter_every_score">Enter Scores for Every Score Games</a><br /><br />
      <a href="/pickem_admin">Pickem Admin Page</a><br /><br />
      <a href="/app/display_box?uat=1&boxid=56">UAT New BOX in DEV</a><br /><br />
      <a href="/app/display_box?uat=1&boxid=37">UAT New BOX in PROD</a><br /><br />

      <form action="/add_money" method="POST">
        <label>Add Money: Username <input type="text" name="username" size="10" /></label>
        <label> Amount <input type="text" name="amount" size="10" /></label>
        <input type="submit" value="Submit" />
      </form><br />

      <form action="/create_game" method="POST">
        <label>Create New Game: FEE <input type="text" name="fee" size="5" /></label>
        <label> Box Name <input type="text" name="box_name" size="10" /></label>
        <label> ESPN ID (optional) <input type="text" name="espn_id" size="10" /></label>
        <label> H <input type="text" name="home" size="10" /></label>
        <label> A <input type="text" name="away" size="10" /></label>
        <select name="box_type">
          <option value="1">New Daily Box</option>
          <option value="2">New Custom Box</option>
          <option value="3">New Gobbler</option>
        </select>
        <select name="pay_type">
          {payoutTypes.map(t => (
            <option key={t.id} value={t.id}>{t.description}</option>
          ))}
        </select>
        <input type="submit" value="Submit" />
      </form>

      <form action="/gobble_games" method="POST">
        <label>Gobble Games: boxid 1 <input type="text" name="boxid_1" size="5" /></label>
        <label> boxid 2 <input type="text" name="boxid_2" size="5" /></label>
        <label> boxid 3 <input type="text" name="boxid_3" size="5" /></label>
        <input type="submit" value="Submit" />
      </form><br />

      <form action="/user_reset" method="POST">
        <label>Reset User Password: Username <input type="text" name="username" size="10" /></label>
        <label> Password <input type="text" name="password" size="10" /></label>
        <label> Password Confirm <input type="text" name="password_confirm" size="10" /></label>
        <input type="submit" value="Submit" />
      </form>

      <form action="/add_boxes_for_user" method="POST">
        <label>Add Boxes for Username <input type="text" name="username" size="10" /></label>
        <label> # of Boxes <input type="text" name="boxes" /></label>
        <input type="submit" value="Submit" />
      </form>

      <form action="/deactivate_user" method="POST">
        <label>Deactivate UserID <input type="text" name="userid" size="5" /></label>
        <input type="submit" value="Submit" />
      </form>

      <form action="/start_game" method="POST">
        <label>Start Game ID <input type="text" name="boxid" size="5" /></label>
        <input type="submit" value="Submit" />
      </form>

      <form action="/create_privategame_code" method="POST">
        <label>Private Game ID <input type="text" name="boxid" size="5" /></label>
        <label> Passcode <input type="text" name="passcode" size="10" /></label>
        <label> Admin ID <input type="text" name="admin_id" size="5" /></label>
        <input type="submit" value="Submit" />
      </form>
    </Layout>
  )
}
