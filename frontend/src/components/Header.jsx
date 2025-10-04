"use client"
import { Link, useNavigate } from "react-router-dom"
import { logoutSpotify } from "../api/spotify"

export default function Header({ user }) {
  const navigate = useNavigate()
  const onLogout = async () => {
    await logoutSpotify()
    localStorage.removeItem("spotify_user")
    navigate("/login")
  }

  return (
    <header className="app-header">
      <Link to="/" className="brand">
        Karaoke Hub
      </Link>
      <nav className="nav">
        {/* <Link to="/">おすすめ</Link> */}
        <Link to="/history">履歴</Link>
      </nav>
      <div className="userbox">
        {user ? <span className="username">{user.display_name || user.id}</span> : <span>Guest</span>}
        <button className="btn" onClick={onLogout}>
          ログアウト
        </button>
      </div>
    </header>
  )
}
