import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { GuestRoute, ProtectedRoute } from './components/ProtectedRoute'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import LoginPage from './pages/LoginPage'
import LogoutPage from './pages/LogoutPage'
import PredictPage from './pages/PredictPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'

export default function App() {
  return (
    <Routes>
      {/* Only for visitors who are NOT logged in */}
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* Only for logged-in users, inside the page frame with the navbar */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/predict" element={<PredictPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>

      {/* Outside the guards: logging out must work whatever the current state is */}
      <Route path="/logout" element={<LogoutPage />} />

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
