import { useEffect, useState } from 'react'
import {
  ListVideo,
  Download,
  RotateCw,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
} from 'lucide-react'

interface VideoJob {
  id: string
  title: string
  job_type: string
  status: string
  progress: number
  error_message?: string
  created_at: string
  completed_at: string | null
  video_path: string | null
}

interface LogEntry {
  timestamp: string
  level: string
  message: string
}

type FilterTab = 'all' | 'in_progress' | 'completed' | 'failed'

const statusColors: Record<string, string> = {
  queued: 'bg-gray-100 text-gray-700',
  generating_script: 'bg-blue-100 text-blue-700',
  generating_audio: 'bg-indigo-100 text-indigo-700',
  generating_avatar: 'bg-purple-100 text-purple-700',
  compositing: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

const statusProgressColors: Record<string, string> = {
  queued: 'bg-gray-400',
  generating_script: 'bg-blue-500',
  generating_audio: 'bg-indigo-500',
  generating_avatar: 'bg-purple-500',
  compositing: 'bg-yellow-500',
}

const jobTypeBadgeColors: Record<string, string> = {
  single_product: 'bg-blue-50 text-blue-700',
  category_overview: 'bg-green-50 text-green-700',
  comparison: 'bg-purple-50 text-purple-700',
  ppt_mode: 'bg-orange-50 text-orange-700',
}

const inProgressStatuses = [
  'queued',
  'generating_script',
  'generating_audio',
  'generating_avatar',
  'compositing',
]

const filterTabs: { key: FilterTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'all', label: 'All', icon: ListVideo },
  { key: 'in_progress', label: 'In Progress', icon: Loader2 },
  { key: 'completed', label: 'Completed', icon: CheckCircle },
  { key: 'failed', label: 'Failed', icon: XCircle },
]

export default function VideoQueue() {
  const [jobs, setJobs] = useState<VideoJob[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterTab>('all')
  const [expandedLogs, setExpandedLogs] = useState<Record<string, LogEntry[]>>({})
  const [loadingLogs, setLoadingLogs] = useState<Record<string, boolean>>({})
  const [retrying, setRetrying] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deletingAll, setDeletingAll] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const fetchJobs = () => {
    fetch('/api/video-jobs')
      .then((r) => r.json())
      .then((data) => {
        setJobs(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchJobs()
    const interval = setInterval(fetchJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  const retryJob = async (id: string) => {
    setRetrying(id)
    try {
      await fetch(`/api/video-jobs/${id}/retry`, { method: 'POST' })
      fetchJobs()
    } finally {
      setRetrying(null)
    }
  }

  const deleteJob = async (id: string) => {
    if (!confirm('Are you sure you want to delete this video job and its files?')) return
    setDeleting(id)
    try {
      await fetch(`/api/video-jobs/${id}`, { method: 'DELETE' })
      fetchJobs()
    } finally {
      setDeleting(null)
    }
  }

  const deleteAllJobs = async () => {
    setDeletingAll(true)
    try {
      await fetch('/api/video-jobs', { method: 'DELETE' })
      fetchJobs()
    } finally {
      setDeletingAll(false)
      setShowDeleteConfirm(false)
    }
  }

  const toggleLogs = async (id: string) => {
    if (expandedLogs[id]) {
      setExpandedLogs((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
      return
    }
    setLoadingLogs((prev) => ({ ...prev, [id]: true }))
    try {
      const res = await fetch(`/api/video-jobs/${id}/logs`)
      const data = await res.json()
      setExpandedLogs((prev) => ({ ...prev, [id]: Array.isArray(data) ? data : [] }))
    } catch {
      setExpandedLogs((prev) => ({ ...prev, [id]: [] }))
    } finally {
      setLoadingLogs((prev) => ({ ...prev, [id]: false }))
    }
  }

  const filteredJobs = jobs.filter((job) => {
    if (filter === 'all') return true
    if (filter === 'in_progress') return inProgressStatuses.includes(job.status)
    if (filter === 'completed') return job.status === 'completed'
    if (filter === 'failed') return job.status === 'failed'
    return true
  })

  const getCounts = () => ({
    all: jobs.length,
    in_progress: jobs.filter((j) => inProgressStatuses.includes(j.status)).length,
    completed: jobs.filter((j) => j.status === 'completed').length,
    failed: jobs.filter((j) => j.status === 'failed').length,
  })

  const counts = getCounts()

  return (
    <div className="space-y-6">
      {/* Filter Tabs + Clear All */}
      <div className="flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-2">
        <div className="flex items-center gap-2">
          {filterTabs.map((tab) => {
            const Icon = tab.icon
            const count = counts[tab.key]
            return (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === tab.key
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                <span
                  className={`px-1.5 py-0.5 rounded-full text-xs ${
                    filter === tab.key
                      ? 'bg-white/20 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>
        {jobs.length > 0 && (
          <div className="relative">
            {showDeleteConfirm ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-red-600 font-medium">Delete all?</span>
                <button
                  onClick={deleteAllJobs}
                  disabled={deletingAll}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {deletingAll ? 'Deleting...' : 'Yes, Delete All'}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear All
              </button>
            )}
          </div>
        )}
      </div>

      {/* Jobs List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-500">
            <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p>Loading video jobs...</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <ListVideo className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>
              {filter === 'all'
                ? 'No video jobs in the queue. Go to Video Studio to create one.'
                : `No ${filter.replace('_', ' ')} jobs.`}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredJobs.map((job) => {
              const isInProgress = inProgressStatuses.includes(job.status)
              const isExpanded = !!expandedLogs[job.id]
              const isLoadingLogs = !!loadingLogs[job.id]

              return (
                <div key={job.id} className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-medium text-gray-900 truncate">{job.title}</h3>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-xs font-medium capitalize shrink-0 ${
                            jobTypeBadgeColors[job.job_type] || 'bg-gray-50 text-gray-700'
                          }`}
                        >
                          {job.job_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {new Date(job.created_at).toLocaleString()}
                        </span>
                        {job.completed_at && (
                          <span className="flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                            Completed {new Date(job.completed_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                          statusColors[job.status] || 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {job.status.replace(/_/g, ' ')}
                      </span>
                      {job.status === 'completed' && job.video_path && (
                        <a
                          href={job.video_path}
                          download
                          className="p-2 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
                          title="Download video"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      )}
                      {job.status === 'failed' && (
                        <button
                          onClick={() => retryJob(job.id)}
                          disabled={retrying === job.id}
                          className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 disabled:opacity-50 transition-colors"
                          title="Retry job"
                        >
                          <RotateCw
                            className={`w-4 h-4 ${retrying === job.id ? 'animate-spin' : ''}`}
                          />
                        </button>
                      )}
                      <button
                        onClick={() => deleteJob(job.id)}
                        disabled={deleting === job.id || isInProgress}
                        className="p-2 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30 transition-colors"
                        title={isInProgress ? 'Cannot delete while processing' : 'Delete job'}
                      >
                        <Trash2
                          className={`w-4 h-4 ${deleting === job.id ? 'animate-pulse' : ''}`}
                        />
                      </button>
                      <button
                        onClick={() => toggleLogs(job.id)}
                        className={`p-2 rounded-lg transition-colors ${
                          isExpanded
                            ? 'bg-primary-50 text-primary-600'
                            : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                        }`}
                        title="View logs"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Error Message */}
                  {job.status === 'failed' && job.error_message && (
                    <div className="flex items-start gap-2 mb-3 p-3 bg-red-50 rounded-lg">
                      <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                      <p className="text-sm text-red-700">{job.error_message}</p>
                    </div>
                  )}

                  {/* Progress Bar */}
                  {isInProgress && (
                    <div className="w-full bg-gray-100 rounded-full h-2.5 mb-1">
                      <div
                        className={`h-2.5 rounded-full transition-all duration-500 ${
                          statusProgressColors[job.status] || 'bg-primary-600'
                        } ${job.status !== 'queued' ? 'animate-pulse' : ''}`}
                        style={{ width: `${Math.max(job.progress, 5)}%` }}
                      />
                    </div>
                  )}
                  {isInProgress && (
                    <p className="text-xs text-gray-500 mt-1">{job.progress}% complete</p>
                  )}

                  {/* Logs Section */}
                  {isExpanded && (
                    <div className="mt-4 bg-gray-900 rounded-lg p-4 max-h-60 overflow-y-auto">
                      <h4 className="text-xs font-medium text-gray-400 uppercase mb-3">
                        Job Logs
                      </h4>
                      {isLoadingLogs ? (
                        <div className="text-center py-4">
                          <div className="w-5 h-5 border-2 border-gray-600 border-t-gray-400 rounded-full animate-spin mx-auto" />
                        </div>
                      ) : expandedLogs[job.id]?.length === 0 ? (
                        <p className="text-sm text-gray-500">No logs available for this job.</p>
                      ) : (
                        <div className="space-y-1 font-mono text-xs">
                          {expandedLogs[job.id]?.map((log, i) => (
                            <div key={i} className="flex items-start gap-2">
                              <span className="text-gray-500 shrink-0">
                                {new Date(log.timestamp).toLocaleTimeString()}
                              </span>
                              <span
                                className={`shrink-0 uppercase ${
                                  log.level === 'error'
                                    ? 'text-red-400'
                                    : log.level === 'warn'
                                      ? 'text-yellow-400'
                                      : 'text-green-400'
                                }`}
                              >
                                [{log.level}]
                              </span>
                              <span className="text-gray-300">{log.message}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
