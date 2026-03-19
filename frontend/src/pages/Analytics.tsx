import { useEffect, useState } from 'react'
import { Users, Activity, BarChart3, MessageSquare, Bot, GraduationCap, Film } from 'lucide-react'

interface Overview {
  total_users: number
  active_users_7d: number
  total_roleplay_sessions: number
  total_sahayak_chats: number
  total_videos_created: number
}

interface FeatureUsage {
  feature: string
  count: number
  unique_users: number
}

interface UserStat {
  id: string
  email: string
  name: string | null
  role: string
  created_at: string | null
  last_login: string | null
  activity_count: number
  roleplay_count: number
  sahayak_count: number
}

const featureIcons: Record<string, any> = {
  'roleplay.start': MessageSquare,
  'roleplay.complete': MessageSquare,
  'sahayak.chat': Bot,
  'training.view': GraduationCap,
}

export default function Analytics() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [features, setFeatures] = useState<FeatureUsage[]>([])
  const [users, setUsers] = useState<UserStat[]>([])
  const [loading, setLoading] = useState(true)

  const token = localStorage.getItem('gromo-token')
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const handleRoleChange = async (userId: string, newRole: string) => {
    const action = newRole === 'admin' ? 'promote to Admin' : 'demote to User'
    if (!confirm(`Are you sure you want to ${action} this user?`)) return
    try {
      const res = await fetch('/api/auth/promote', {
        method: 'POST',
        headers,
        body: JSON.stringify({ user_id: userId, role: newRole }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        alert(data.detail || 'Failed to change role')
        return
      }
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
    } catch {
      alert('Failed to change role')
    }
  }

  useEffect(() => {
    Promise.all([
      fetch('/api/analytics/overview', { headers }).then(r => r.json()),
      fetch('/api/analytics/feature-usage', { headers }).then(r => r.json()),
      fetch('/api/analytics/users', { headers }).then(r => r.json()),
    ]).then(([ov, ft, us]) => {
      setOverview(ov)
      setFeatures(ft)
      setUsers(us)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  const statCards = overview ? [
    { label: 'Total Users', value: overview.total_users, icon: Users, color: 'bg-blue-500' },
    { label: 'Active (7 days)', value: overview.active_users_7d, icon: Activity, color: 'bg-green-500' },
    { label: 'Roleplay Sessions', value: overview.total_roleplay_sessions, icon: MessageSquare, color: 'bg-orange-500' },
    { label: 'Sahayak Chats', value: overview.total_sahayak_chats, icon: Bot, color: 'bg-emerald-500' },
    { label: 'Videos Created', value: overview.total_videos_created, icon: Film, color: 'bg-purple-500' },
  ] : []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{card.value}</p>
              </div>
              <div className={`${card.color} p-2 rounded-lg`}>
                <card.icon className="w-5 h-5 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Feature Usage */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary-500" />
          Feature Usage
        </h3>
        {features.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm">No activity data yet</p>
        ) : (
          <div className="space-y-3">
            {features.map((f) => {
              const Icon = featureIcons[f.feature] || Activity
              const maxCount = Math.max(...features.map(x => x.count), 1)
              const pct = (f.count / maxCount) * 100
              return (
                <div key={f.feature} className="flex items-center gap-3">
                  <Icon className="w-4 h-4 text-gray-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{f.feature}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{f.count} times · {f.unique_users} users</span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                      <div className="bg-primary-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-primary-500" />
          Users ({users.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Name</th>
                <th className="text-left py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Email</th>
                <th className="text-center py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Role</th>
                <th className="text-center py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Activity</th>
                <th className="text-center py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Roleplay</th>
                <th className="text-center py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Sahayak</th>
                <th className="text-left py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Last Login</th>
                <th className="text-center py-3 px-2 font-medium text-gray-500 dark:text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="py-3 px-2 text-gray-900 dark:text-white font-medium">{u.name || '—'}</td>
                  <td className="py-3 px-2 text-gray-600 dark:text-gray-300">{u.email}</td>
                  <td className="py-3 px-2 text-center">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      u.role === 'admin'
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                        : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-center text-gray-600 dark:text-gray-300">{u.activity_count}</td>
                  <td className="py-3 px-2 text-center text-gray-600 dark:text-gray-300">{u.roleplay_count}</td>
                  <td className="py-3 px-2 text-center text-gray-600 dark:text-gray-300">{u.sahayak_count}</td>
                  <td className="py-3 px-2 text-gray-500 dark:text-gray-400 text-xs">
                    {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                  </td>
                  <td className="py-3 px-2 text-center">
                    <button
                      onClick={() => handleRoleChange(u.id, u.role === 'admin' ? 'user' : 'admin')}
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                        u.role === 'admin'
                          ? 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-red-900/20 dark:hover:text-red-400'
                          : 'bg-purple-50 text-purple-600 hover:bg-purple-100 dark:bg-purple-900/20 dark:text-purple-400 dark:hover:bg-purple-900/40'
                      }`}
                    >
                      {u.role === 'admin' ? 'Remove Admin' : 'Make Admin'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
