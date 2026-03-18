import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Package, Film, ListVideo, RefreshCw, Plus, GraduationCap, MessageSquare, CheckCircle, Trophy } from 'lucide-react'

interface Stats {
  total_products: number
  total_videos: number
  videos_in_queue: number
  total_categories: number
  roleplay_sessions: number
  avg_roleplay_score: number
}

interface VideoJob {
  id: string
  title: string
  job_type: string
  status: string
  progress: number
  created_at: string
}

const statusColors: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  generating_script: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  generating_audio: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  generating_avatar: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  compositing: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({ total_products: 0, total_videos: 0, videos_in_queue: 0, total_categories: 0, roleplay_sessions: 0, avg_roleplay_score: 0 })
  const [recentJobs, setRecentJobs] = useState<VideoJob[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')

  const fetchStats = () => {
    fetch('/api/dashboard/stats').then(r => r.json()).then(setStats).catch(() => {})
  }

  useEffect(() => {
    fetchStats()
    fetch('/api/video-jobs').then(r => r.json()).then((jobs: VideoJob[]) => setRecentJobs(jobs.slice(0, 5))).catch(() => {})
  }, [])

  const handleSync = async () => {
    setSyncing(true)
    setSyncMsg('')
    try {
      const res = await fetch('/api/sync', { method: 'POST' })
      const data = await res.json()
      setSyncMsg(data.message || data.detail || 'Sync completed')
      fetchStats()
    } catch {
      setSyncMsg('Sync failed — check GroMo API settings')
    } finally {
      setSyncing(false)
    }
  }

  const statCards = [
    { label: 'Total Products', value: stats.total_products, icon: Package, color: 'bg-blue-500' },
    { label: 'Categories', value: stats.total_categories, icon: Package, color: 'bg-purple-500' },
    { label: 'Videos Created', value: stats.total_videos, icon: Film, color: 'bg-green-500' },
    { label: 'In Queue', value: stats.videos_in_queue, icon: ListVideo, color: 'bg-yellow-500' },
    { label: 'Roleplay Sessions', value: stats.roleplay_sessions, icon: MessageSquare, color: 'bg-orange-500' },
    { label: 'Avg Score', value: `${stats.avg_roleplay_score}/10`, icon: Trophy, color: 'bg-red-500' },
  ]

  return (
    <div className="space-y-6">
      {/* Sync Banner */}
      {syncMsg && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
          <p className="text-sm text-green-800 dark:text-green-300">{syncMsg}</p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{card.value}</p>
              </div>
              <div className={`${card.color} p-2 rounded-lg shrink-0`}>
                <card.icon className="w-5 h-5 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors text-sm font-medium"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Products'}
          </button>
          <Link
            to="/video-studio"
            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Create Video
          </Link>
          <Link
            to="/training"
            className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
          >
            <GraduationCap className="w-4 h-4" />
            Start Training
          </Link>
          <Link
            to="/roleplay"
            className="flex items-center gap-2 px-4 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors text-sm font-medium"
          >
            <MessageSquare className="w-4 h-4" />
            Roleplay Practice
          </Link>
        </div>
      </div>

      {/* Recent Video Jobs */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Video Jobs</h3>
          {recentJobs.length > 0 && (
            <Link to="/video-queue" className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium">
              View All
            </Link>
          )}
        </div>
        {recentJobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <Film className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
            <p>No video jobs yet. Create your first video to get started.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{job.title}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{new Date(job.created_at).toLocaleString()}</p>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColors[job.status] || 'bg-gray-100 dark:bg-gray-700'}`}>
                  {job.status.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
