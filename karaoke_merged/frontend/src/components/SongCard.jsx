// 役割: おすすめ曲カード（BPM/Key/Popularityなどメタ情報込み）
import React from "react";

function msToMinSec(ms) {
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000).toString().padStart(2, "0");
  return `${m}:${s}`;
}

const KEY_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];

export default function SongCard({ track, feature, popularity }) {
  const artists = (track?.artists || []).map(a => a.name).join(", ");
  const tempo = feature?.tempo ?? null;
  const keyName = feature?.key != null ? KEY_NAMES[feature.key] : "-";
  return (
    <div className="song-card">
      <img
        className="cover"
        src={track?.album?.images?.[1]?.url || track?.album?.images?.[0]?.url}
        alt={track?.name}
      />
      <div className="song-info">
        <div className="title">{track?.name}</div>
        <div className="artist">{artists}</div>
        <div className="meta">
          <span>時間: {msToMinSec(track?.duration_ms || 0)}</span>
          <span>Popularity: {popularity ?? track?.popularity ?? "-"}</span>
          <span>BPM: {tempo ?? "-"}</span>
          <span>Key: {keyName}</span>
        </div>
      </div>
      <a className="open-link" href={track?.external_urls?.spotify} target="_blank" rel="noreferrer">
        ▶︎ Spotifyで開く
      </a>
    </div>
  );
}
