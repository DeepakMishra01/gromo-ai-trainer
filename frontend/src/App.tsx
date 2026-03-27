import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { useAuthStore } from './store/authStore'

// Pages
import Login from './pages/Login'
// Register page removed — Google + Phone OTP auto-register
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Avatars from './pages/Avatars'
import Voices from './pages/Voices'
import VideoStudio from './pages/VideoStudio'
import VideoQueue from './pages/VideoQueue'
import TrainingPlayer from './pages/TrainingPlayer'
import RoleplayPractice from './pages/RoleplayPractice'
import TrainingAgent from './pages/TrainingAgent'
import Settings from './pages/Settings'
import Analytics from './pages/Analytics'

export default function App() {
  const { loadFromStorage, isAuthenticated, isAdmin } = useAuthStore()

  useEffect(() => {
    loadFromStorage()
  }, [])

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={isAuthenticated ? <Navigate to={isAdmin ? '/' : '/training'} /> : <Login />} />
      <Route path="/register" element={<Navigate to="/login" />} />

      {/* Protected routes inside Layout */}
      <Route path="/" element={
        <ProtectedRoute requireAdmin>
          <Layout><Dashboard /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/products" element={
        <ProtectedRoute requireAdmin>
          <Layout><Products /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/avatars" element={
        <ProtectedRoute requireAdmin>
          <Layout><Avatars /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/voices" element={
        <ProtectedRoute requireAdmin>
          <Layout><Voices /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/video-studio" element={
        <ProtectedRoute requireAdmin>
          <Layout><VideoStudio /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/video-queue" element={
        <ProtectedRoute requireAdmin>
          <Layout><VideoQueue /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/analytics" element={
        <ProtectedRoute requireAdmin>
          <Layout><Analytics /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute requireAdmin>
          <Layout><Settings /></Layout>
        </ProtectedRoute>
      } />

      {/* User-accessible routes */}
      <Route path="/training" element={
        <ProtectedRoute>
          <Layout><TrainingPlayer /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/roleplay" element={
        <ProtectedRoute>
          <Layout><RoleplayPractice /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/agent" element={
        <ProtectedRoute>
          <Layout><TrainingAgent /></Layout>
        </ProtectedRoute>
      } />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to={isAuthenticated ? (isAdmin ? '/' : '/training') : '/login'} />} />
    </Routes>
  )
}
