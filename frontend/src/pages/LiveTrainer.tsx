import { useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Play,
  Trophy,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { useLiveSession } from '../hooks/useLiveSession'
import TrainerAvatar from '../components/live-trainer/TrainerAvatar'
import SlideCard from '../components/live-trainer/SlideCard'
import InteractionBar from '../components/live-trainer/InteractionBar'

export default function LiveTrainer() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const productId = searchParams.get('product')

  const live = useLiveSession()

  // Start session on mount
  useEffect(() => {
    if (productId && live.state === 'idle') {
      live.startSession(productId)
    }
  }, [productId])

  // No product ID
  if (!productId) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-gray-700 dark:text-gray-300 font-medium mb-2">No product selected</p>
          <button
            onClick={() => navigate('/training')}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
          >
            Go to Training
          </button>
        </div>
      </div>
    )
  }

  // Loading
  if (live.state === 'loading') {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            AI Trainer prepare ho rahi hai...
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Training script generate ho raha hai
          </p>
        </div>
      </div>
    )
  }

  // Error
  if (live.error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-gray-700 dark:text-gray-300 font-medium mb-2">{live.error}</p>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => navigate('/training')}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Back
            </button>
            <button
              onClick={() => live.startSession(productId)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Ready — waiting for user to start
  if (live.state === 'ready' && live.session) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="w-20 h-20 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full flex items-center justify-center mx-auto mb-5 shadow-lg">
            <Play className="w-8 h-8 text-white ml-1" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Live Class Ready!
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
            <span className="font-medium text-gray-700 dark:text-gray-300">{live.session.product_name}</span>
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-6">
            {live.session.category_name} &middot; {live.session.segments.length} sections &middot; Quiz
          </p>
          <button
            onClick={live.beginTeaching}
            className="px-8 py-3 bg-primary-600 text-white rounded-xl text-base font-semibold hover:bg-primary-700 shadow-lg hover:shadow-xl transition-all active:scale-95"
          >
            Start Live Class
          </button>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
            Priya aapko is product ke baare mein sikhayegi
          </p>
        </div>
      </div>
    )
  }

  // Completed
  if (live.state === 'completed' && live.session) {
    const percentage = live.totalQuizQuestions > 0
      ? Math.round((live.quizScore / live.totalQuizQuestions) * 100)
      : 0

    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center max-w-md mx-auto px-4">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-5 shadow-lg ${
            percentage >= 80
              ? 'bg-gradient-to-br from-green-400 to-green-600'
              : percentage >= 60
              ? 'bg-gradient-to-br from-amber-400 to-amber-600'
              : 'bg-gradient-to-br from-red-400 to-red-600'
          }`}>
            <Trophy className="w-8 h-8 text-white" />
          </div>

          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Training Complete!
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {live.session.product_name}
          </p>

          {/* Score Card */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 mb-5">
            <div className="text-4xl font-bold text-gray-900 dark:text-white mb-1">
              {live.quizScore}/{live.totalQuizQuestions}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Quiz Score</p>

            {/* Answer breakdown */}
            <div className="flex justify-center gap-1.5 mt-3">
              {Object.entries(live.quizAnswers).map(([qIdx, ansIdx]) => {
                const questions = live.session!.quiz_segments.filter(q => q.type === 'quiz_question')
                const q = questions[Number(qIdx)]
                const isCorrect = q && ansIdx === q.correct_answer
                return (
                  <div key={qIdx} className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    isCorrect
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  }`}>
                    {isCorrect ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  </div>
                )
              })}
            </div>

            <p className={`text-sm font-medium mt-3 ${
              percentage >= 80
                ? 'text-green-600 dark:text-green-400'
                : percentage >= 60
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-red-600 dark:text-red-400'
            }`}>
              {percentage >= 80 ? 'Excellent! You are ready to sell!' :
               percentage >= 60 ? 'Good effort! Practice more!' :
               'Keep learning, you will improve!'}
            </p>
          </div>

          <div className="flex gap-2 justify-center">
            <button
              onClick={() => navigate('/training')}
              className="px-5 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Back to Products
            </button>
            <button
              onClick={() => {
                live.endSession()
                live.startSession(productId)
              }}
              className="px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
            >
              Retake Class
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Active session (teaching, quiz, doubt)
  if (!live.session) return null

  const isQuizMode = ['quiz_intro', 'quiz_asking', 'quiz_feedback'].includes(live.state)

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] md:h-[calc(100vh-8rem)]">
      {/* Top: Header + Avatar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-3 md:p-4 mb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              live.endSession()
              navigate('/training')
            }}
            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1 min-w-0">
            <TrainerAvatar
              isSpeaking={live.isPlaying}
              state={live.state}
            />
          </div>
        </div>

        {/* Progress bar */}
        {!isQuizMode && live.session.segments.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 mb-1">
              <span>Section {live.currentSegmentIndex + 1} of {live.session.segments.length}</span>
              <span>{Math.round(((live.currentSegmentIndex + 1) / live.session.segments.length) * 100)}%</span>
            </div>
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all duration-500"
                style={{
                  width: `${((live.currentSegmentIndex + 1) / live.session.segments.length) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Quiz progress */}
        {isQuizMode && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 mb-1">
              <span>Quiz: Question {live.currentQuizIndex + 1} of {live.totalQuizQuestions}</span>
              <span>Score: {live.quizScore}/{live.currentQuizIndex}</span>
            </div>
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                style={{
                  width: `${((live.currentQuizIndex + 1) / Math.max(live.totalQuizQuestions, 1)) * 100}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Middle: Slide Content */}
      <div className="flex-1 overflow-y-auto mb-3">
        {/* Doubt Q&A display */}
        {(live.state === 'doubt_listening' || live.state === 'doubt_answering') && (
          <div className="mb-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800 p-4">
            {live.doubtText && (
              <div className="mb-2">
                <p className="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1">Your Question:</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{live.doubtText}</p>
              </div>
            )}
            {live.doubtAnswer && (
              <div>
                <p className="text-xs font-medium text-primary-600 dark:text-primary-400 mb-1">Priya's Answer:</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{live.doubtAnswer}</p>
              </div>
            )}
          </div>
        )}

        <SlideCard
          segment={live.currentSegment}
          quizQuestion={isQuizMode ? live.currentQuizQuestion : null}
          quizMode={isQuizMode}
          selectedAnswer={live.quizAnswers[live.currentQuizIndex]}
          showFeedback={live.state === 'quiz_feedback'}
          totalSegments={live.session.segments.length}
          currentIndex={live.currentSegmentIndex}
        />
      </div>

      {/* Bottom: Interaction Bar */}
      <div className="shrink-0">
        <InteractionBar
          state={live.state}
          isPlaying={live.isPlaying}
          isPaused={live.isPaused}
          playbackRate={live.playbackRate}
          onPause={live.pauseSession}
          onResume={live.resumeSession}
          onRaiseHand={live.raiseHand}
          onSubmitDoubt={live.submitDoubt}
          onCancelDoubt={live.cancelDoubt}
          onChangeSpeed={live.changeSpeed}
          onAnswerQuiz={live.answerQuiz}
          quizQuestion={live.currentQuizQuestion}
          onEndSession={() => {
            live.endSession()
            navigate('/training')
          }}
        />
      </div>
    </div>
  )
}
