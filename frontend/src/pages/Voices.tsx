import { useEffect, useState } from 'react'
import { Mic, Star, Plus, Trash2, X } from 'lucide-react'

interface Voice {
  id: string
  name: string
  sample_path: string
  language: string
  is_default: boolean
  created_at: string
}

const languageBadgeColors: Record<string, string> = {
  hinglish: 'bg-purple-100 text-purple-700',
  hindi: 'bg-orange-100 text-orange-700',
  english: 'bg-blue-100 text-blue-700',
}

const languageOptions = [
  { value: 'hinglish', label: 'Hinglish' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'english', label: 'English' },
]

export default function Voices() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newLanguage, setNewLanguage] = useState('hinglish')
  const [creating, setCreating] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const fetchVoices = () => {
    fetch('/api/voices')
      .then((r) => r.json())
      .then((data) => {
        setVoices(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchVoices()
  }, [])

  const setDefault = async (id: string) => {
    await fetch(`/api/voices/${id}/set-default`, { method: 'POST' })
    fetchVoices()
  }

  const createVoice = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await fetch('/api/voices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), language: newLanguage }),
      })
      setNewName('')
      setNewLanguage('hinglish')
      setShowModal(false)
      fetchVoices()
    } finally {
      setCreating(false)
    }
  }

  const deleteVoice = async (id: string) => {
    await fetch(`/api/voices/${id}`, { method: 'DELETE' })
    setDeleteConfirm(null)
    fetchVoices()
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <p className="text-xs md:text-sm text-gray-500 dark:text-gray-400">Manage Indian Hinglish voices for narration</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-3 md:px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-xs md:text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Voice
        </button>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center text-gray-500">
          <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p>Loading voices...</p>
        </div>
      ) : voices.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center text-gray-500">
          <Mic className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No voices configured yet. Add a voice to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {voices.map((voice) => (
            <div
              key={voice.id}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
            >
              <div className="p-4 md:p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center">
                    <Mic className="w-6 h-6 text-primary-600" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                        languageBadgeColors[voice.language] || 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {voice.language}
                    </span>
                    {voice.is_default && (
                      <span className="flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 border border-yellow-200 px-2.5 py-1 rounded-full font-medium">
                        <Star className="w-3 h-3" fill="currentColor" />
                        Default
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="font-medium text-gray-900 dark:text-white text-base md:text-lg">{voice.name}</h3>
                <p className="text-xs text-gray-400 mt-1">
                  Added {new Date(voice.created_at).toLocaleDateString()}
                </p>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                  {!voice.is_default ? (
                    <button
                      onClick={() => setDefault(voice.id)}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Set as Default
                    </button>
                  ) : (
                    <span />
                  )}
                  {deleteConfirm === voice.id ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => deleteVoice(voice.id)}
                        className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 font-medium"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(null)}
                        className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirm(voice.id)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Voice Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Add New Voice</h3>
              <button
                onClick={() => {
                  setShowModal(false)
                  setNewName('')
                  setNewLanguage('hinglish')
                }}
                className="p-1 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Voice Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && createVoice()}
                  placeholder="e.g. Priya, Rahul, Ananya"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Language
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {languageOptions.map((lang) => (
                    <button
                      key={lang.value}
                      onClick={() => setNewLanguage(lang.value)}
                      className={`px-3 py-2 rounded-lg border-2 text-sm font-medium transition-all ${
                        newLanguage === lang.value
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowModal(false)
                  setNewName('')
                  setNewLanguage('hinglish')
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={createVoice}
                disabled={!newName.trim() || creating}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
              >
                {creating ? 'Creating...' : 'Create Voice'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
