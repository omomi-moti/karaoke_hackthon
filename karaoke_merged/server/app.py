
import os
import time
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, request, session, make_response
from flask_cors import CORS
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://127.0.0.1:5173,http://localhost:5173")
API_PREFIX = "/api"

CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/callback")
SCOPE = os.environ.get("SPOTIFY_SCOPE", "user-read-email user-read-recently-played user-top-read")

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-me-please")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# CORS: allow frontend to send cookies
CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in FRONTEND_ORIGIN.split(",")]}}, supports_credentials=True)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=None,
        # show_dialog=True,  # force re-consent if needed
    )

def _ensure_token():
    token_info = session.get("token_info")
    if not token_info:
        return None

    # refresh if expired/about to expire
    now = int(time.time())
    if token_info.get("expires_at") and token_info["expires_at"] - now < 60:
        oauth = _oauth()
        token_info = oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
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
    oauth = _oauth()
    auth_url = oauth.get_authorize_url()
    return redirect(auth_url, code=302)

@app.route(f"{API_PREFIX}/auth/callback")
def auth_callback():
    error = request.args.get("error")
    if error:
        return make_response(f"Spotify auth error: {error}", 400)
    code = request.args.get("code")
    oauth = _oauth()
    token_info = oauth.get_access_token(code, as_dict=True)
    session["token_info"] = token_info
    # Redirect back to frontend
    return redirect(f"{FRONTEND_ORIGIN}/", code=302)

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
    try:
        user = sp.current_user()
        # only return a few fields to keep it light
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
    try:
        limit = int(request.args.get("limit", 20))
        rp = sp.current_user_recently_played(limit=limit)
        # ← ここが重要：items[].track をそのまま返す
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
    try:
        feats = sp.audio_features(ids_list) or []
        # pass-through but ensure id is present
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
    try:
        limit = int(request.args.get("limit", 20))

        # 1) market（国コード）を付けると成功率が上がる
        try:
            user = sp.current_user()
            market = (user or {}).get("country") or "JP"
        except Exception:
            market = "JP"

        # 2) 最近聴いた曲 → seed_tracks を作る（ローカル曲は除外）
        rp = sp.current_user_recently_played(limit=10).get("items", [])
        seed_tracks = [
            it["track"]["id"] for it in rp
            if it.get("track") and it["track"].get("id") and not it["track"].get("is_local")
        ][:5] or None

        # 3) 順にフォールバック
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
            # 最終フォールバック（ジャンル）
            seed_genres = ["pop", "j-pop", "dance", "rock", "anime"]
            rec = sp.recommendations(seed_genres=seed_genres[:5], limit=limit, market=market)

        return jsonify({"tracks": rec.get("tracks", [])})
    except Exception as e:
        return jsonify({"error": "failed_to_fetch_recommendations", "details": str(e)}), 500



# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
