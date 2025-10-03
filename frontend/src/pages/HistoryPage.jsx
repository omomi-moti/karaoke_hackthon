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

  const add = (entry) =>
    setItems(prev => [{ ...entry, createdAt: entry.createdAt || new Date().toISOString() }, ...prev]);

  const remove = (id) =>
    setItems(prev => prev.filter(x => x.id !== id));

  const update = (id, patch) =>
    setItems(prev => prev.map(x => (
      x.id === id ? { ...x, ...patch, updatedAt: new Date().toISOString() } : x
    )));

  return { items, add, remove, update };
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });
  const { items, add, remove, update } = useHistoryStore();

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
        <h2>履歴の管理</h2>
        <AddHistoryForm onAdd={add} />
        <HistoryList items={items} onUpdate={update} onDelete={remove} />
      </section>
    </div>
  );
}
