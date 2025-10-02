import React, { useEffect, useState } from "react";
import Header from "../components/Header";
import RecentPlayList from "../components/RecentPlayList";
import { fetchMe, fetchRecentlyPlayed } from "../api/spotify";
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

export default function MainPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });

  // ← おすすめは削除。最近聴いた曲のみ。
  const [recent, setRecent] = useState([]);
  const { add: addHistory } = useHistoryStore();

  // 認証チェック
  useEffect(() => {
    fetchMe()
      .then(u => {
        localStorage.setItem("spotify_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => navigate("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 最近聴いた曲だけ取得
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const recents = await fetchRecentlyPlayed(12);
        if (!mounted) return;
        setRecent(recents);
      } catch (e) {
        console.error(e);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const onQuickAdd = (t) => {
    addHistory({
      id: crypto.randomUUID(),
      title: t.title,
      artist: t.artist,
      score: null,
      comment: "",
      createdAt: new Date().toISOString(),
    });
  };

  if (!user) return null;

  return (
    <div className="page">
      <Header user={user} />
      <section>
        <h2>最近聴いた曲</h2>
        <RecentPlayList tracks={recent} onQuickAdd={onQuickAdd} />
      </section>
    </div>
  );
}
