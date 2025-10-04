# server/app.py
import os
import time
import random

from flask import Flask, jsonify, redirect, request, session, make_response
from flask_cors import CORS
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from spotipy.cache_handler import MemoryCacheHandler

load_dotenv()

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
FRONTEND_ORIGIN_ENV = os.environ.get("FRONTEND_ORIGIN", "http://127.0.0.1:5173")
FRONTEND_ORIGINS = [o.strip() for o in FRONTEND_ORIGIN_ENV.split(",") if o.strip()]
FRONTEND_PRIMARY = FRONTEND_ORIGINS[0]

API_PREFIX = "/api"

CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/callback")

SCOPE = os.environ.get(
    "SPOTIFY_SCOPE",
    "user-read-email user-read-private user-read-recently-played user-top-read user-library-read"
)

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me-please")
# Primary recommendation source: Sample Playlist (override via env if needed)
RECOMMENDATION_PLAYLIST_ID = os.environ.get("RECOMMENDATION_PLAYLIST_ID", "3cEYpjA9oz9GiPac4AsH4n")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# CORS: フロントからCookie送信可
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGINS}}, supports_credentials=True)

# 本番で別オリジン/HTTPSの場合はクロスサイトCookieを有効化
if os.environ.get("COOKIE_CROSS_SITE", "false").lower() == "true":
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
    )
else:
    # ローカル用に明示しておく（デフォルトでも問題ないが可視化）
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=MemoryCacheHandler(),
        show_dialog=True,  # アカウント選択を毎回出す
    )

def _ensure_token():
    token_info = session.get("token_info")
    if not token_info:
        return None

    now = int(time.time())
    if token_info.get("expires_at") and token_info["expires_at"] - now < 60:
        try:
            oauth = _oauth()
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
            session["token_info"] = token_info
            print("[AUTH] token refreshed")
        except Exception as e:
            print("[AUTH] refresh failed -> clear session:", e)
            session.clear()
            return None
    return token_info

def _spotify():
    token_info = _ensure_token()
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info["access_token"])

def _require_auth():
    if not _ensure_token():
        return jsonify({"error": "unauthorized"}), 401
    return None

# 最近のおすすめ履歴（セッション保持）
RECENT_RECS_MAX = 5

def _save_recent_recs(track_ids):
    try:
        ids_in = [tid for tid in (track_ids or []) if isinstance(tid, str) and tid]
    except Exception:
        ids_in = []
    # de-duplicate while preserving order
    seen = set()
    ids = []
    for tid in ids_in:
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    if not ids:
        return
    now_ts = int(time.time())
    lst = session.get("recent_recs") or []
    # if identical to latest snapshot, just refresh timestamp and do not append
    if lst and (lst[0].get("track_ids") or []) == ids:
        lst[0]["ts"] = now_ts
        session["recent_recs"] = lst
        return
    entry = {"ts": now_ts, "track_ids": ids}
    lst = [entry] + lst
    if len(lst) > RECENT_RECS_MAX:
        lst = lst[:RECENT_RECS_MAX]
    session["recent_recs"] = lst

def _get_recent_recs():
    return session.get("recent_recs") or []

# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.route(f"{API_PREFIX}/ping")
def ping():
    return jsonify({"ok": True, "ts": int(time.time())})

@app.route(f"{API_PREFIX}/health")
def health():
    return jsonify({"status": "ok"})

@app.route(f"{API_PREFIX}/_routes")
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith(API_PREFIX):
            methods = ",".join(sorted(m for m in rule.methods if m in {"GET","POST","DELETE"}))
            output.append({"path": rule.rule, "methods": methods})
    return jsonify(output)

# -------- Auth --------
@app.route(f"{API_PREFIX}/auth/login")
def auth_login():
    # アカウント切替のため毎回セッションクリア
    session.clear()
    oauth = _oauth()
    auth_url = oauth.get_authorize_url()
    if "show_dialog=true" not in auth_url:
        auth_url += "&show_dialog=true"
    print("[AUTH] authorize:", auth_url)
    return redirect(auth_url, code=302)

@app.route(f"{API_PREFIX}/auth/callback")
def auth_callback():
    error = request.args.get("error")
    if error:
        return make_response(f"Spotify auth error: {error}", 400)

    code = request.args.get("code")
    oauth = _oauth()
    token_info = oauth.get_access_token(code, as_dict=True)

    # トークンをセッションに保存
    session["token_info"] = token_info

    # ★この時点でユーザーIDを確定してセッションに保存
    try:
        sp = spotipy.Spotify(auth=token_info["access_token"])
        me = sp.current_user()
        session["user_id"] = me.get("id")
        print("[AUTH] logged in as:", me.get("id"), me.get("display_name"))
    except Exception as e:
        session["user_id"] = None
        print("[AUTH] failed to fetch /me:", e)

    # フロントへ戻す（複数オリジンのときも先頭1つへ）
    return redirect(f"{FRONTEND_PRIMARY}/", code=302)

@app.route(f"{API_PREFIX}/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})

# -------- API: me / recently played / audio features / recommendations --------
@app.route(f"{API_PREFIX}/me")
def me():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user = sp.current_user()
        return jsonify({
            "id": user.get("id"),
            "display_name": user.get("display_name"),
            "country": user.get("country"),
            "product": user.get("product"),
            "images": user.get("images", []),
            "external_urls": user.get("external_urls", {}),
        })
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_user", "details": str(e)}), 500

@app.route(f"{API_PREFIX}/recently-played")
def recently_played():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        limit = int(request.args.get("limit", 20))
        rp = sp.current_user_recently_played(limit=limit)
        tracks = [it.get("track") for it in rp.get("items", []) if it.get("track")]
        return jsonify({"items": tracks})
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_recently_played", "details": str(e)}), 500

@app.route(f"{API_PREFIX}/liked-tracks")
def liked_tracks():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        res = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = res.get("items", [])
        tracks = [it.get("track") for it in items if it.get("track")]
        return jsonify({"items": tracks, "total": res.get("total")})
    except SpotifyException as se:
        msg = str(se)
        if getattr(se, "http_status", None) == 403 or (msg and "Insufficient client scope" in msg):
            return jsonify({
                "error": "insufficient_scope",
                "details": "user-library-read scope required. Please logout and login again.",
            }), 403
        return jsonify({"error": "failed_to_fetch_liked_tracks", "details": msg}), 500
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_liked_tracks", "details": str(e)}), 500

@app.route(f"{API_PREFIX}/audio-features")
def audio_features():
    need = _require_auth()
    if need: return need
    ids = request.args.get("ids", "")
    ids_list = [x for x in ids.split(",") if x.strip()]
    if not ids_list:
        return jsonify({"audio_features": []})
    sp = _spotify()
    if sp is None:
        return jsonify({"audio_features": []})
    try:
        feats = sp.audio_features(ids_list) or []
        for f in feats:
            if f and "id" not in f:
                f["id"] = None
        return jsonify({"audio_features": feats})
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_audio_features", "details": str(e)}), 500

@app.route(f"{API_PREFIX}/recommendations")
def recommendations():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        # Primary: use RECOMMENDATION_PLAYLIST_ID; Fallbacks: search + toplists category
        n = 10

        def extract_tracks(items):
            return [
                it.get("track") for it in (items or [])
                if it.get("track") and it["track"].get("id") and not it["track"].get("is_local")
            ]

        def try_fetch_playlist(pid, market=None):
            try:
                pl = sp.playlist(pid, market=market)
                items_local = (pl.get("tracks") or {}).get("items", [])
                return extract_tracks(items_local)
            except Exception:
                return []

        def is_spotify_owner(pl):
            owner = (pl or {}).get("owner") or {}
            name = (owner.get("display_name") or owner.get("id") or "").lower()
            return "spotify" in name

        # Determine user market (best effort)
        try:
            user = sp.current_user()
            market = (user or {}).get("country") or None
        except Exception:
            market = None

        tracks = []
        # 1) Fixed playlist id first (no market, then with market)
        tracks = try_fetch_playlist(RECOMMENDATION_PLAYLIST_ID, market=None)
        if not tracks and market:
            tracks = try_fetch_playlist(RECOMMENDATION_PLAYLIST_ID, market=market)

        # 2) Search by common names if still empty
        if not tracks:
            queries = [
                # New Music Friday variants
                "New Music Friday",
                "New Music Friday Japan",
                "New Music Friday – Japan",
                "New Music Friday — Japan",
                "ニュー・ミュージック・フライデー",
                # Fallbacks that often exist globally
                "Today's Top Hits",
                "Today’s Top Hits",
                "Top Hits",
                "今日のトップヒッツ",
            ]
            candidates = []
            for q in queries:
                try:
                    res = sp.search(q=q, type="playlist", limit=10) or {}
                    pls = (res.get("playlists") or {}).get("items", [])
                    # prioritize Spotify-owned first, then others
                    spotify_owned = [p for p in pls if is_spotify_owner(p)]
                    others = [p for p in pls if not is_spotify_owner(p)]
                    candidates.extend(spotify_owned + others)
                except Exception:
                    continue
            # Try each candidate until tracks found
            for p in candidates:
                pid = p.get("id")
                if not pid:
                    continue
                tracks = try_fetch_playlist(pid, market=market)
                if tracks:
                    break

        # 3) Fallback to toplists category for user's market
        if not tracks and market:
            try:
                cat = sp.category_playlists("toplists", country=market, limit=20) or {}
                pls = (cat.get("playlists") or {}).get("items", [])
                # Prefer names that look like Top Hits, Spotify-owned
                prefer = []
                for p in pls:
                    name = (p.get("name") or "").lower()
                    score = 0
                    if "top" in name and "hit" in name:
                        score += 2
                    if is_spotify_owner(p):
                        score += 1
                    prefer.append((score, p))
                for _, p in sorted(prefer, key=lambda x: -x[0]):
                    pid = p.get("id")
                    if not pid:
                        continue
                    tracks = try_fetch_playlist(pid, market=market)
                    if tracks:
                        break
            except Exception:
                pass

        # Limit to n tracks
        if len(tracks) > n:
            try:
                tracks = random.sample(tracks, n)
            except Exception:
                tracks = tracks[:n]
        else:
            tracks = tracks[:n]

        # Save snapshot (best-effort)
        try:
            track_ids = [t.get("id") for t in tracks if t and t.get("id")]
            _save_recent_recs(track_ids)
        except Exception:
            pass

        return jsonify({"tracks": tracks})
    except Exception as e:
        # Never 500 for UI: fail safe with empty list
        return jsonify({"tracks": []})

# -------- API: recent recommendations history --------
@app.route(f"{API_PREFIX}/recommendations/recent")
def recommendations_recent():
    need = _require_auth()
    if need: return need
    entries = _get_recent_recs()
    if not entries:
        return jsonify({"entries": []})
    sp = _spotify()
    out = []
    tracks_by_id = {}
    try:
        all_ids = []
        for e in entries:
            all_ids.extend([tid for tid in e.get("track_ids", []) if tid])
        for i in range(0, len(all_ids), 50):
            resp = sp.tracks(all_ids[i:i+50]) if sp else {"tracks": []}
            for t in (resp.get("tracks") or []):
                if t and t.get("id"):
                    tracks_by_id[t["id"]] = t
    except Exception:
        tracks_by_id = {}
    for e in entries:
        tids = [tid for tid in e.get("track_ids", []) if tid]
        ts = e.get("ts")
        t_objs = [tracks_by_id.get(tid) for tid in tids if tracks_by_id.get(tid)]
        out.append({"ts": ts, "track_ids": tids, "tracks": t_objs})
    return jsonify({"entries": out})

@app.route(f"{API_PREFIX}/recommendations/recent", methods=["DELETE"])
def recommendations_recent_clear():
    session.pop("recent_recs", None)
    return jsonify({"ok": True})

# -------- API: recommendation sources (playlist candidates) --------
@app.route(f"{API_PREFIX}/recommendations/sources")
def recommendation_sources():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"entries": []})
    try:
        try:
            user = sp.current_user()
            market = (user or {}).get("country") or "JP"
        except Exception:
            market = "JP"

        seen = set()
        out = []

        def try_add_playlist_basic(pl):
            pid = (pl or {}).get("id")
            if not pid or pid in seen:
                return
            try:
                # Validate accessibility by fetching the playlist
                pl_full = sp.playlist(pid)
                tracks_total = (pl_full.get("tracks") or {}).get("total")
                out.append({
                    "id": pid,
                    "name": pl.get("name"),
                    "owner": ((pl.get("owner") or {}).get("display_name") or (pl.get("owner") or {}).get("id")),
                    "tracks_total": tracks_total,
                })
                seen.add(pid)
            except Exception:
                # Skip inaccessible playlists
                pass

        # 1) Category 'toplists' for user's market
        try:
            cat = sp.category_playlists("toplists", country=market, limit=20) or {}
            pls = (cat.get("playlists") or {}).get("items", [])
            # Prefer Japan-related names first
            preferred = [p for p in pls if isinstance(p.get("name"), str) and (
                "Japan" in p["name"] or "日本" in p["name"] or "JP" in p["name"]
            )]
            for p in preferred + pls:
                try_add_playlist_basic(p)
        except Exception:
            pass

        # 2) Search common Japan editorial lists
        queries = [
            "Top 50 - Japan",
            "Viral 50 - Japan",
            "Hot Hits Japan",
            "J-Pop Now",
            "J-Rock Now",
            "Tokyo Super Hits",
            "New Music Friday Japan",
        ]
        for q in queries:
            try:
                res = sp.search(q=q, type="playlist", limit=5) or {}
                playlists = (res.get("playlists") or {}).get("items", [])
                for p in playlists:
                    try_add_playlist_basic(p)
            except Exception:
                continue

        return jsonify({"entries": out[:20], "market": market})
    except Exception as e:
        # Fail safe: return empty suggestions
        return jsonify({"entries": [], "market": None, "error": "failed_to_list_sources", "details": str(e)})

# -------- API: delete single recent recommendation entry --------
@app.route(f"{API_PREFIX}/recommendations/recent/<int:index>", methods=["DELETE"])
def recommendations_recent_delete_index(index: int):
    lst = session.get("recent_recs") or []
    if index < 0 or index >= len(lst):
        return jsonify({"ok": False, "error": "index_out_of_range", "size": len(lst)}), 400
    removed = lst.pop(index)
    session["recent_recs"] = lst
    return jsonify({"ok": True, "removed_ts": removed.get("ts"), "size": len(lst)})

@app.route(f"{API_PREFIX}/recommendations/recent/by-ts/<int:ts>", methods=["DELETE"])
def recommendations_recent_delete_ts(ts: int):
    lst = session.get("recent_recs") or []
    new_lst = [e for e in lst if int(e.get("ts") or 0) != int(ts)]
    removed_count = len(lst) - len(new_lst)
    session["recent_recs"] = new_lst
    return jsonify({"ok": True, "removed": removed_count, "size": len(new_lst)})

# -------- Debug --------
@app.route(f"{API_PREFIX}/debug/me")
def debug_me():
    need = _require_auth()
    if need:
        return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        user = sp.current_user()
        print("[DEBUG /me]", {
            "time": int(time.time()),
            "session_has_token": bool(session.get("token_info")),
            "session_user_id": session.get("user_id"),
            "me_id": user.get("id"),
            "me_display_name": user.get("display_name"),
            "me_country": user.get("country"),
        })
        return jsonify(user)
    except Exception as e:
        return jsonify({"error": "debug_me_failed", "details": str(e)}), 500

@app.route(f"{API_PREFIX}/debug/session")
def debug_session():
    ti = session.get("token_info")
    return jsonify({
        "has_token": bool(ti),
        "expires_at": ti.get("expires_at") if ti else None,
        "keys": list(session.keys()),
        "session_user_id": session.get("user_id"),
    })

@app.route(f"{API_PREFIX}/debug/me-ids")
def debug_me_ids():
    need = _require_auth()
    if need: return need
    sp = _spotify()
    if sp is None:
        return jsonify({"error": "unauthorized"}), 401
    me = sp.current_user()
    return jsonify({
        "session_user_id": session.get("user_id"),
        "live_me_id": me.get("id"),
        "display_name": me.get("display_name"),
        "email": me.get("email"),
    })

import hashlib

@app.route(f"{API_PREFIX}/debug/token-fp")
def debug_token_fp():
    ti = session.get("token_info")
    if not ti:
        return jsonify({"error": "no_token"}), 401
    at = ti.get("access_token") or ""
    rt = ti.get("refresh_token") or ""
    def fp(s): 
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10] if s else None
    return jsonify({
        "access_fp": fp(at),
        "refresh_fp": fp(rt),
        "expires_at": ti.get("expires_at"),
        "session_user_id": session.get("user_id"),
    })

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)