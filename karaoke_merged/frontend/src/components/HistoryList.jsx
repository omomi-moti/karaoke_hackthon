// 役割: 履歴アイテムの一覧表示（空ならメッセージ）
import React from "react";
import HistoryItem from "./HistoryItem";

export default function HistoryList({ items, onDelete }) {
  if (!items?.length) return <div>記録はまだありません。</div>;
  return (
    <div className="stack">
      {items.map(it => (
        <HistoryItem key={it.id} item={it} onDelete={onDelete} />
      ))}
    </div>
  );
}
