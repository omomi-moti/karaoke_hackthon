"use client"

export default function HistoryItem({ item, onDelete }) {
  return (
    <div className="history-item">
      <div className="left">
        <div className="title">{item.title}</div>
        <div className="artist">{item.artist}</div>
        <div className="comment">コメント: {item.comment || "（なし）"}</div>
      </div>
      <div className="right">
        <div className="score">点数: {item.score ?? "-"}</div>
        <button className="btn btn-danger" onClick={() => onDelete?.(item.id)}>
          削除
        </button>
      </div>
    </div>
  )
}
