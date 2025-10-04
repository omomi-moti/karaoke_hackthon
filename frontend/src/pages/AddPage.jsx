import React, { useEffect, useRef, useState } from "react";
import Header from "../components/Header";
import RecentPlayList from "../components/RecentPlayList";
import RecommendationList from "../components/RecommendationList";
import { fetchMe, fetchRecentlyPlayed, fetchRecommendationsFromRecent, fetchLikedTracks, loginWithSpotify } from "../api/spotify";
import { useNavigate } from "react-router-dom";
import useSelectedStore from "../hooks/useSelectedStore";

export default function AddPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("spotify_user") || "null"); } catch { return null; }
  });
  const [recent, setRecent] = useState([]);
  const [currentRecs, setCurrentRecs] = useState([]);
  const [liked, setLiked] = useState([]);
  const [likedLoading, setLikedLoading] = useState(false);
  const [likedError, setLikedError] = useState("");
  const [recsLoading, setRecsLoading] = useState(false);
  const { addSelected } = useSelectedStore();

  useEffect(() => {
    fetchMe()
      .then(u => {
        localStorage.setItem("spotify_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => navigate("/login"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 最近再生
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const recents = await fetchRecentlyPlayed(12);
        if (!mounted) return;
        setRecent(recents);
      } catch (e) { console.error(e); }
    })();
    return () => { mounted = false; };
  }, []);

  // おすすめ自動生成（一度だけ）
  const generatedOnceRef = useRef(false);
  useEffect(() => {
    if (!user) return;
    if (generatedOnceRef.current) return;
    generatedOnceRef.current = true;
    (async () => {
      try {
        setRecsLoading(true);
        const tracks = await fetchRecommendationsFromRecent(12);
        const uniq = [];
        const seen = new Set();
        for (const t of (Array.isArray(tracks) ? tracks : [])) {
          const id = t && t.id;
          if (id && !seen.has(id)) { seen.add(id); uniq.push(t); }
        }
        setCurrentRecs(uniq);
      } catch (e) { console.error(e); }
      finally { setRecsLoading(false); }
    })();
  }, [user]);

  // お気に入り（Liked Songs）
  useEffect(() => {
    if (!user) return;
    let mounted = true;
    (async () => {
      try {
        setLikedLoading(true);
        const { tracks } = await fetchLikedTracks(20, 0);
        if (!mounted) return;
        setLiked(tracks);
      } catch (e) {
        console.error(e);
        setLikedError("お気に入りの取得に失敗しました。スコープ(user-library-read)が不足している可能性があります。ヘッダーからログアウトし、再ログインしてください。");
      }
      finally { setLikedLoading(false); }
    })();
    return () => { mounted = false; };
  }, [user]);

  if (!user) return null;

  return (
    <div className="page">
      <Header user={user} />
      <section>
        <h2>お気に入りの曲</h2>
        {likedLoading ? (
          <div>読み込み中…</div>
        ) : likedError ? (
          <div style={{ color: 'var(--danger, #c00)' }}>
            <div>{likedError}</div>
            <div style={{ marginTop: 8 }}>
              <button className="btn primary" onClick={loginWithSpotify}>再ログインして許可する</button>
            </div>
          </div>
        ) : (
          <RecentPlayList tracks={liked} onAddSelected={addSelected} />
        )}
      </section>
      <section>
        <h2>最近聴いた曲</h2>
        <RecentPlayList tracks={recent} onAddSelected={addSelected} />
      </section>
      <section>
        <h2>おすすめ曲</h2>
        {recsLoading ? (
          <div>おすすめを準備中…</div>
        ) : (
          <RecommendationList tracks={currentRecs} onAddSelected={addSelected} />
        )}
      </section>
    </div>
  );
}
