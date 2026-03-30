import { useState, useRef, useEffect } from 'react'
import { authFetch } from '../api/authFetch'
import { Bot, Send, Mic, MicOff, Volume2, VolumeX, Trash2, History, Plus, X, Square } from 'lucide-react'
import { useVoice } from '../hooks/useVoice'

interface ProductMention {
  id: string
  name: string
  category_name: string
}

interface Message {
  role: 'user' | 'assistant'
  text: string
  products?: string[]
  timestamp?: string
}

interface SessionItem {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export default function TrainingAgent() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [voiceMode, setVoiceMode] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleTranscriptReady = (text: string) => {
    setInput(text)
    sendMessage(text)
  }

  const voice = useVoice({
    lang: 'hi-IN',
    autoSend: true,
    onTranscriptReady: handleTranscriptReady,
  })

  useEffect(() => {
    authFetch('/api/agent/suggestions')
      .then(r => r.json())
      .then(d => setSuggestions(d.suggestions || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || sending) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setSending(true)

    try {
      const res = await authFetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msg }),
      })
      const data = await res.json()

      setSessionId(data.session_id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.response,
        products: data.products_mentioned?.map((p: ProductMention) => p.name) || [],
      }])

      if (voiceMode) {
        voice.speakText(data.response)
      }
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Sorry, kuch error aa gaya. Please try again!',
      }])
    } finally {
      setSending(false)
    }
  }

  const loadHistory = async () => {
    try {
      const res = await authFetch('/api/agent/sessions')
      const data = await res.json()
      setSessions(data)
      setShowHistory(true)
    } catch {
      setSessions([])
    }
  }

  const loadSession = async (id: string) => {
    try {
      const res = await authFetch(`/api/agent/sessions/${id}`)
      const data = await res.json()
      setSessionId(id)
      setMessages(data.conversation_log?.messages || [])
      setShowHistory(false)
    } catch {}
  }

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this conversation?')) return
    await authFetch(`/api/agent/sessions/${id}`, { method: 'DELETE' })
    setSessions(prev => prev.filter(s => s.id !== id))
    if (sessionId === id) newChat()
  }

  const newChat = () => {
    setSessionId(null)
    setMessages([])
    setInput('')
    setShowHistory(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] md:h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 md:px-6 py-2 md:py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 md:gap-3 min-w-0">
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center shrink-0">
            <Bot className="w-5 h-5 md:w-6 md:h-6 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base md:text-lg font-semibold text-gray-900 dark:text-white">Sahayak</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">Training Assistant — Kuch bhi poochiye!</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 md:gap-2 shrink-0">
          <button onClick={newChat} className="flex items-center gap-1 md:gap-1.5 px-2 md:px-3 py-1.5 text-xs md:text-sm text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors">
            <Plus className="w-3.5 h-3.5 md:w-4 md:h-4" /> <span className="hidden sm:inline">New</span> Chat
          </button>
          <button onClick={loadHistory} className="flex items-center gap-1 md:gap-1.5 px-2 md:px-3 py-1.5 text-xs md:text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
            <History className="w-3.5 h-3.5 md:w-4 md:h-4" /> <span className="hidden sm:inline">History</span>
          </button>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="absolute inset-0 z-50 bg-white dark:bg-gray-800 flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversation History</h2>
            <button onClick={() => setShowHistory(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {sessions.length === 0 ? (
              <p className="text-center text-gray-400 mt-8">No conversations yet</p>
            ) : sessions.map(s => (
              <div
                key={s.id}
                onClick={() => loadSession(s.id)}
                className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 cursor-pointer transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{s.title || 'Untitled'}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{s.message_count} messages · {new Date(s.updated_at).toLocaleDateString()}</p>
                </div>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-3 md:px-6 py-3 md:py-4 space-y-3 md:space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <div className="w-20 h-20 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <Bot className="w-12 h-12 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="text-center">
              <h2 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">Namaste! Main hoon Sahayak</h2>
              <p className="text-sm md:text-base text-gray-500 dark:text-gray-400 mt-2 max-w-md">
                Aapka training assistant. Kisi bhi GroMo product ke baare mein poochiye —
                benefits, process, terms, ya comparison!
              </p>
            </div>
            {voice.hasSpeechRecognition && (
              <p className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <Mic className="w-4 h-4" /> Voice mode available — Mic button dabayein aur boliye!
              </p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
              {suggestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(q); sendMessage(q) }}
                  className="text-left p-3 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 hover:border-emerald-200 dark:hover:border-emerald-700 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mr-2 mt-1 flex-shrink-0">
                  <Bot className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              )}
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-md'
                    : 'bg-emerald-50 dark:bg-emerald-900/20 text-gray-900 dark:text-gray-100 border border-emerald-100 dark:border-emerald-800 rounded-bl-md'
                }`}>
                  {msg.text}
                </div>
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {msg.products?.map((p, j) => (
                      <span key={j} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                        {p}
                      </span>
                    ))}
                    <button
                      onClick={() => voice.speakText(msg.text, `msg-${i}`)}
                      className={`p-1 rounded-full transition-colors ${
                        voice.speakingId === `msg-${i}`
                          ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30'
                          : 'text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20'
                      }`}
                      title="Play audio"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {sending && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <Bot className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl rounded-bl-md border border-emerald-100 dark:border-emerald-800">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {voice.isListening && (
          <div className="flex items-center justify-center py-4">
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center animate-pulse">
                <Mic className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Listening... Boliye!</p>
              {voice.transcript && (
                <p className="text-sm text-gray-700 dark:text-gray-300 italic max-w-md text-center">"{voice.transcript}"</p>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-3 md:px-6 py-2 md:py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          {voice.hasSpeechRecognition && (
            <button
              onClick={voice.toggleListening}
              className={`p-2.5 rounded-full transition-all ${
                voice.isListening
                  ? 'bg-red-500 text-white shadow-lg shadow-red-200 dark:shadow-red-900/50 animate-pulse'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 hover:text-emerald-600 dark:hover:text-emerald-400'
              }`}
              title={voice.isListening ? 'Stop listening' : 'Start voice input'}
            >
              {voice.isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          )}

          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder={voice.isListening ? 'Listening...' : 'Type your question...'}
              disabled={sending || voice.isListening}
              className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:opacity-50"
            />
          </div>

          {voice.isSpeaking ? (
            <button
              onClick={voice.stopSpeaking}
              className="p-2.5 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors animate-pulse"
              title="Stop speaking"
            >
              <Square className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className="p-2.5 bg-emerald-600 text-white rounded-full hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          )}

          <button
            onClick={() => setVoiceMode(!voiceMode)}
            className={`p-2 rounded-full transition-colors ${
              voiceMode
                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
            }`}
            title={voiceMode ? 'Voice mode ON' : 'Voice mode OFF'}
          >
            {voiceMode ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
          </button>
        </div>

        <div className="flex items-center justify-center gap-4 mt-2 text-xs text-gray-400 dark:text-gray-500">
          <span className={voiceMode ? 'text-emerald-600 dark:text-emerald-400 font-medium' : ''}>
            {voiceMode ? '🔊 Voice mode — Responses will auto-play' : '💬 Text mode — Click 🔊 to enable voice'}
          </span>
        </div>
      </div>
    </div>
  )
}
