// 役割: おすすめ曲のカード一覧を表示
import React from "react";
import SongCard from "./SongCard";

export default function RecommendationList({ tracks, featuresMap, onAddSelected }) {
  if (!tracks?.length) return <div>おすすめを準備中…</div>;
  return (
    <div className="grid">
      {tracks.map(t => (
        <div key={t.id} className="rec-card">
          <SongCard track={t} feature={featuresMap?.get(t.id)} popularity={t.popularity} />
          {onAddSelected && (
            <div style={{ marginTop: 8 }}>
              <button className="btn primary" onClick={() => onAddSelected(t)}>選択に追加</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
