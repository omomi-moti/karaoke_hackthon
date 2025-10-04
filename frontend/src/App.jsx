import { Routes, Route, Navigate } from "react-router-dom"
import LandingPage from "./pages/LandingPage"
// LoginPageはもう不要なので削除
import MainPage from "./pages/MainPage"
import HistoryPage from "./pages/HistoryPage"

export default function App() {
  return (
    <Routes>
      {/* ルートパス「/」をメインページに変更 */}
      <Route path="/" element={<MainPage />} />
      
      {/* 「/login」パスでランディングページを表示 */}
      <Route path="/login" element={<LandingPage />} />
      
      <Route path="/history" element={<HistoryPage />} />
      
      {/* それ以外のパスはメインページ「/」にリダイレクト */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}