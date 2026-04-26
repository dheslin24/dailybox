import Layout from '../components/Layout'

export default function ResetPassword() {
  return (
    <Layout>
      <form action="/reset_password" method="post">
        <fieldset>
          <div className="form-group">
            <input autoComplete="off" autoFocus className="form-control" name="old_password" placeholder="Old Password" type="password" />
          </div>
          <div className="form-group">
            <input className="form-control" name="password" placeholder="New Password" type="password" />
          </div>
          <div className="form-group">
            <input className="form-control" name="password_confirm" placeholder="New Password Confirm" type="password" />
          </div>
          <div className="form-group">
            <button className="btn btn-default" type="submit">Confirm</button>
          </div>
        </fieldset>
      </form>
    </Layout>
  )
}
