import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import HistoryList from "../components/HistoryList";
import AddHistoryForm from "../components/AddHistoryForm";
import { fetchMe } from "../api/spotify";
import { useNavigate } from "react-router-dom";

function useHistoryStore() {
  const KEY = "karaoke_history";
  const [items, setItems] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
  });
  useEffect(() => { localStorage.setItem(KEY, JSON.stringify(items)); }, [items]);
  const add = (entry) => setItems(prev => [entry, ...prev]);
  const remove = (id) => setItems(prev => prev.filter(x => x.id !== id));
  return { items, add, remove };
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });
  const { items, add, remove } = useHistoryStore();

  useEffect(() => {
    fetchMe()
      .then(u => {
        localStorage.setItem("spotify_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => navigate("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page">
      <Header user={user} />
      <section>
        <h2>履歴を追加</h2>
        <AddHistoryForm onAdd={add} />
      </section>
      <section>
        <h2>これまでの記録</h2>
        <HistoryList items={items} onDelete={remove} />
      </section>
    </div>
  );
}
