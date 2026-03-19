import { useState, useEffect, useRef } from 'react'
import { authFetch } from '../api/authFetch'
import {
  MessageSquare,
  Send,
  ArrowLeft,
  Clock,
  Trophy,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  User,
  BarChart3,
  History,
  Target,
  Trash2,
  Mic,
  MicOff,
  Volume2,
  Square,
  HelpCircle,
  X,
  GraduationCap,
  Award,
} from 'lucide-react'
import { useVoice } from '../hooks/useVoice'
import SahayakMiniChat from '../components/roleplay/SahayakMiniChat'

type Difficulty = 'easy' | 'medium' | 'hard'
type ViewState = 'setup' | 'learn' | 'chat' | 'results' | 'coaching' | 'history'

interface Message {
  role: 'partner' | 'customer'
  text: string
}

interface Persona {
  name: string
  personality: string
  scenario_intro: string
}

interface ProductItem {
  id: string
  name: string
  category_name: string
  payout: string | null
  description: string | null
}

interface SkillScores {
  product_knowledge: number
  communication: number
  objection_handling: number
  closing_skills: number
  empathy: number
}

interface SessionResults {
  overall_score: number
  skill_scores: SkillScores
  feedback: string
  strengths: string[]
  improvements: string[]
}

interface HistoryItem {
  id: string
  product_id: string
  product_name: string
  difficulty: string
  overall_score: number | null
  skill_scores: Record<string, number> | null
  feedback: string | null
  duration_seconds: number | null
  created_at: string
}

const SKILL_LABELS: Record<string, string> = {
  product_knowledge: 'Product Knowledge',
  communication: 'Communication',
  objection_handling: 'Objection Handling',
  closing_skills: 'Closing Skills',
  empathy: 'Empathy',
}

export default function RoleplayPractice() {
  const [view, setView] = useState<ViewState>('setup')
  const [products, setProducts] = useState<ProductItem[]>([])
  const [selectedProduct, setSelectedProduct] = useState<string>('')
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [sessionId, setSessionId] = useState<string>('')
  const [persona, setPersona] = useState<Persona | null>(null)
  const [conversation, setConversation] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [buyingSignal, setBuyingSignal] = useState(0)
  const [sentiment, setSentiment] = useState<string>('neutral')
  const [turnNumber, setTurnNumber] = useState(0)
  const [results, setResults] = useState<SessionResults | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [startError, setStartError] = useState('')
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<HistoryItem | null>(null)
  const [deletingSession, setDeletingSession] = useState<string | null>(null)
  const [deletingAll, setDeletingAll] = useState(false)
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false)

  // New state for Sahayak integration
  const [voiceMode, setVoiceMode] = useState(false)
  const [showHelpPanel, setShowHelpPanel] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)

  // Voice hook for voice roleplay
  const handleTranscriptReady = (text: string) => {
    setInput(text)
    doSendMessage(text)
  }

  const voice = useVoice({
    lang: 'hi-IN',
    autoSend: true,
    onTranscriptReady: handleTranscriptReady,
  })

  const difficulties: { value: Difficulty; label: string; desc: string; color: string; bgColor: string }[] = [
    { value: 'easy', label: 'Easy', desc: 'Interested customer, ready to buy', color: 'border-green-500 bg-green-50', bgColor: 'bg-green-500' },
    { value: 'medium', label: 'Medium', desc: 'Cautious customer, needs convincing', color: 'border-yellow-500 bg-yellow-50', bgColor: 'bg-yellow-500' },
    { value: 'hard', label: 'Hard', desc: 'Skeptical customer, has objections', color: 'border-red-500 bg-red-50', bgColor: 'bg-red-500' },
  ]

  useEffect(() => { fetchProducts() }, [])
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [conversation])

  const fetchProducts = () => {
    authFetch('/api/products').then(r => r.json()).then((data: ProductItem[]) => {
      setProducts(data)
      if (data.length > 0 && !selectedProduct) setSelectedProduct(data[0].id)
    }).catch(() => {})
  }

  const fetchHistory = () => {
    authFetch('/api/roleplay/history').then(r => r.json()).then(setHistory).catch(() => {})
  }

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this roleplay session?')) return
    setDeletingSession(id)
    try {
      await authFetch(`/api/roleplay/${id}`, { method: 'DELETE' })
      if (selectedHistoryItem?.id === id) setSelectedHistoryItem(null)
      fetchHistory()
    } finally { setDeletingSession(null) }
  }

  const deleteAllSessions = async () => {
    setDeletingAll(true)
    try {
      await authFetch('/api/roleplay', { method: 'DELETE' })
      setHistory([])
      setSelectedHistoryItem(null)
    } finally { setDeletingAll(false); setShowDeleteAllConfirm(false) }
  }

  const selectedProductData = products.find(p => p.id === selectedProduct)

  const startLearnPhase = () => {
    if (!selectedProduct) return
    setView('learn')
  }

  const startSession = async () => {
    if (!selectedProduct) return
    setLoading(true)
    setStartError('')
    try {
      const res = await authFetch('/api/roleplay/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: selectedProduct, difficulty }),
      })
      if (!res.ok) throw new Error('Failed to start session')
      const data = await res.json()
      setSessionId(data.session_id)
      setPersona(data.persona)
      setConversation([{ role: 'customer', text: data.first_message }])
      setBuyingSignal(0)
      setSentiment('neutral')
      setTurnNumber(0)
      setResults(null)
      setShowHelpPanel(false)
      setView('chat')

      // Speak the first customer message in voice mode
      if (voiceMode) {
        voice.speakText(data.first_message)
      }
    } catch {
      setStartError('Failed to start roleplay session. Please try again.')
    } finally { setLoading(false) }
  }

  const doSendMessage = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || sending) return
    setInput('')
    setConversation(prev => [...prev, { role: 'partner', text: msg }])
    setSending(true)
    try {
      const res = await authFetch('/api/roleplay/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msg }),
      })
      if (!res.ok) throw new Error('Failed to send message')
      const data = await res.json()
      setConversation(prev => [...prev, { role: 'customer', text: data.response }])
      setBuyingSignal(Math.round(data.buying_signal * 100))
      setSentiment(data.sentiment)
      setTurnNumber(data.turn_number)

      // Speak customer response in voice mode
      if (voiceMode) {
        voice.speakText(data.response)
      }
    } catch {
      setConversation(prev => [...prev, { role: 'customer', text: 'Sorry, kuch technical problem ho gayi. Phir se try karo.' }])
    } finally { setSending(false) }
  }

  const endSession = async () => {
    setLoading(true)
    try {
      const res = await authFetch('/api/roleplay/end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      if (!res.ok) throw new Error('Failed to end session')
      const data = await res.json()
      setResults(data)
      setView('results')
    } catch {} finally { setLoading(false) }
  }

  const openHistory = () => { fetchHistory(); setSelectedHistoryItem(null); setView('history') }

  const resetToSetup = () => {
    setView('setup'); setSessionId(''); setPersona(null); setConversation([])
    setBuyingSignal(0); setSentiment('neutral'); setTurnNumber(0)
    setResults(null); setSelectedHistoryItem(null); setShowHelpPanel(false)
  }

  const sentimentEmoji = () => {
    if (sentiment === 'positive') return { icon: '●', color: 'text-green-500', label: 'Positive' }
    if (sentiment === 'negative') return { icon: '●', color: 'text-red-500', label: 'Negative' }
    return { icon: '●', color: 'text-yellow-500', label: 'Neutral' }
  }

  const scoreColor = (s: number) => s > 7 ? 'text-green-600' : s > 4 ? 'text-yellow-600' : 'text-red-600'
  const scoreBgColor = (s: number) => s > 7 ? 'bg-green-500' : s > 4 ? 'bg-yellow-500' : 'bg-red-500'
  const scoreBarBg = (s: number) => s > 7 ? 'bg-green-100' : s > 4 ? 'bg-yellow-100' : 'bg-red-100'

  // ═══════════════════════════════════════════════════════════════════════════
  // SETUP SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'setup') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-primary-600" />
          <h2 className="text-xl font-bold text-gray-900">Sales Roleplay Practice</h2>
          <p className="text-gray-500 mt-2">Practice selling financial products to an AI customer</p>
        </div>

        {/* Product Selection */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Select Product</h3>
          {products.length === 0 ? (
            <p className="text-sm text-gray-500">No products available. Sync from Products page.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-60 overflow-y-auto">
              {products.map(p => (
                <button key={p.id} onClick={() => setSelectedProduct(p.id)}
                  className={`p-3 rounded-xl border-2 text-left transition-all ${selectedProduct === p.id ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <h4 className="font-medium text-gray-900 text-sm truncate">{p.name}</h4>
                  <p className="text-xs text-gray-500 mt-0.5">{p.category_name}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Difficulty */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Select Difficulty</h3>
          <div className="space-y-3">
            {difficulties.map(d => (
              <button key={d.value} onClick={() => setDifficulty(d.value)}
                className={`w-full p-4 rounded-xl border-2 text-left transition-all ${difficulty === d.value ? d.color : 'border-gray-200 hover:border-gray-300'}`}>
                <h4 className="font-medium text-gray-900">{d.label}</h4>
                <p className="text-sm text-gray-500">{d.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Voice Mode Toggle */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Voice Mode</h3>
              <p className="text-sm text-gray-500 mt-1">Speak to the AI customer and hear voice responses</p>
            </div>
            <button onClick={() => setVoiceMode(!voiceMode)}
              className={`relative w-12 h-6 rounded-full transition-colors ${voiceMode ? 'bg-emerald-500' : 'bg-gray-300'}`}>
              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${voiceMode ? 'translate-x-6' : 'translate-x-0.5'}`} />
            </button>
          </div>
          {voiceMode && voice.hasSpeechRecognition && (
            <p className="text-xs text-emerald-600 mt-2 flex items-center gap-1"><Mic className="w-3 h-3" /> Voice input + TTS output enabled</p>
          )}
        </div>

        {startError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{startError}</div>}

        {/* Actions */}
        <div className="flex gap-3">
          <button onClick={startLearnPhase} disabled={!selectedProduct || loading}
            className="flex-1 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            <GraduationCap className="w-5 h-5" />
            {loading ? 'Starting...' : 'Learn & Practice'}
          </button>
          <button onClick={startSession} disabled={!selectedProduct || loading}
            className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50 transition-colors">
            {loading ? 'Starting...' : 'Skip to Practice'}
          </button>
          <button onClick={openHistory}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors">
            <History className="w-5 h-5" />
          </button>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LEARN PHASE
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'learn') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 10rem)' }}>
          <div className="flex items-center justify-between px-4 py-3 bg-emerald-50 border-b border-emerald-200">
            <div className="flex items-center gap-2">
              <button onClick={resetToSetup} className="p-1 hover:bg-emerald-100 rounded">
                <ArrowLeft className="w-4 h-4 text-emerald-700" />
              </button>
              <GraduationCap className="w-5 h-5 text-emerald-600" />
              <div>
                <h2 className="text-sm font-semibold text-emerald-800">Study Phase</h2>
                <p className="text-xs text-emerald-600">{selectedProductData?.name || 'Product'} — Ask Sahayak anything!</p>
              </div>
            </div>
            <button onClick={startSession} disabled={loading}
              className="px-4 py-1.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors">
              {loading ? 'Starting...' : 'Start Practice →'}
            </button>
          </div>
          <div style={{ height: 'calc(100% - 52px)' }}>
            <SahayakMiniChat
              productId={selectedProduct}
              productName={selectedProductData?.name}
              mode="learn"
              onReady={startSession}
            />
          </div>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // CHAT INTERFACE (with voice + help panel)
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'chat') {
    const sentimentInfo = sentimentEmoji()

    return (
      <div className="flex gap-4 h-[calc(100vh-10rem)]">
        {/* Main Chat */}
        <div className={`flex flex-col bg-white rounded-xl shadow-sm border border-gray-200 transition-all ${showHelpPanel ? 'flex-1' : 'w-full'}`}>
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center ${voice.isSpeaking ? 'animate-pulse ring-2 ring-orange-300' : ''}`}>
                  <User className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{persona?.name || 'Customer'}</h3>
                  <p className="text-xs text-gray-500">{persona?.personality || ''}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className={`text-lg ${sentimentInfo.color}`}>{sentimentInfo.icon}</span>
                  <span>{sentimentInfo.label}</span>
                </div>
                <span className="text-xs text-gray-500">Turn {turnNumber}</span>

                {/* Voice toggle */}
                <button onClick={() => setVoiceMode(!voiceMode)} title={voiceMode ? 'Voice ON' : 'Voice OFF'}
                  className={`p-1.5 rounded-lg transition-colors ${voiceMode ? 'bg-emerald-100 text-emerald-600' : 'text-gray-400 hover:text-gray-600'}`}>
                  <Volume2 className="w-4 h-4" />
                </button>

                {/* Help button */}
                <button onClick={() => setShowHelpPanel(!showHelpPanel)} title="Ask Sahayak"
                  className={`p-1.5 rounded-lg transition-colors ${showHelpPanel ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'}`}>
                  <HelpCircle className="w-4 h-4" />
                </button>

                <button onClick={endSession} disabled={loading}
                  className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg font-medium border border-red-200 transition-colors disabled:opacity-50">
                  {loading ? 'Ending...' : 'End'}
                </button>
              </div>
            </div>

            {/* Buying Signal Meter */}
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span className="flex items-center gap-1"><Target className="w-3 h-3" /> Buying Signal</span>
                <span className="font-medium">{buyingSignal}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className={`h-2 rounded-full transition-all duration-500 ${buyingSignal >= 70 ? 'bg-green-500' : buyingSignal >= 40 ? 'bg-yellow-500' : 'bg-red-400'}`}
                  style={{ width: `${buyingSignal}%` }} />
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {conversation.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'partner' ? 'justify-end' : 'justify-start'} animate-fadeIn`}>
                {msg.role === 'customer' && (
                  <div className={`w-7 h-7 rounded-full bg-orange-100 flex items-center justify-center mr-2 mt-1 shrink-0 ${voice.isSpeaking && i === conversation.length - 1 && msg.role === 'customer' ? 'animate-pulse ring-2 ring-orange-300' : ''}`}>
                    <User className="w-3.5 h-3.5 text-orange-600" />
                  </div>
                )}
                <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${msg.role === 'partner' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                  {msg.text}
                </div>
                {/* Replay button for customer messages */}
                {msg.role === 'customer' && voiceMode && (
                  <button onClick={() => voice.speakText(msg.text, `rp-${i}`)}
                    className="p-1 ml-1 mt-1 text-gray-300 hover:text-orange-500 rounded-full self-start">
                    <Volume2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
            {sending && (
              <div className="flex justify-start animate-fadeIn">
                <div className="w-7 h-7 rounded-full bg-orange-100 flex items-center justify-center mr-2 mt-1 shrink-0">
                  <User className="w-3.5 h-3.5 text-orange-600" />
                </div>
                <div className="bg-gray-100 rounded-2xl px-4 py-2.5 text-sm text-gray-500">
                  <span className="inline-flex gap-1">
                    <span className="animate-bounce">.</span>
                    <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
                  </span>
                </div>
              </div>
            )}

            {/* Listening indicator */}
            {voice.isListening && (
              <div className="flex items-center justify-center py-4">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center animate-pulse">
                    <Mic className="w-7 h-7 text-red-600" />
                  </div>
                  <p className="text-sm text-gray-500">Listening... Boliye!</p>
                  {voice.transcript && <p className="text-sm text-gray-700 italic">"{voice.transcript}"</p>}
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center gap-2">
              {/* Mic button (voice mode) */}
              {voiceMode && voice.hasSpeechRecognition && (
                <button onClick={voice.toggleListening}
                  className={`p-2.5 rounded-full transition-all ${voice.isListening ? 'bg-red-500 text-white shadow-lg shadow-red-200 animate-pulse' : 'bg-gray-100 text-gray-600 hover:bg-emerald-100 hover:text-emerald-600'}`}>
                  {voice.isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                </button>
              )}

              <input type="text" value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doSendMessage()}
                placeholder={voice.isListening ? 'Listening...' : voiceMode ? 'Speak or type...' : 'Type your sales pitch...'}
                disabled={sending || voice.isListening}
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50" />

              {voice.isSpeaking ? (
                <button onClick={voice.stopSpeaking} className="p-2.5 bg-red-500 text-white rounded-full animate-pulse" title="Stop speaking">
                  <Square className="w-4 h-4" />
                </button>
              ) : (
                <button onClick={() => doSendMessage()} disabled={!input.trim() || sending}
                  className="p-2.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 transition-colors">
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">
              {voiceMode ? '🎤 Voice mode — Speak naturally or type' : 'Tip: Mention features, pricing, eligibility to score higher'}
            </p>
          </div>
        </div>

        {/* Sahayak Help Panel */}
        {showHelpPanel && (
          <div className="w-80 bg-white rounded-xl shadow-sm border border-blue-200 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-blue-50 border-b border-blue-200">
              <div className="flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-semibold text-blue-700">Sahayak Help</span>
              </div>
              <button onClick={() => setShowHelpPanel(false)} className="p-1 hover:bg-blue-100 rounded">
                <X className="w-4 h-4 text-blue-600" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <SahayakMiniChat
                productId={selectedProduct}
                productName={selectedProductData?.name}
                mode="help"
              />
            </div>
          </div>
        )}
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RESULTS SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'results' && results) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Overall Score */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <Trophy className="w-10 h-10 mx-auto mb-3 text-yellow-500" />
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Session Complete</h2>
          <div className={`text-6xl font-bold ${scoreColor(results.overall_score)}`}>{results.overall_score}</div>
          <p className="text-sm text-gray-500 mt-1">out of 10</p>
          <div className="mt-3 flex items-center justify-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${results.overall_score > 7 ? 'bg-green-100 text-green-700' : results.overall_score > 4 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
              {results.overall_score > 7 ? 'Excellent' : results.overall_score > 4 ? 'Good' : 'Needs Improvement'}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 capitalize">{difficulty}</span>
          </div>
        </div>

        {/* Skill Scores */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-600" /> Skill Breakdown
          </h3>
          <div className="space-y-4">
            {Object.entries(results.skill_scores).map(([key, val]) => (
              <div key={key}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-700 font-medium">{SKILL_LABELS[key] || key}</span>
                  <span className={`font-bold ${scoreColor(val)}`}>{val}/10</span>
                </div>
                <div className={`w-full rounded-full h-2.5 ${scoreBarBg(val)}`}>
                  <div className={`h-2.5 rounded-full transition-all duration-700 ${scoreBgColor(val)}`} style={{ width: `${val * 10}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feedback */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-3">Feedback</h3>
          <p className="text-sm text-gray-600 leading-relaxed">{results.feedback}</p>
        </div>

        {/* Strengths & Improvements */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.strengths.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-semibold text-green-700 mb-3 flex items-center gap-2"><CheckCircle className="w-4 h-4" /> Strengths</h3>
              <ul className="space-y-2">
                {results.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2"><span className="text-green-500 mt-0.5 shrink-0">+</span>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {results.improvements.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-semibold text-orange-700 mb-3 flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Areas for Improvement</h3>
              <ul className="space-y-2">
                {results.improvements.map((s, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2"><span className="text-orange-500 mt-0.5 shrink-0">-</span>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button onClick={() => setView('coaching')}
            className="flex-1 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium transition-colors flex items-center justify-center gap-2">
            <Award className="w-5 h-5" /> Get Coaching from Sahayak
          </button>
          <button onClick={startSession} disabled={loading}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium disabled:opacity-50 transition-colors">
            Practice Again
          </button>
          <button onClick={resetToSetup}
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors">
            New Product
          </button>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // COACHING SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'coaching') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 10rem)' }}>
          <div className="flex items-center justify-between px-4 py-3 bg-purple-50 border-b border-purple-200">
            <div className="flex items-center gap-2">
              <button onClick={() => setView('results')} className="p-1 hover:bg-purple-100 rounded">
                <ArrowLeft className="w-4 h-4 text-purple-700" />
              </button>
              <Award className="w-5 h-5 text-purple-600" />
              <div>
                <h2 className="text-sm font-semibold text-purple-800">Sahayak Coaching</h2>
                <p className="text-xs text-purple-600">{selectedProductData?.name || 'Product'} — Performance Review</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={startSession} disabled={loading}
                className="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors">
                Practice Again
              </button>
              <button onClick={resetToSetup}
                className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors">
                New Product
              </button>
            </div>
          </div>
          <div style={{ height: 'calc(100% - 52px)' }}>
            <SahayakMiniChat
              productId={selectedProduct}
              productName={selectedProductData?.name}
              mode="coaching"
              roleplaySessionId={sessionId}
            />
          </div>
        </div>
      </div>
    )
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // HISTORY SCREEN
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'history') {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={resetToSetup} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Session History</h2>
              <p className="text-sm text-gray-500">Your past roleplay practice sessions</p>
            </div>
          </div>
          {history.length > 0 && (
            <div>
              {showDeleteAllConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-red-600 font-medium">Delete all?</span>
                  <button onClick={deleteAllSessions} disabled={deletingAll}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50">
                    {deletingAll ? 'Deleting...' : 'Yes'}
                  </button>
                  <button onClick={() => setShowDeleteAllConfirm(false)}
                    className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setShowDeleteAllConfirm(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-lg">
                  <Trash2 className="w-3.5 h-3.5" /> Clear All
                </button>
              )}
            </div>
          )}
        </div>

        {history.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <History className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">No sessions yet. Start practicing!</p>
          </div>
        ) : (
          <div className="flex gap-6">
            <div className={`space-y-3 ${selectedHistoryItem ? 'w-1/2' : 'w-full'}`}>
              {history.map(item => (
                <button key={item.id} onClick={() => setSelectedHistoryItem(item)}
                  className={`w-full bg-white rounded-xl shadow-sm border p-4 text-left transition-all hover:shadow ${selectedHistoryItem?.id === item.id ? 'border-primary-500 bg-primary-50' : 'border-gray-200'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">{item.product_name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${item.difficulty === 'easy' ? 'bg-green-100 text-green-700' : item.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                          {item.difficulty}
                        </span>
                        <span className="text-xs text-gray-400 flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(item.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={(e) => deleteSession(item.id, e)} disabled={deletingSession === item.id}
                        className="p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 disabled:opacity-50">
                        <Trash2 className={`w-3.5 h-3.5 ${deletingSession === item.id ? 'animate-pulse' : ''}`} />
                      </button>
                      <div className="text-right">
                        {item.overall_score != null ? (
                          <span className={`text-2xl font-bold ${scoreColor(item.overall_score)}`}>{item.overall_score}</span>
                        ) : (
                          <span className="text-sm text-gray-400 flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" />No score</span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {selectedHistoryItem && (
              <div className="w-1/2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-h-[calc(100vh-14rem)] overflow-y-auto">
                <h3 className="font-semibold text-gray-900 mb-1">{selectedHistoryItem.product_name}</h3>
                <div className="flex items-center gap-2 mb-4">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${selectedHistoryItem.difficulty === 'easy' ? 'bg-green-100 text-green-700' : selectedHistoryItem.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                    {selectedHistoryItem.difficulty}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(selectedHistoryItem.created_at).toLocaleString()}</span>
                </div>
                {selectedHistoryItem.overall_score != null && (
                  <div className="text-center mb-6 py-4 bg-gray-50 rounded-lg">
                    <div className={`text-4xl font-bold ${scoreColor(selectedHistoryItem.overall_score)}`}>{selectedHistoryItem.overall_score}</div>
                    <p className="text-xs text-gray-500 mt-1">Overall Score</p>
                  </div>
                )}
                {selectedHistoryItem.skill_scores && (
                  <div className="space-y-3 mb-6">
                    <h4 className="text-sm font-semibold text-gray-700">Skills</h4>
                    {Object.entries(selectedHistoryItem.skill_scores).map(([key, val]) => (
                      <div key={key}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-gray-600">{SKILL_LABELS[key] || key}</span>
                          <span className={`font-bold ${scoreColor(val)}`}>{val}/10</span>
                        </div>
                        <div className={`w-full rounded-full h-2 ${scoreBarBg(val)}`}>
                          <div className={`h-2 rounded-full ${scoreBgColor(val)}`} style={{ width: `${val * 10}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {selectedHistoryItem.feedback && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Feedback</h4>
                    <p className="text-sm text-gray-600 leading-relaxed">{selectedHistoryItem.feedback}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return null
}
