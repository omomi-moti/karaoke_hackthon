# Karaoke Stack (Frontend + Flask Backend)

本プロジェクトは **フロント: Vite + React**、**バックエンド: Flask(Spotipy)** で、Spotify の再生履歴からカラオケ向けの曲を提案します。

## ディレクトリ構成

```
karaoke_stack/
  frontend/   # Vite + React アプリ（既存 zip を移植）
  server/     # Flask + Spotipy バックエンド（/api/* を提供）
```

## 1) Spotify Developer の準備

1. https://developer.spotify.com/ にログインし、アプリを作成
2. **Redirect URI** に以下を登録
   - `http://127.0.0.1:8000/api/auth/callback`
3. Client ID / Client Secret を控える

## 2) Backend のセットアップ（Python 3.10+ 推奨）

```bash
cd server
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env  # Windows (macは cp)
# .env を開いて、Spotify の Client ID / Secret を設定
python app.py
```
サーバは `http://127.0.0.1:8000` で起動します。

## 3) Frontend のセットアップ（Node.js 18+ 推奨）

```bash
cd frontend
npm install
# 開発用にバックエンドのURLを指定（不要ならデフォルトの http://127.0.0.1:8000/api が使われます）
echo VITE_API_BASE=http://127.0.0.1:8000/api > .env.local
npm run dev
```

フロントは `http://127.0.0.1:5173` で起動します。

## 4) ログイン動作

- フロントの「ログイン」ボタンを押す → `/api/auth/login` にリダイレクト
- Spotify 認可後に `/api/auth/callback` → **フロントトップへ戻ります**
- 以降、Cookie セッションで `/api/me` や `/api/recently-played` にアクセスできます

## 5) 提供API

- `GET /api/ping` : ヘルスチェック
- `GET /api/health` : ヘルスチェック（簡易）
- `GET /api/_routes` : ルート一覧（開発用）
- `GET /api/me` : Spotify のユーザ情報
- `GET /api/recently-played?limit=20` : 再生履歴
- `GET /api/audio-features?ids=comma,separated,trackIds` : 複数IDの音響特徴
- `GET /api/recommendations?limit=20` : 最近聴いた曲/上位アーティストからのおすすめ
- `POST /api/auth/logout` : ログアウト（セッション破棄）

## 6) よくあるエラーと対処

- **CORS / Cookie が送れない**: `server/.env` の `FRONTEND_ORIGIN` が実際のフロントURLと一致しているか確認。
- **Callback URL mismatch**: Spotify Dashboard の Redirect URI に `http://127.0.0.1:8000/api/auth/callback` を登録。
- **401 Unauthorized**: ログイン後の Cookie が消えている可能性。ブラウザのサードパーティCookie設定も確認。
- **recommendations が空**: 聴取履歴が少ないとレコメンドが弱いです。Spotifyで数曲再生してから試してください。

---

初学者向けに、README の手順通りに進めれば起動するように整えています。
