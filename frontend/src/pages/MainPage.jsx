import React, { useEffect, useState, useRef } from "react";
import Header from "../components/Header";
import RecentPlayList from "../components/RecentPlayList";
import RecentRecommendations from "../components/RecentRecommendations";
import RecommendationList from "../components/RecommendationList";
import { fetchMe, fetchRecentlyPlayed, fetchRecommendationHistory, clearRecommendationHistory, fetchRecommendationsFromRecent } from "../api/spotify";
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
  const [recHistory, setRecHistory] = useState([]);
  const [currentRecs, setCurrentRecs] = useState([]);
  const [recsLoading, setRecsLoading] = useState(false);
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

  // 最近のおすすめ履歴をロード
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const entries = await fetchRecommendationHistory();
        if (!mounted) return;
        setRecHistory(entries);
      } catch (e) {
        console.error(e);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const reloadRecHistory = async () => {
    try {
      const entries = await fetchRecommendationHistory();
      setRecHistory(entries);
    } catch (e) {
      console.error(e);
    }
  };

  const onGenerateRecommendations = async () => {
    try {
      setRecsLoading(true);
      const tracks = await fetchRecommendationsFromRecent(12);
      // de-duplicate by track id
      const uniq = [];
      const seen = new Set();
      for (const t of (Array.isArray(tracks) ? tracks : [])) {
        const id = t && t.id;
        if (id && !seen.has(id)) {
          seen.add(id);
          uniq.push(t);
        }
      }
      setCurrentRecs(uniq);
      await reloadRecHistory();
      setRecsLoading(false);
    } catch (e) {
      console.error(e);
      setRecsLoading(false);
    }
  };

  const onClearRecommendationHistory = async () => {
    try {
      await clearRecommendationHistory();
      await reloadRecHistory();
    } catch (e) {
      console.error(e);
    }
  };

  // 初回表示時におすすめを自動生成（StrictMode/再マウント対策に sessionStorage も併用）
  const generatedOnceRef = useRef(false);
  useEffect(() => {
    if (!user) return;
    if (generatedOnceRef.current) return;
    if (sessionStorage.getItem("recs_generated_once") === "1") return;
    generatedOnceRef.current = true;
    sessionStorage.setItem("recs_generated_once", "1");
    onGenerateRecommendations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

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
      <section>
        <h2>最近のおすすめ</h2>
        <div style={{ display: 'none' }}>
          <button className="btn primary" onClick={onGenerateRecommendations} style={{ marginRight: 8 }}>おすすめを生成</button>
          <button className="btn" onClick={onClearRecommendationHistory}>履歴をクリア</button>
        </div>
        {recsLoading ? (
          <div>おすすめを準備中…</div>
        ) : currentRecs.length > 0 ? (
          <RecommendationList tracks={currentRecs} />
        ) : null}
        {(!recsLoading && currentRecs.length === 0) ? (
          <RecentRecommendations entries={recHistory} />
        ) : (
          // When showing current results, hide the latest history entry to avoid duplicate display
          <RecentRecommendations entries={recHistory.slice(1)} />
        )}
      </section>
    </div>
  );
}
