import { useState, useRef, useEffect, useCallback } from 'react'
import { Bot, Send, Mic, MicOff, Volume2, VolumeX, Square, GraduationCap, HelpCircle, Award } from 'lucide-react'
import { useVoice } from '../../hooks/useVoice'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

interface SahayakMiniChatProps {
  productId: string
  productName?: string
  mode: 'learn' | 'help' | 'coaching'
  /** For coaching mode: the roleplay session ID to analyze */
  roleplaySessionId?: string
  /** Callback when user is ready to start practice (learn mode) */
  onReady?: () => void
}

const MODE_CONFIG = {
  learn: {
    title: 'Study with Sahayak',
    subtitle: 'Product ke baare mein poochiye!',
    icon: GraduationCap,
    color: 'emerald',
    placeholder: 'Product ke baare mein kuch bhi poochiye...',
    suggestions: [
      'Benefits batao',
      'Process kya hai?',
      'Eligibility kya hai?',
      'Objections kaise handle karein?',
    ],
  },
  help: {
    title: 'Sahayak Help',
    subtitle: 'Quick product info',
    icon: HelpCircle,
    color: 'blue',
    placeholder: 'Quick question poochiye...',
    suggestions: [
      'Benefits kya hain?',
      'Eligibility batao',
      'Process kya hai?',
    ],
  },
  coaching: {
    title: 'Sahayak Coaching',
    subtitle: 'Performance review',
    icon: Award,
    color: 'purple',
    placeholder: 'Coaching ke baare mein poochiye...',
    suggestions: [
      'Main kya better kar sakta tha?',
      'Objection handling tips do',
      'Closing technique batao',
    ],
  },
}

export default function SahayakMiniChat({
  productId,
  productName,
  mode,
  roleplaySessionId,
  onReady,
}: SahayakMiniChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sahayakSessionId, setSahayakSessionId] = useState<string | null>(null)
  const [voiceMode, setVoiceMode] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const coachingFetched = useRef(false) // Prevent double-fire in strict mode
  const config = MODE_CONFIG[mode]

  const handleTranscriptReady = useCallback((text: string) => {
    setInput(text)
    sendMessage(text)
  }, [])

  const voice = useVoice({
    lang: 'hi-IN',
    autoSend: true,
    onTranscriptReady: handleTranscriptReady,
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Auto-start coaching analysis (with guard against double-fire)
  useEffect(() => {
    if (mode === 'coaching' && roleplaySessionId && !coachingFetched.current) {
      coachingFetched.current = true
      fetchCoaching()
    }
  }, [mode, roleplaySessionId])

  const fetchCoaching = async () => {
    if (!roleplaySessionId) return
    setSending(true)
    try {
      const res = await fetch('/api/roleplay/coaching', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: roleplaySessionId }),
      })
      if (res.ok) {
        const data = await res.json()
        setMessages([{ role: 'assistant', text: data.coaching }])
        // Only auto-play if voice mode is on
        if (voiceMode) {
          voice.speakText(data.coaching)
        }
      }
    } catch {} finally {
      setSending(false)
    }
  }

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || sending) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setSending(true)

    try {
      let responseText = ''

      if (mode === 'help') {
        const res = await fetch('/api/roleplay/sahayak-help', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: productId,
            question: msg,
            session_id: sahayakSessionId,
          }),
        })
        const data = await res.json()
        responseText = data.response
        if (data.session_id) setSahayakSessionId(data.session_id)
      } else {
        const res = await fetch('/api/agent/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sahayakSessionId,
            message: msg,
          }),
        })
        const data = await res.json()
        responseText = data.response
        setSahayakSessionId(data.session_id)
      }

      setMessages(prev => [...prev, { role: 'assistant', text: responseText }])
      // Only auto-play if voice mode is on
      if (voiceMode) {
        voice.speakText(responseText)
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

  const colorClasses = {
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', iconBg: 'bg-emerald-100', iconText: 'text-emerald-600', btn: 'bg-emerald-600 hover:bg-emerald-700' },
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', iconBg: 'bg-blue-100', iconText: 'text-blue-600', btn: 'bg-blue-600 hover:bg-blue-700' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', iconBg: 'bg-purple-100', iconText: 'text-purple-600', btn: 'bg-purple-600 hover:bg-purple-700' },
  }
  const c = colorClasses[config.color as keyof typeof colorClasses]
  const Icon = config.icon

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className={`px-4 py-3 ${c.bg} border-b ${c.border}`}>
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full ${c.iconBg} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${c.iconText}`} />
          </div>
          <div>
            <h3 className={`text-sm font-semibold ${c.text}`}>{config.title}</h3>
            <p className="text-xs text-gray-500">{productName || config.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && !sending ? (
          <div className="space-y-3 mt-2">
            <p className="text-xs text-gray-500 text-center">
              {mode === 'learn' && 'Product ke baare mein poochiye — main batati hoon!'}
              {mode === 'help' && 'Product ka koi bhi doubt poochiye!'}
              {mode === 'coaching' && 'Aapki performance analyze kar rahi hoon...'}
            </p>
            {mode !== 'coaching' && (
              <div className="space-y-2">
                {config.suggestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(q); sendMessage(q) }}
                    className={`w-full text-left px-3 py-2 text-xs rounded-lg border ${c.border} hover:${c.bg} transition-colors`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className={`w-6 h-6 rounded-full ${c.iconBg} flex items-center justify-center mr-1.5 mt-1 shrink-0`}>
                  <Bot className={`w-3.5 h-3.5 ${c.iconText}`} />
                </div>
              )}
              <div className="max-w-[85%]">
                <div className={`px-3 py-2 rounded-xl text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : `${c.bg} text-gray-900 border ${c.border}`
                }`}>
                  {msg.text}
                </div>
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => voice.speakText(msg.text, `mini-${i}`)}
                    className={`mt-1 p-1 rounded-full transition-colors ${
                      voice.speakingId === `mini-${i}`
                        ? `${c.iconText} ${c.iconBg}`
                        : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                    }`}
                    title="Play audio"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        {sending && (
          <div className="flex items-center gap-1.5">
            <div className={`w-6 h-6 rounded-full ${c.iconBg} flex items-center justify-center`}>
              <Bot className={`w-3.5 h-3.5 ${c.iconText}`} />
            </div>
            <div className={`px-3 py-2 ${c.bg} rounded-xl border ${c.border}`}>
              <div className="flex gap-1">
                <div className={`w-1.5 h-1.5 ${c.iconBg} rounded-full animate-bounce`} />
                <div className={`w-1.5 h-1.5 ${c.iconBg} rounded-full animate-bounce`} style={{ animationDelay: '150ms' }} />
                <div className={`w-1.5 h-1.5 ${c.iconBg} rounded-full animate-bounce`} style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {voice.isListening && (
          <div className="flex items-center justify-center py-2">
            <div className="flex flex-col items-center gap-1">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center animate-pulse">
                <Mic className="w-5 h-5 text-red-600" />
              </div>
              <p className="text-xs text-gray-500">Listening...</p>
              {voice.transcript && (
                <p className="text-xs text-gray-700 italic">"{voice.transcript}"</p>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-200">
        <div className="flex items-center gap-1.5">
          {voice.hasSpeechRecognition && (
            <button
              onClick={voice.toggleListening}
              className={`p-2 rounded-full transition-all ${
                voice.isListening
                  ? 'bg-red-500 text-white animate-pulse'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {voice.isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder={config.placeholder}
            disabled={sending || voice.isListening}
            className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
          />

          {voice.isSpeaking ? (
            <button onClick={voice.stopSpeaking} className="p-2 bg-red-500 text-white rounded-full animate-pulse" title="Stop speaking">
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className={`p-2 ${c.btn} text-white rounded-full disabled:opacity-50 transition-colors`}
            >
              <Send className="w-4 h-4" />
            </button>
          )}

          {/* Voice mode toggle */}
          <button
            onClick={() => setVoiceMode(!voiceMode)}
            className={`p-1.5 rounded-full transition-colors ${
              voiceMode ? `${c.iconBg} ${c.iconText}` : 'bg-gray-100 text-gray-400 hover:text-gray-600'
            }`}
            title={voiceMode ? 'Auto-play ON' : 'Auto-play OFF'}
          >
            {voiceMode ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Ready Button (learn mode only) */}
      {mode === 'learn' && onReady && (
        <div className="p-3 border-t border-gray-100">
          <button
            onClick={onReady}
            className="w-full py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium text-sm transition-colors"
          >
            Ready to Practice! →
          </button>
        </div>
      )}
    </div>
  )
}
