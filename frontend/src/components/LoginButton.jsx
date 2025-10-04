"use client"
import { loginWithSpotify } from "../api/spotify"

export default function LoginButton() {
  return (
    <button className="btn btn-primary" onClick={loginWithSpotify}>
      Spotifyにログイン
    </button>
  )
}
