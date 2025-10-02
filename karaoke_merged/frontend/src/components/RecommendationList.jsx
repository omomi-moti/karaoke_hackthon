// 役割: おすすめ曲のカード一覧を表示
import React from "react";
import SongCard from "./SongCard";

export default function RecommendationList({ tracks, featuresMap }) {
  if (!tracks?.length) return <div>おすすめを準備中…</div>;
  return (
    <div className="grid">
      {tracks.map(t => (
        <SongCard key={t.id} track={t} feature={featuresMap?.get(t.id)} popularity={t.popularity} />
      ))}
    </div>
  );
}
