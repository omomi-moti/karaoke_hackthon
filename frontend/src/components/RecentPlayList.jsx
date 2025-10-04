import SongItem from "./SongItem"

export default function RecentPlayList({ tracks, onQuickAdd }) {
  if (!tracks?.length) return <div>最近聴いた曲がありません。</div>
  return (
    <div className="list">
      {tracks.map((t) => (
        <SongItem key={t.id} track={t} onQuickAdd={onQuickAdd} />
      ))}
    </div>
  )
}
