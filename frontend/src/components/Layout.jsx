import { useSession } from '../SessionContext'

export default function Layout({ children }) {
  const session = useSession()

  return (
    <div className="container">
      <nav className="navbar navbar-default">
        <div className="container-fluid">
          <div className="navbar-header">
            <button className="navbar-toggle collapsed" data-target="#navbar" data-toggle="collapse" type="button" aria-expanded="false">
              <span className="sr-only">Toggle navigation</span>
              <span className="icon-bar"></span>
              <span className="icon-bar"></span>
              <span className="icon-bar"></span>
            </button>
            <a className="navbar-brand" href="/">
              <span className="blue">B</span>
              <span className="blue">Y</span>
              <span className="blue">G</span>
              <span className="green">T</span>
              e<span className="red">c</span>
              <span className="yellow">h</span>
            </a>
          </div>
          <div className="collapse navbar-collapse" id="navbar">
            {session?.logged_in ? (
              <>
                <ul className="nav navbar-nav">
                  <li><a href="/custom_game_list">Super Bowl Boxes</a></li>
                  <li><a href="/my_games">My Games</a></li>
                  <li><a href="/payment_status/user/False">Payment Status</a></li>
                </ul>
                <ul className="nav navbar-nav navbar-right">
                  {session.is_admin === 1 && (
                    <>
                      <li><a href="/bygzomo">BYGZomo</a></li>
                      <li><a href="/admin">Admin</a></li>
                    </>
                  )}
                  <li><a href="/app/user_details">User {session.username}</a></li>
                  <li><a href="/logout">Log Out</a></li>
                </ul>
              </>
            ) : (
              <ul className="nav navbar-nav navbar-right">
                <li><a href="/register">Register</a></li>
                <li><a href="/login">Log In</a></li>
              </ul>
            )}
          </div>
        </div>
      </nav>

      <main>
        {children}
      </main>
    </div>
  )
}
