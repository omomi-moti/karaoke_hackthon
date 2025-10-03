// 役割: 履歴追加フォーム（曲名/アーティスト/点数/コメント）
// - onAdd に送信（親でローカルストレージへ保存）

import React, { useState } from "react";

export default function AddHistoryForm({ onAdd }) {
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [score, setScore] = useState("");
  const [comment, setComment] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAdd?.({
      id: crypto.randomUUID(),
      title: title.trim(),
      artist: artist.trim(),
      score: score ? Number(score) : null,
      comment: comment.trim(),
      createdAt: Date.now(),
    });
    setTitle(""); setArtist(""); setScore(""); setComment("");
  };

  return (
    <form className="form" onSubmit={submit}>
      <div className="row">
        <label>曲名</label>
        <input value={title} onChange={(e)=>setTitle(e.target.value)} placeholder="例: Pretender" />
      </div>
      <div className="row">
        <label>アーティスト</label>
        <input value={artist} onChange={(e)=>setArtist(e.target.value)} placeholder="例: Official髭男dism" />
      </div>
      <div className="row">
        <label>点数</label>
        <input type="number" min="0" max="100" value={score} onChange={(e)=>setScore(e.target.value)} placeholder="例: 85" />
      </div>
      <div className="row">
        <label>コメント</label>
        <textarea value={comment} onChange={(e)=>setComment(e.target.value)} placeholder="感想や難易度など" />
      </div>
      <button className="btn btn-primary" type="submit">保存</button>
    </form>
  );
}
