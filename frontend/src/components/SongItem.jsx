"use client"

export default function SongItem({ track, onQuickAdd }) {
  const artists = (track?.artists || []).map((a) => a.name).join(", ")
  return (
    <div className="song-item">
      <img
        className="cover-sm"
        src={track?.album?.images?.[2]?.url || track?.album?.images?.[1]?.url || track?.album?.images?.[0]?.url || ""}
        alt={track?.name}
      />
      <div className="info">
        <div className="title">{track?.name}</div>
        <div className="artist">{artists}</div>
      </div>
      {onQuickAdd && (
        <button className="btn" onClick={() => onQuickAdd({ title: track?.name, artist: artists })}>
          履歴に追加
        </button>
      )}
    </div>
  )
}
