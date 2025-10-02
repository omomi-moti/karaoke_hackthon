// src/api/spotify.js
// フロントはトークンを持たず、バックエンドのAPI（/api/...）だけを呼ぶ。
// Cookie送信が必要なので fetch に credentials: "include" を付ける。

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";

function apiFetch(path, init = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  }).then(async (res) => {
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json();
  });
}

export function loginWithSpotify() {
  // サーバの /api/auth/login へ遷移（302でSpotify認可へ）
  window.location.href = `${API_BASE}/auth/login`;
}

export async function logoutSpotify() {
  await apiFetch(`/auth/logout`, { method: "POST" });
}

export async function fetchMe() {
  return apiFetch(`/me`);
}

export async function fetchRecentlyPlayed(limit = 20) {
  const data = await apiFetch(`/recently-played?limit=${limit}`);

  // サーバの返しが:
  // ① { items: [ {track: {...}}, {...track無し...} ] }（items内がオブジェクト）
  // ② { items: [ {...}, {...} ] }（items内がtrackオブジェクトそのもの）
  // の両方に対応する
  const items = Array.isArray(data?.items) ? data.items : [];
  const tracks = items.map(it => it?.track ?? it).filter(Boolean);
  return tracks;
}


export async function fetchRecommendationsFromRecent(limit = 12) {
  const data = await apiFetch(`/recommendations?limit=${limit}`);
  return data.tracks || [];
}

export async function fetchAudioFeatures(trackIds = []) {
  if (!trackIds.length) return [];
  const ids = trackIds.join(",");
  const data = await apiFetch(`/audio-features?ids=${ids}`);
  return data.audio_features || [];
}

export function buildSingabilityMap(featuresList) {
  const map = new Map();
  for (const f of featuresList) {
    if (!f || !f.id) continue;
    const tempo = f.tempo || 0;
    const bpmScore = Math.max(0, 1 - Math.abs(95 - tempo) / 60);
    map.set(f.id, { tempo: Math.round(tempo), key: f.key, scorePartial: bpmScore });
  }
  return map;
}
