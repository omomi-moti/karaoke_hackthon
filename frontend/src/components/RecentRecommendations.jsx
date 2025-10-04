// 役割: 最近のおすすめを表示（最新順）
import React from "react";
import RecommendationList from "./RecommendationList";

function formatTs(ts) {
  try {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  } catch {
    return "";
  }
}

export default function RecentRecommendations({ entries }) {
  const list = Array.isArray(entries) ? entries : [];
  if (!list.length) return <div>最近のおすすめコメントはまだありません。</div>;
  const compressed = [];
  let prevSig = null;
  for (const e of list) {
    const tids = Array.isArray(e?.track_ids) ? e.track_ids : [];
    const sig = tids.join(",");
    if (sig && sig === prevSig) {
      continue; // drop consecutive identical snapshot
    }
    prevSig = sig || prevSig;
    // de-duplicate tracks by id within entry
    const seen = new Set();
    const uniqTracks = [];
    for (const t of (e?.tracks || [])) {
      const id = t && t.id;
      if (id && !seen.has(id)) { seen.add(id); uniqTracks.push(t); }
    }
    compressed.push({ ...e, tracks: uniqTracks });
  }
  return (
    <div className="rec-history">
      {compressed.map((e, idx) => (
        <div key={`${e.ts}-${idx}`} className="rec-history-entry" style={{marginBottom: 24}}>
          <div className="rec-history-meta" style={{marginBottom: 8, fontWeight: 600}}>
            生成時刻: {formatTs(e.ts)} / 件数: {e.tracks?.length || 0}
          </div>
          <RecommendationList tracks={e.tracks || []} />
        </div>
      ))}
    </div>
  );
}
