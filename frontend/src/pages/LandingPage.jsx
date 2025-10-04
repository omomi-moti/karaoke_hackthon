"use client"
import LoginButton from "../components/LoginButton";
import './LandingPage.css'; // ← この行を追加

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* 背景エフェクト */}
      <div className="background-effects">
        <div className="glow-orb pink"></div>
        <div className="glow-orb purple"></div>
        <div className="glow-orb yellow"></div>
      </div>

      {/* メインコンテンツ */}
      <div className="landing-content">
        <h1 className="landing-title">karaokeHUB</h1>
        <p className="landing-subtitle">カラオケリストを設定して、きもちよく歌おう</p>
        <div className="landing-button">
          <LoginButton />
        </div>
      </div>

      {/* <style jsx>ブロックはここから消えている */}
    </div>
  )
}