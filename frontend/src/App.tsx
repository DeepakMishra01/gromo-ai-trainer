import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
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

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/products" element={<Products />} />
        <Route path="/avatars" element={<Avatars />} />
        <Route path="/voices" element={<Voices />} />
        <Route path="/video-studio" element={<VideoStudio />} />
        <Route path="/video-queue" element={<VideoQueue />} />
        <Route path="/training" element={<TrainingPlayer />} />
        <Route path="/roleplay" element={<RoleplayPractice />} />
        <Route path="/agent" element={<TrainingAgent />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}
