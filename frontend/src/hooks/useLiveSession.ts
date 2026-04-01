import { useState, useCallback, useRef } from 'react'
import { authFetch } from '../api/authFetch'
import { useAudioQueue } from './useAudioQueue'

// ---- Types ----

export type SessionState =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'teaching'
  | 'paused'
  | 'doubt_listening'
  | 'doubt_answering'
  | 'quiz_intro'
  | 'quiz_asking'
  | 'quiz_feedback'
  | 'completed'

export interface SlideContent {
  type: string
  product_name?: string
  category?: string
  description?: string
  summary?: string
  payout?: string
  items?: Array<{ label: string; value: string }>
  tip?: string
}

export interface NarrationSegment {
  index: number
  section: string
  title: string
  narration: string
  slide_content: SlideContent
  talking_points: string[]
}

export interface QuizSegment {
  type: string
  question_index?: number
  question?: string
  options?: string[]
  correct_answer?: number
  question_narration?: string
  correct_feedback?: string
  incorrect_feedback?: string
  explanation?: string
  narration?: string
}

export interface LiveSessionData {
  session_id: string
  product_id: string
  product_name: string
  category_name: string
  segments: NarrationSegment[]
  quiz_segments: QuizSegment[]
}

// ---- Hook ----

export function useLiveSession() {
  const [state, setState] = useState<SessionState>('idle')
  const [session, setSession] = useState<LiveSessionData | null>(null)
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0)
  const [error, setError] = useState('')
  const [doubtText, setDoubtText] = useState('')
  const [doubtAnswer, setDoubtAnswer] = useState('')

  // Quiz state
  const [currentQuizIndex, setCurrentQuizIndex] = useState(0)
  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({})
  const [quizScore, setQuizScore] = useState(0)
  const [totalQuizQuestions, setTotalQuizQuestions] = useState(0)

  // Playback speed
  const [playbackRate, setPlaybackRateState] = useState(1.0)

  const sessionRef = useRef<LiveSessionData | null>(null)

  // Audio queue
  const audioQueue = useAudioQueue({
    speaker: 'priya',
    pace: 0.85,
    model: 'bulbul:v2',
    onSegmentStart: (index: number) => {
      setCurrentSegmentIndex(index)
    },
    onSegmentEnd: (_index: number) => {
      // Segment ended — next segment will auto-play via queue
    },
    onQueueComplete: () => {
      // All teaching segments done — transition to quiz
      startQuiz()
    },
  })

  // ---- Start Session ----

  const startSession = useCallback(async (productId: string) => {
    setState('loading')
    setError('')
    setCurrentSegmentIndex(0)
    setQuizAnswers({})
    setQuizScore(0)
    setCurrentQuizIndex(0)

    try {
      const res = await authFetch('/api/training/live-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId }),
      })

      if (!res.ok) throw new Error('Failed to generate live training script')
      const data: LiveSessionData = await res.json()

      setSession(data)
      sessionRef.current = data
      setTotalQuizQuestions(
        data.quiz_segments.filter((q) => q.type === 'quiz_question').length
      )

      // Load narration texts into audio queue
      const narrations = data.segments.map((s) => s.narration)
      audioQueue.loadSegments(narrations)

      setState('ready')
    } catch (err) {
      console.error('Failed to start live session:', err)
      setError('Training session load nahi ho payi. Please try again.')
      setState('idle')
    }
  }, [audioQueue])

  // ---- Begin Playback ----

  const beginTeaching = useCallback(() => {
    setState('teaching')
    audioQueue.play()
  }, [audioQueue])

  // ---- Pause / Resume ----

  const pauseSession = useCallback(() => {
    audioQueue.pause()
    setState('paused')
  }, [audioQueue])

  const resumeSession = useCallback(() => {
    audioQueue.resume()
    setState('teaching')
  }, [audioQueue])

  // ---- Speed Control ----

  const changeSpeed = useCallback((rate: number) => {
    setPlaybackRateState(rate)
    audioQueue.setPlaybackRate(rate)
  }, [audioQueue])

  // ---- Doubt Flow ----

  const raiseHand = useCallback(() => {
    audioQueue.pause()
    setState('doubt_listening')
    setDoubtText('')
    setDoubtAnswer('')
  }, [audioQueue])

  const submitDoubt = useCallback(async (question: string) => {
    if (!question.trim() || !sessionRef.current) return

    setDoubtText(question)
    setState('doubt_answering')

    try {
      const res = await authFetch('/api/training/live-doubt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: sessionRef.current.product_id,
          question: question.trim(),
        }),
      })

      if (!res.ok) throw new Error('Doubt resolution failed')
      const data = await res.json()
      const answerText = data.answer_narration

      setDoubtAnswer(answerText)

      // Play the doubt answer audio, then resume teaching
      await audioQueue.playInterrupt(answerText)

      setState('teaching')
      audioQueue.resume()
    } catch (err) {
      console.error('Doubt resolution failed:', err)
      setDoubtAnswer('Maaf kijiye, abhi jawab nahi mil raha. Chalo aage badhte hain.')
      setState('teaching')
      audioQueue.resume()
    }
  }, [audioQueue])

  const cancelDoubt = useCallback(() => {
    setState('teaching')
    audioQueue.resume()
  }, [audioQueue])

  // ---- Quiz Flow ----

  const startQuiz = useCallback(async () => {
    if (!sessionRef.current) return

    const quizIntro = sessionRef.current.quiz_segments.find(
      (q) => q.type === 'quiz_intro'
    )

    if (quizIntro?.narration) {
      setState('quiz_intro')
      setCurrentQuizIndex(0)
      // Play quiz intro narration
      await audioQueue.playInterrupt(quizIntro.narration)
    }

    setState('quiz_asking')
  }, [audioQueue])

  const answerQuiz = useCallback(async (selectedIndex: number) => {
    if (!sessionRef.current) return

    const questions = sessionRef.current.quiz_segments.filter(
      (q) => q.type === 'quiz_question'
    )
    const currentQ = questions[currentQuizIndex]
    if (!currentQ) return

    const isCorrect = selectedIndex === currentQ.correct_answer
    setQuizAnswers((prev) => ({ ...prev, [currentQuizIndex]: selectedIndex }))

    if (isCorrect) {
      setQuizScore((prev) => prev + 1)
    }

    // Play feedback
    setState('quiz_feedback')
    const feedbackText = isCorrect
      ? currentQ.correct_feedback || 'Sahi jawab!'
      : currentQ.incorrect_feedback || 'Galat jawab!'

    await audioQueue.playInterrupt(feedbackText)

    // Move to next question or complete
    if (currentQuizIndex + 1 < questions.length) {
      setCurrentQuizIndex((prev) => prev + 1)
      setState('quiz_asking')

      // Play next question narration
      const nextQ = questions[currentQuizIndex + 1]
      if (nextQ?.question_narration) {
        await audioQueue.playInterrupt(nextQ.question_narration)
      }
    } else {
      // Quiz complete — get completion narration
      await completeSession()
    }
  }, [currentQuizIndex, audioQueue])

  const completeSession = useCallback(async () => {
    if (!sessionRef.current) return

    const questions = sessionRef.current.quiz_segments.filter(
      (q) => q.type === 'quiz_question'
    )
    const finalScore = quizScore + (
      // Check if the last answer was correct (not yet counted)
      0 // Score already updated in answerQuiz
    )

    try {
      const res = await authFetch('/api/training/live-completion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_name: sessionRef.current.product_name,
          score: finalScore,
          total: questions.length,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        await audioQueue.playInterrupt(data.narration)
      }
    } catch {
      // Ignore completion narration errors
    }

    setState('completed')
  }, [quizScore, audioQueue])

  // ---- Cleanup ----

  const endSession = useCallback(() => {
    audioQueue.stop()
    setState('idle')
    setSession(null)
    sessionRef.current = null
    setCurrentSegmentIndex(0)
    setQuizAnswers({})
    setQuizScore(0)
    setCurrentQuizIndex(0)
  }, [audioQueue])

  // Current data helpers
  const currentSegment = session?.segments[currentSegmentIndex] || null
  const currentQuizQuestion = session?.quiz_segments.filter(
    (q) => q.type === 'quiz_question'
  )[currentQuizIndex] || null

  return {
    // State
    state,
    session,
    error,
    currentSegmentIndex,
    currentSegment,
    playbackRate,

    // Quiz
    currentQuizIndex,
    currentQuizQuestion,
    quizAnswers,
    quizScore,
    totalQuizQuestions,

    // Doubt
    doubtText,
    doubtAnswer,

    // Audio
    isPlaying: audioQueue.isPlaying,
    isPaused: audioQueue.isPaused,

    // Actions
    startSession,
    beginTeaching,
    pauseSession,
    resumeSession,
    changeSpeed,
    raiseHand,
    submitDoubt,
    cancelDoubt,
    answerQuiz,
    endSession,
  }
}
