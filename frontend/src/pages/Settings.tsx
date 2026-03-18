import { useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'

interface AppSettings {
  gromo_api_base_url: string
  gromo_api_client_id_set: boolean
  gromo_api_secret_key_set: boolean
  gromo_api_gpuid: string
  excluded_categories: string
  llm_provider: string
  ollama_base_url: string
  ollama_model: string
  openai_api_key_set: boolean
  tts_provider: string
  sarvam_api_key_set: boolean
  elevenlabs_api_key_set: boolean
  avatar_provider: string
  heygen_api_key_set: boolean
  default_language: string
  default_resolution: string
  default_video_speed: number
  storage_backend: string
}

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
      <Check className="w-3 h-3" /> Configured
    </span>
  ) : (
    <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-1 rounded-full">
      <X className="w-3 h-3" /> Not Set
    </span>
  )
}

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null)

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then(setSettings)
      .catch(() => {})
  }, [])

  if (!settings) {
    return <div className="text-center py-12 text-gray-500">Loading settings...</div>
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* GroMo API */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">GroMo API Configuration</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">API Base URL</p>
              <p className="text-sm text-gray-500">{settings.gromo_api_base_url}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">Client ID</p>
            <StatusBadge active={settings.gromo_api_client_id_set} />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-700">Secret Key</p>
            <StatusBadge active={settings.gromo_api_secret_key_set} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">GP UID</p>
              <p className="text-sm text-gray-500">{settings.gromo_api_gpuid}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Excluded Categories</p>
              <p className="text-sm text-gray-500">{settings.excluded_categories}</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Providers */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">AI Providers</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">LLM Provider (Scripts, Roleplay, Doubts)</p>
              <p className="text-sm text-gray-500 capitalize">{settings.llm_provider}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">OpenAI API Key</p>
            </div>
            <StatusBadge active={settings.openai_api_key_set} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">TTS Provider (Audio)</p>
              <p className="text-sm text-gray-500 capitalize">{settings.tts_provider}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Sarvam AI API Key</p>
            </div>
            <StatusBadge active={settings.sarvam_api_key_set} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Avatar / Visual Provider</p>
              <p className="text-sm text-gray-500 capitalize">{settings.avatar_provider}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Defaults */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Default Settings</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Language</p>
            <p className="text-sm text-gray-500 capitalize">{settings.default_language}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Resolution</p>
            <p className="text-sm text-gray-500">{settings.default_resolution}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Video Speed</p>
            <p className="text-sm text-gray-500">{settings.default_video_speed}x</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Storage</p>
            <p className="text-sm text-gray-500 capitalize">{settings.storage_backend}</p>
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-400 text-center">
        Settings are configured via environment variables. Edit .env file to change.
      </p>
    </div>
  )
}
