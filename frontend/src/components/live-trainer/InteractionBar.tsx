import { useState } from 'react'
import {
  Pause,
  Play,
  Hand,
  Send,
  X,
  Mic,
  MicOff,
  Gauge,
} from 'lucide-react'
import type { SessionState, QuizSegment } from '../../hooks/useLiveSession'

interface InteractionBarProps {
  state: SessionState
  isPlaying: boolean
  isPaused: boolean
  playbackRate: number
  onPause: () => void
  onResume: () => void
  onRaiseHand: () => void
  onSubmitDoubt: (question: string) => void
  onCancelDoubt: () => void
  onChangeSpeed: (rate: number) => void
  onAnswerQuiz: (selectedIndex: number) => void
  quizQuestion?: QuizSegment | null
  onEndSession: () => void
}

const speeds = [1.0, 1.25, 1.5]

export default function InteractionBar({
  state,
  isPlaying,
  isPaused,
  playbackRate,
  onPause,
  onResume,
  onRaiseHand,
  onSubmitDoubt,
  onCancelDoubt,
  onChangeSpeed,
  onAnswerQuiz,
  quizQuestion,
  onEndSession,
}: InteractionBarProps) {
  const [doubtInput, setDoubtInput] = useState('')
  const [showSpeedMenu, setShowSpeedMenu] = useState(false)

  // Doubt input mode
  if (state === 'doubt_listening') {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <div className="flex items-center gap-2 mb-2">
          <Hand className="w-4 h-4 text-amber-500" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Apna sawaal puchein</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={doubtInput}
            onChange={(e) => setDoubtInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && doubtInput.trim()) {
                onSubmitDoubt(doubtInput.trim())
                setDoubtInput('')
              }
            }}
            placeholder="Yahan apna sawaal type karein..."
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
          <button
            onClick={() => {
              if (doubtInput.trim()) {
                onSubmitDoubt(doubtInput.trim())
                setDoubtInput('')
              }
            }}
            disabled={!doubtInput.trim()}
            className="p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
          <button
            onClick={onCancelDoubt}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  // Doubt answering mode
  if (state === 'doubt_answering') {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-primary-200 dark:border-primary-800 p-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
          <span className="text-sm text-primary-700 dark:text-primary-400 font-medium">
            Priya aapka jawab de rahi hai...
          </span>
        </div>
      </div>
    )
  }

  // Quiz mode
  if (state === 'quiz_asking' && quizQuestion) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Apna jawab select karein:</p>
        <div className="grid grid-cols-2 gap-2">
          {quizQuestion.options?.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => onAnswerQuiz(idx)}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm hover:border-primary-400 dark:hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all active:scale-95"
            >
              <span className="w-5 h-5 rounded-full border border-gray-300 dark:border-gray-500 flex items-center justify-center text-xs font-bold shrink-0">
                {String.fromCharCode(65 + idx)}
              </span>
              <span className="text-left text-xs leading-tight line-clamp-2">{opt}</span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  // Quiz feedback / intro
  if (state === 'quiz_feedback' || state === 'quiz_intro') {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {state === 'quiz_intro' ? 'Quiz shuru ho raha hai...' : 'Result aa raha hai...'}
          </span>
        </div>
      </div>
    )
  }

  // Completed
  if (state === 'completed') {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-green-200 dark:border-green-800 p-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-green-700 dark:text-green-400">
            Training complete! Well done!
          </span>
          <button
            onClick={onEndSession}
            className="px-4 py-1.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700"
          >
            Back to Products
          </button>
        </div>
      </div>
    )
  }

  // Default teaching/paused controls
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-3">
      <div className="flex items-center justify-between gap-2">
        {/* Left: Play/Pause */}
        <div className="flex items-center gap-2">
          <button
            onClick={isPaused || !isPlaying ? onResume : onPause}
            className="p-2.5 rounded-full bg-primary-600 text-white hover:bg-primary-700 transition-colors"
          >
            {isPaused || !isPlaying ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
        </div>

        {/* Center: Raise Hand */}
        <button
          onClick={onRaiseHand}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors text-sm font-medium"
        >
          <Hand className="w-4 h-4" />
          <span className="hidden sm:inline">Ask Doubt</span>
        </button>

        {/* Right: Speed */}
        <div className="relative">
          <button
            onClick={() => setShowSpeedMenu(!showSpeedMenu)}
            className="flex items-center gap-1 px-2.5 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm font-medium"
          >
            <Gauge className="w-3.5 h-3.5" />
            {playbackRate}x
          </button>

          {showSpeedMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowSpeedMenu(false)} />
              <div className="absolute bottom-full right-0 mb-1 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 min-w-[80px]">
                {speeds.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      onChangeSpeed(s)
                      setShowSpeedMenu(false)
                    }}
                    className={`w-full px-3 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 ${
                      s === playbackRate
                        ? 'text-primary-600 dark:text-primary-400 font-medium'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
