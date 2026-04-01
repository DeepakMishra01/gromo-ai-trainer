import { GraduationCap } from 'lucide-react'
import AudioWaveform from './AudioWaveform'
import type { SessionState } from '../../hooks/useLiveSession'

interface TrainerAvatarProps {
  isSpeaking: boolean
  state: SessionState
  trainerName?: string
}

const stateLabels: Partial<Record<SessionState, string>> = {
  loading: 'Session prepare ho rahi hai...',
  ready: 'Class shuru karne ke liye ready!',
  teaching: 'Priya padha rahi hai...',
  paused: 'Session paused',
  doubt_listening: 'Aapka sawaal sun rahi hoon...',
  doubt_answering: 'Jawab soch rahi hoon...',
  quiz_intro: 'Quiz shuru ho raha hai!',
  quiz_asking: 'Sawaal sun lijiye...',
  quiz_feedback: 'Result de rahi hoon...',
  completed: 'Training complete!',
}

export default function TrainerAvatar({ isSpeaking, state, trainerName = 'Priya' }: TrainerAvatarProps) {
  const statusText = stateLabels[state] || ''

  return (
    <div className="flex items-center gap-3 md:gap-4">
      {/* Avatar circle */}
      <div className="relative">
        <div
          className={`w-12 h-12 md:w-14 md:h-14 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shadow-lg transition-transform duration-300 ${
            isSpeaking ? 'scale-110' : 'scale-100'
          }`}
        >
          <GraduationCap className="w-6 h-6 md:w-7 md:h-7 text-white" />
        </div>
        {/* Speaking indicator ring */}
        {isSpeaking && (
          <div className="absolute inset-0 rounded-full border-2 border-primary-400 animate-ping opacity-30" />
        )}
        {/* Online dot */}
        <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-gray-800 ${
          state === 'completed' ? 'bg-gray-400' : 'bg-green-500'
        }`} />
      </div>

      {/* Name and status */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm md:text-base font-semibold text-gray-900 dark:text-white">
            {trainerName}
          </h3>
          <span className="text-xs px-1.5 py-0.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-full font-medium">
            AI Trainer
          </span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <AudioWaveform active={isSpeaking} barCount={4} />
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {statusText}
          </p>
        </div>
      </div>
    </div>
  )
}
