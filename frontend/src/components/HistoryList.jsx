"use client"

// 履歴一覧：点数とコメントを編集可能にする
import { useState } from "react"

function clampScore(v) {
  if (v === "" || v === null || typeof v === "undefined") return null
  const n = Number(v)
  if (Number.isNaN(n)) return null
  return Math.max(0, Math.min(100, Math.round(n)))
}

function Row({ item, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [score, setScore] = useState(item.score ?? "")
  const [comment, setComment] = useState(item.comment ?? "")

  const onSave = () => {
    const next = {
      score: clampScore(score),
      comment: (comment || "").trim(),
    }
    onUpdate(item.id, next)
    setEditing(false)
  }

  const onCancel = () => {
    setScore(item.score ?? "")
    setComment(item.comment ?? "")
    setEditing(false)
  }

  return (
    <div className="history-row">
      <div className="meta">
        <div className="title">{item.title || "(無題)"}</div>
        <div className="artist">{item.artist || "Unknown Artist"}</div>
        <div className="dates">
          {item.createdAt ? <span>作成: {new Date(item.createdAt).toLocaleString()}</span> : null}
          {item.updatedAt ? (
            <span style={{ marginLeft: 8 }}>更新: {new Date(item.updatedAt).toLocaleString()}</span>
          ) : null}
        </div>
      </div>

      {!editing ? (
        <div className="fields">
          <div>点数: {item.score ?? "-"}</div>
          <div className="comment">コメント: {item.comment ? item.comment : "-"}</div>
          <div className="actions">
            <button className="btn" onClick={() => setEditing(true)}>
              編集
            </button>
            <button className="btn danger" onClick={() => onDelete(item.id)}>
              削除
            </button>
          </div>
        </div>
      ) : (
        <div className="fields edit">
          <label style={{ display: "block", marginBottom: 8 }}>
            点数（0〜100・空でも可）：
            <input
              type="number"
              min={0}
              max={100}
              value={score === null ? "" : score}
              onChange={(e) => setScore(e.target.value)}
              style={{ marginLeft: 8, width: 100 }}
            />
          </label>

          <label style={{ display: "block", marginBottom: 8 }}>
            コメント：
            <textarea
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: 6 }}
              placeholder="メモを追加..."
            />
          </label>

          <div className="actions">
            <button className="btn primary" onClick={onSave}>
              保存
            </button>
            <button className="btn" onClick={onCancel}>
              取消
            </button>
            <button className="btn danger" onClick={() => onDelete(item.id)} style={{ marginLeft: "auto" }}>
              削除
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function HistoryList({ items, onUpdate, onDelete }) {
  if (!items?.length) return <div>まだ履歴がありません。</div>
  return (
    <div className="history-list">
      {items.map((it) => (
        <Row key={it.id || `${it.title}-${it.createdAt}`} item={it} onUpdate={onUpdate} onDelete={onDelete} />
      ))}
    </div>
  )
}
