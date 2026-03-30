import { useEffect, useState } from 'react'
import { User, Star, Plus, Trash2, X } from 'lucide-react'

interface Avatar {
  id: string
  name: string
  image_path: string
  is_default: boolean
  created_at: string
}

const avatarColors = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-teal-500',
  'bg-indigo-500',
  'bg-red-500',
]

function getInitials(name: string) {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getAvatarColor(name: string) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

export default function Avatars() {
  const [avatars, setAvatars] = useState<Avatar[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const fetchAvatars = () => {
    fetch('/api/avatars')
      .then((r) => r.json())
      .then((data) => {
        setAvatars(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchAvatars()
  }, [])

  const setDefault = async (id: string) => {
    await fetch(`/api/avatars/${id}/set-default`, { method: 'POST' })
    fetchAvatars()
  }

  const createAvatar = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await fetch('/api/avatars', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() }),
      })
      setNewName('')
      setShowModal(false)
      fetchAvatars()
    } finally {
      setCreating(false)
    }
  }

  const deleteAvatar = async (id: string) => {
    await fetch(`/api/avatars/${id}`, { method: 'DELETE' })
    setDeleteConfirm(null)
    fetchAvatars()
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <p className="text-xs md:text-sm text-gray-500 dark:text-gray-400">Manage your AI avatars for video generation</p>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-3 md:px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-xs md:text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Avatar
        </button>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center text-gray-500">
          <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p>Loading avatars...</p>
        </div>
      ) : avatars.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center text-gray-500">
          <User className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No avatars configured yet. Add an avatar to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {avatars.map((avatar) => (
            <div
              key={avatar.id}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
            >
              <div className="h-40 bg-gray-50 flex items-center justify-center relative">
                <div
                  className={`w-24 h-24 rounded-full ${getAvatarColor(avatar.name)} flex items-center justify-center`}
                >
                  <span className="text-3xl font-bold text-white">
                    {getInitials(avatar.name)}
                  </span>
                </div>
                {avatar.is_default && (
                  <span className="absolute top-3 right-3 flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 border border-yellow-200 px-2.5 py-1 rounded-full font-medium">
                    <Star className="w-3 h-3" fill="currentColor" />
                    Default
                  </span>
                )}
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900 dark:text-white text-sm md:text-base">{avatar.name}</h3>
                  <p className="text-xs text-gray-400">
                    {new Date(avatar.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center justify-between mt-3">
                  {!avatar.is_default ? (
                    <button
                      onClick={() => setDefault(avatar.id)}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Set as Default
                    </button>
                  ) : (
                    <span />
                  )}
                  {deleteConfirm === avatar.id ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => deleteAvatar(avatar.id)}
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
                      onClick={() => setDeleteConfirm(avatar.id)}
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

      {/* Add Avatar Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Add New Avatar</h3>
              <button
                onClick={() => {
                  setShowModal(false)
                  setNewName('')
                }}
                className="p-1 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Avatar Name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && createAvatar()}
                placeholder="e.g. Professional Male, Friendly Female"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                autoFocus
              />
              {newName.trim() && (
                <div className="mt-4 flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full ${getAvatarColor(newName.trim())} flex items-center justify-center`}
                  >
                    <span className="text-sm font-bold text-white">
                      {getInitials(newName.trim())}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500">Preview</span>
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowModal(false)
                  setNewName('')
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={createAvatar}
                disabled={!newName.trim() || creating}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
              >
                {creating ? 'Creating...' : 'Create Avatar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
