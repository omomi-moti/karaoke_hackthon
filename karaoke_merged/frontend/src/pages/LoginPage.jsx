import React, { useEffect, useState } from "react";
import LoginButton from "../components/LoginButton";
import { fetchMe } from "../api/spotify";
import { useNavigate } from "react-router-dom";

export default function LoginPage() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });
  const navigate = useNavigate();

  useEffect(() => {
    // 既にCookieにrefresh tokenがあれば /api/me が成功する
    fetchMe()
      .then(u => {
        localStorage.setItem("spotify_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (user) navigate("/");
  }, [user, navigate]);

  return (
    <div className="page center">
      <h1>Karaoke Hub</h1>
      <p>Spotify の再生履歴から、カラオケで歌いやすい曲をおすすめします。</p>
      <LoginButton />
      <div className="hint">
        ログイン後、自動でトップへ遷移します。
      </div>
    </div>
  );
}
