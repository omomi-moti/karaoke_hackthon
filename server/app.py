# server/app.py
import os
import time

from flask import Flask, jsonify, redirect, request, session, make_response
from flask_cors import CORS
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth
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
    "user-read-email user-read-private user-read-recently-played user-top-read"
)

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me-please")

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
        limit = int(request.args.get("limit", 20))
        try:
            user = sp.current_user()
            market = (user or {}).get("country") or "JP"
        except Exception:
            market = "JP"

        rp = sp.current_user_recently_played(limit=10).get("items", [])
        seed_tracks = [
            it["track"]["id"] for it in rp
            if it.get("track") and it["track"].get("id") and not it["track"].get("is_local")
        ][:5] or None

        rec = None
        if seed_tracks:
            try:
                rec = sp.recommendations(seed_tracks=seed_tracks, limit=limit, market=market)
            except Exception:
                rec = None

        if not rec:
            try:
                top = sp.current_user_top_artists(limit=5).get("items", [])
                seed_artists = [a["id"] for a in top if a.get("id")][:5]
                if seed_artists:
                    rec = sp.recommendations(seed_artists=seed_artists, limit=limit, market=market)
            except Exception:
                rec = None

        if not rec:
            seed_genres = ["pop", "j-pop", "dance", "rock", "anime"]
            rec = spotipy.Spotify(auth=_ensure_token()["access_token"]).recommendations(
                seed_genres=seed_genres[:5], limit=limit, market=market
            )

        return jsonify({"tracks": rec.get("tracks", [])})
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_recommendations", "details": str(e)}), 500

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
