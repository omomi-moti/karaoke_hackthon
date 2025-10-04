// 役割: 最近聴いた曲のリスト表示（コメント/選択に追加ボタン付き）
import React from "react";
import SongItem from "./SongItem";

export default function RecentPlayList({ tracks, onQuickAdd, onAddSelected }) {
  const list = Array.isArray(tracks) ? tracks : [];
  if (!list.length) return <div>最近聴いた曲がありません。</div>;

  // De-duplicate by track id/uri to avoid key collisions
  const seen = new Set();
  const uniq = [];
  for (const t of list) {
    const id = (t && (t.id || t.uri)) || null;
    if (id) {
      if (seen.has(id)) continue;
      seen.add(id);
    }
    uniq.push(t);
  }

  return (
    <div className="list">
      {uniq.map((t, idx) => (
        <SongItem
          key={t?.id || t?.uri || `${t?.name || 'track'}-${idx}`}
          track={t}
          onQuickAdd={onQuickAdd}
          onAddSelected={onAddSelected}
        />
      ))}
    </div>
  );
}
