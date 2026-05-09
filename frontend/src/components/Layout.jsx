import { useState, useEffect } from 'react'
import { useSession } from '../SessionContext'

export default function Layout({ children }) {
  const session = useSession()
  const [adminOpen, setAdminOpen] = useState(false)
  const [footballOpen, setFootballOpen] = useState(false)

  useEffect(() => {
    if (!adminOpen && !footballOpen) return
    const close = () => { setAdminOpen(false); setFootballOpen(false) }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [adminOpen, footballOpen])

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
                  <li className={`dropdown${footballOpen ? ' open' : ''}`}>
                    <a href="#" className="dropdown-toggle" onClick={e => { e.preventDefault(); e.stopPropagation(); setFootballOpen(o => !o) }}>
                      Football Pools <span className="caret"></span>
                    </a>
                    <ul className="dropdown-menu">
                      <li><a href="/app/custom_game_list">Super Bowl Boxes</a></li>
                      <li><a href="/app/pickem_game_list">Pickem Games</a></li>
                      <li><a href="/app/survivor_pool">Survivor Pools</a></li>
                      <li role="separator" className="divider"></li>
                      <li><a href="/app/payment_status">SB Boxes Payment Status</a></li>
                      <li><a href="/app/pickem_payment_status">Pickem Payment Status</a></li>
                    </ul>
                  </li>
                  <li><a href="/app/my_games">My Games</a></li>
                  {/* <li><a href="/app/payment_status">Payment Status</a></li> */}
                  <li><a href="/app/horse_racing">Triple Crown</a></li>
                  <li><a href="/app/golf_pool">Golf Pool</a></li>
                </ul>
                <ul className="nav navbar-nav navbar-right">
                  {(session.is_admin === 1 || session.has_golf_grant) && (
                    <li className={`dropdown${adminOpen ? ' open' : ''}`}>
                      <a href="#" className="dropdown-toggle" onClick={e => { e.preventDefault(); e.stopPropagation(); setAdminOpen(o => !o) }}>
                        Admin <span className="caret"></span>
                      </a>
                      <ul className="dropdown-menu">
                        {session.is_admin === 1 && <li><a href="/app/admin">Admin</a></li>}
                        {session.is_admin === 1 && <li><a href="/app/horse_racing_admin">HR Admin</a></li>}
                        <li><a href="/app/golf_admin">Golf Admin</a></li>
                        {session.is_admin === 1 && <li role="separator" className="divider"></li>}
                        {session.is_admin === 1 && <li><a href="/app/bygzomo">BYGZomo</a></li>}
                      </ul>
                    </li>
                  )}
                  <li><a href="/app/user_details">User {session.username}</a></li>
                  <li><a href="/logout">Log Out</a></li>
                </ul>
              </>
            ) : (
              <ul className="nav navbar-nav navbar-right">
                <li><a href="/app/register">Register</a></li>
                <li><a href="/app/login">Log In</a></li>
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
