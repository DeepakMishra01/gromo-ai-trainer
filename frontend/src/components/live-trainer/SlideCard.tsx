import {
  Info,
  Star,
  ClipboardList,
  DollarSign,
  Trophy,
  HelpCircle,
  Lightbulb,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import type { NarrationSegment, QuizSegment } from '../../hooks/useLiveSession'

const sectionIcons: Record<string, React.ReactNode> = {
  intro: <Info className="w-5 h-5" />,
  benefits: <Star className="w-5 h-5" />,
  process: <ClipboardList className="w-5 h-5" />,
  terms: <DollarSign className="w-5 h-5" />,
  tips: <Trophy className="w-5 h-5" />,
  quiz: <HelpCircle className="w-5 h-5" />,
}

const sectionColors: Record<string, string> = {
  intro: 'from-blue-500 to-blue-600',
  benefits: 'from-green-500 to-emerald-600',
  process: 'from-violet-500 to-purple-600',
  terms: 'from-amber-500 to-orange-600',
  tips: 'from-pink-500 to-rose-600',
  quiz: 'from-cyan-500 to-teal-600',
}

interface SlideCardProps {
  segment: NarrationSegment | null
  quizQuestion?: QuizSegment | null
  quizMode?: boolean
  selectedAnswer?: number
  showFeedback?: boolean
  totalSegments?: number
  currentIndex?: number
}

export default function SlideCard({
  segment,
  quizQuestion,
  quizMode,
  selectedAnswer,
  showFeedback,
  totalSegments = 0,
  currentIndex = 0,
}: SlideCardProps) {
  if (quizMode && quizQuestion) {
    return <QuizSlide question={quizQuestion} selectedAnswer={selectedAnswer} showFeedback={showFeedback} />
  }

  if (!segment) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex items-center justify-center min-h-[200px]">
        <p className="text-gray-400 dark:text-gray-500 text-sm">Waiting for session to start...</p>
      </div>
    )
  }

  const sectionType = segment.section || 'intro'
  const icon = sectionIcons[sectionType] || <Info className="w-5 h-5" />
  const gradient = sectionColors[sectionType] || 'from-primary-500 to-primary-600'
  const content = segment.slide_content
  const items = content?.items || []

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden animate-fadeIn">
      {/* Header bar */}
      <div className={`bg-gradient-to-r ${gradient} px-4 py-2.5 flex items-center justify-between`}>
        <div className="flex items-center gap-2 text-white">
          {icon}
          <h3 className="text-sm md:text-base font-semibold">{segment.title}</h3>
        </div>
        <span className="text-white/70 text-xs font-medium">
          {currentIndex + 1} / {totalSegments}
        </span>
      </div>

      {/* Content */}
      <div className="p-4 md:p-5 space-y-3 min-h-[180px] max-h-[40vh] overflow-y-auto">
        {/* Description/Summary */}
        {(content?.description || content?.summary) && (
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {content.description || content.summary}
          </p>
        )}

        {/* Items list */}
        {items.length > 0 && (
          <ul className="space-y-2">
            {items.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-500 dark:bg-primary-400 mt-1.5 shrink-0" />
                <div>
                  {item.label && (
                    <span className="font-medium text-gray-900 dark:text-white">{item.label}: </span>
                  )}
                  <span className="text-gray-600 dark:text-gray-300">{item.value}</span>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Tip */}
        {content?.tip && (
          <div className="flex items-start gap-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 mt-2">
            <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-700 dark:text-amber-300">{content.tip}</p>
          </div>
        )}

        {/* Talking Points */}
        {segment.talking_points && segment.talking_points.length > 0 && (
          <div className="border-t border-gray-100 dark:border-gray-700 pt-3 mt-3">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider">Key Points</p>
            <div className="flex flex-wrap gap-1.5">
              {segment.talking_points.map((tp, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-md text-xs"
                >
                  {tp}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


function QuizSlide({
  question,
  selectedAnswer,
  showFeedback,
}: {
  question: QuizSegment
  selectedAnswer?: number
  showFeedback?: boolean
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden animate-fadeIn">
      <div className="bg-gradient-to-r from-cyan-500 to-teal-600 px-4 py-2.5 flex items-center gap-2 text-white">
        <HelpCircle className="w-5 h-5" />
        <h3 className="text-sm md:text-base font-semibold">
          Question {(question.question_index ?? 0) + 1}
        </h3>
      </div>

      <div className="p-4 md:p-5">
        <p className="text-sm md:text-base font-medium text-gray-900 dark:text-white mb-4">
          {question.question}
        </p>

        <div className="space-y-2">
          {question.options?.map((opt, idx) => {
            const isSelected = selectedAnswer === idx
            const isCorrect = idx === question.correct_answer
            let optionClass = 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200'

            if (showFeedback && isSelected && isCorrect) {
              optionClass = 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300'
            } else if (showFeedback && isSelected && !isCorrect) {
              optionClass = 'border-red-500 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            } else if (showFeedback && isCorrect) {
              optionClass = 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300'
            }

            return (
              <div
                key={idx}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border ${optionClass} text-sm`}
              >
                <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-xs font-bold shrink-0">
                  {String.fromCharCode(65 + idx)}
                </span>
                <span className="flex-1">{opt}</span>
                {showFeedback && isCorrect && <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />}
                {showFeedback && isSelected && !isCorrect && <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
              </div>
            )
          })}
        </div>

        {showFeedback && question.explanation && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 italic">
            {question.explanation}
          </p>
        )}
      </div>
    </div>
  )
}
