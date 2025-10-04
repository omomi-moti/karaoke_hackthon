import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import SelectedList from "../components/SelectedList";
import { fetchMe } from "../api/spotify";
import { useNavigate } from "react-router-dom";
import useSelectedStore from "../hooks/useSelectedStore";

export default function MainPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });
  const { selected, removeSelected } = useSelectedStore();

  useEffect(() => {
    fetchMe()
      .then(u => {
        localStorage.setItem("spotify_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => navigate("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!user) return null;

  return (
    <div className="page">
      <Header user={user} />
      <section>
        <h2>選択された曲</h2>
        <SelectedList tracks={selected} onRemove={removeSelected} />
      </section>
    </div>
  );
}

