import { useState, useEffect, useRef } from 'react'
import { authFetch } from '../api/authFetch'
import {
  GraduationCap,
  Send,
  BookOpen,
  Star,
  ClipboardList,
  DollarSign,
  Trophy,
  HelpCircle,
  Brain,
  ChevronRight,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Loader2,
  Info,
  Lightbulb,
  Search,
  Package,
  AlertCircle,
} from 'lucide-react'

// ---- Types ----

interface TrainingProduct {
  id: string
  name: string
  category_name: string
  sub_type: string | null
  payout: string | null
  description: string | null
  has_benefits: boolean
  has_process: boolean
  has_terms: boolean
}

interface SectionItem {
  label: string
  value: string
}

interface FaqItem {
  question: string
  answer: string
}

interface SectionContent {
  type: string
  product_name?: string
  category?: string
  description?: string
  summary?: string
  items?: SectionItem[] | FaqItem[]
  tip?: string
}

interface TrainingSection {
  index: number
  title: string
  icon: string
  content: SectionContent
  talking_points: string[]
}

interface QuizQuestion {
  question: string
  options: string[]
  correct_answer: number
  explanation: string
}

interface TrainingSession {
  session_id: string
  product_id: string
  product_name: string
  category_name: string
  total_sections: number
  sections: TrainingSection[]
  quiz: QuizQuestion[]
}

interface Doubt {
  question: string
  answer: string
}

// ---- Icon Map ----

const sectionIcons: Record<string, React.ReactNode> = {
  info: <Info className="w-4 h-4" />,
  star: <Star className="w-4 h-4" />,
  clipboard: <ClipboardList className="w-4 h-4" />,
  currency: <DollarSign className="w-4 h-4" />,
  trophy: <Trophy className="w-4 h-4" />,
  help: <HelpCircle className="w-4 h-4" />,
  quiz: <Brain className="w-4 h-4" />,
}

// ---- Main Component ----

export default function TrainingPlayer() {
  const [products, setProducts] = useState<TrainingProduct[]>([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<TrainingProduct | null>(null)
  const [session, setSession] = useState<TrainingSession | null>(null)
  const [loadingSession, setLoadingSession] = useState(false)
  const [sessionError, setSessionError] = useState('')
  const [currentSection, setCurrentSection] = useState(0)
  const [completedSections, setCompletedSections] = useState<Set<number>>(new Set())

  // Doubt state
  const [doubts, setDoubts] = useState<Doubt[]>([])
  const [doubtInput, setDoubtInput] = useState('')
  const [askingDoubt, setAskingDoubt] = useState(false)
  const doubtEndRef = useRef<HTMLDivElement>(null)

  // Quiz state
  const [quizStarted, setQuizStarted] = useState(false)
  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({})
  const [quizChecked, setQuizChecked] = useState<Record<number, boolean>>({})
  const [quizScore, setQuizScore] = useState<number | null>(null)
  const [currentQuizIndex, setCurrentQuizIndex] = useState(0)

  // Fetch products on mount
  useEffect(() => {
    fetchProducts()
  }, [])

  // Scroll doubts to bottom
  useEffect(() => {
    doubtEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [doubts])

  const fetchProducts = () => {
    setLoadingProducts(true)
    authFetch('/api/training/products')
      .then((r) => r.json())
      .then((data) => {
        setProducts(data)
        setLoadingProducts(false)
      })
      .catch(() => setLoadingProducts(false))
  }

  const startSession = async (product: TrainingProduct) => {
    setSelectedProduct(product)
    setLoadingSession(true)
    setCurrentSection(0)
    setCompletedSections(new Set())
    setDoubts([])
    setQuizStarted(false)
    setQuizAnswers({})
    setQuizChecked({})
    setQuizScore(null)
    setCurrentQuizIndex(0)
    setSessionError('')
    try {
      const res = await authFetch('/api/training/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: product.id }),
      })
      if (!res.ok) throw new Error('Failed to load training session')
      const data = await res.json()
      setSession(data)
    } catch {
      setSessionError('Failed to load training session. Please try again.')
    } finally {
      setLoadingSession(false)
    }
  }

  const askDoubt = async () => {
    if (!doubtInput.trim() || !selectedProduct) return
    const question = doubtInput.trim()
    setDoubtInput('')
    setDoubts((prev) => [...prev, { question, answer: '' }])
    setAskingDoubt(true)
    try {
      const res = await authFetch('/api/training/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: selectedProduct.id, question }),
      })
      const data = await res.json()
      setDoubts((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { question, answer: data.answer }
        return updated
      })
    } catch {
      setDoubts((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          question,
          answer: 'Sorry, unable to get answer right now. Please try again.',
        }
        return updated
      })
    } finally {
      setAskingDoubt(false)
    }
  }

  const navigateSection = (index: number) => {
    // Mark current as completed
    setCompletedSections((prev) => {
      const next = new Set(prev)
      next.add(currentSection)
      return next
    })
    setCurrentSection(index)

    // If it's the quiz section, set quiz started
    if (session && index === session.sections.length - 1) {
      setQuizStarted(true)
    }
  }

  const handleQuizAnswer = (questionIndex: number, optionIndex: number) => {
    if (quizChecked[questionIndex] !== undefined) return
    setQuizAnswers((prev) => ({ ...prev, [questionIndex]: optionIndex }))
  }

  const checkQuizAnswer = (questionIndex: number) => {
    if (!session) return
    const correct = session.quiz[questionIndex].correct_answer
    const selected = quizAnswers[questionIndex]
    if (selected === undefined) return
    setQuizChecked((prev) => ({ ...prev, [questionIndex]: selected === correct }))
  }

  const calculateScore = () => {
    if (!session) return
    let correct = 0
    session.quiz.forEach((q, i) => {
      if (quizAnswers[i] === q.correct_answer) correct++
    })
    setQuizScore(correct)
    // Mark quiz section as completed
    setCompletedSections((prev) => {
      const next = new Set(prev)
      next.add(session.sections.length - 1)
      return next
    })
  }

  const goBack = () => {
    setSelectedProduct(null)
    setSession(null)
    setCurrentSection(0)
    setCompletedSections(new Set())
    setDoubts([])
    setQuizStarted(false)
    setQuizAnswers({})
    setQuizChecked({})
    setQuizScore(null)
    setCurrentQuizIndex(0)
  }

  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.category_name.toLowerCase().includes(search.toLowerCase())
  )

  // ---- Product Selection View ----
  if (!selectedProduct) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <GraduationCap className="w-12 h-12 mx-auto mb-4 text-primary-600" />
          <h2 className="text-xl font-bold text-gray-900">AI Training Sessions</h2>
          <p className="text-gray-500 mt-2">
            Select a product to start an interactive training session with AI-powered doubt resolution
          </p>
        </div>

        {/* Search */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <span className="text-sm text-gray-500">{filteredProducts.length} products available</span>
        </div>

        {/* Product Cards */}
        {loadingProducts ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Package className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No products found. Sync products first from the Products page.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProducts.map((product) => (
              <button
                key={product.id}
                onClick={() => startSession(product)}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-left hover:border-primary-300 hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
                      {product.name}
                    </h3>
                    <span className="inline-block mt-1 px-2.5 py-0.5 bg-primary-50 text-primary-700 rounded-full text-xs font-medium">
                      {product.category_name}
                    </span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-primary-500 transition-colors mt-1" />
                </div>
                {product.payout && (
                  <p className="text-sm text-green-600 font-medium mt-2">Payout: {product.payout}</p>
                )}
                {product.description && (
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">{product.description}</p>
                )}
                <div className="flex gap-2 mt-3">
                  {product.has_benefits && (
                    <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">Benefits</span>
                  )}
                  {product.has_process && (
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">Process</span>
                  )}
                  {product.has_terms && (
                    <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded text-xs">Terms</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ---- Loading Session ----
  if (sessionError) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-gray-700 font-medium mb-2">Could not load training session</p>
          <p className="text-gray-500 text-sm mb-4">{sessionError}</p>
          <button onClick={goBack} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700">
            Back to Products
          </button>
        </div>
      </div>
    )
  }

  if (loadingSession || !session) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-gray-500">Preparing training session for {selectedProduct.name}...</p>
        </div>
      </div>
    )
  }

  const currentSectionData = session.sections[currentSection]
  const isQuizSection = currentSectionData?.content.type === 'quiz'

  // ---- Training Session View ----
  return (
    <div className="flex gap-4 h-[calc(100vh-10rem)]">
      {/* Left Panel: Section Navigator */}
      <div className="w-64 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={goBack}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Products
          </button>
          <h3 className="font-semibold text-gray-900 text-sm">{session.product_name}</h3>
          <span className="text-xs text-primary-600">{session.category_name}</span>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {session.sections.map((section, idx) => {
            const isActive = currentSection === idx
            const isCompleted = completedSections.has(idx)
            return (
              <button
                key={idx}
                onClick={() => navigateSection(idx)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm transition-all mb-1 ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 font-medium'
                    : isCompleted
                    ? 'text-green-700 bg-green-50/50'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <span
                  className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs ${
                    isActive
                      ? 'bg-primary-600 text-white'
                      : isCompleted
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    sectionIcons[section.icon] || <span>{idx + 1}</span>
                  )}
                </span>
                <span className="truncate">{section.title}</span>
              </button>
            )
          })}
        </nav>
        {/* Progress */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>Progress</span>
            <span>
              {completedSections.size}/{session.sections.length}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(completedSections.size / session.sections.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Content Panel */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 overflow-y-auto mb-4">
          <div className="p-6">
            {/* Section Header */}
            <div className="flex items-center gap-3 mb-6">
              <span className="w-10 h-10 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center">
                {sectionIcons[currentSectionData.icon] || <BookOpen className="w-5 h-5" />}
              </span>
              <div>
                <h2 className="text-lg font-bold text-gray-900">{currentSectionData.title}</h2>
                <p className="text-xs text-gray-500">
                  Section {currentSection + 1} of {session.sections.length}
                </p>
              </div>
            </div>

            {/* Section Content */}
            {isQuizSection ? (
              <QuizView
                quiz={session.quiz}
                quizStarted={quizStarted}
                quizAnswers={quizAnswers}
                quizChecked={quizChecked}
                quizScore={quizScore}
                currentQuizIndex={currentQuizIndex}
                setCurrentQuizIndex={setCurrentQuizIndex}
                onStartQuiz={() => setQuizStarted(true)}
                onAnswer={handleQuizAnswer}
                onCheck={checkQuizAnswer}
                onCalculateScore={calculateScore}
                description={currentSectionData.content.description || ''}
              />
            ) : (
              <SectionContentView content={currentSectionData.content} />
            )}

            {/* Talking Points */}
            {!isQuizSection && currentSectionData.talking_points.length > 0 && (
              <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
                <h4 className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
                  <Lightbulb className="w-4 h-4" />
                  Selling Tips
                </h4>
                <ul className="space-y-1">
                  {currentSectionData.talking_points.map((point, i) => (
                    <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                      <ChevronRight className="w-3 h-3 mt-1 shrink-0" />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between mt-8 pt-4 border-t border-gray-100">
              <button
                onClick={() => currentSection > 0 && navigateSection(currentSection - 1)}
                disabled={currentSection === 0}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              {currentSection < session.sections.length - 1 && (
                <button
                  onClick={() => navigateSection(currentSection + 1)}
                  className="px-6 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
                >
                  Next Section
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Doubt Chat Bar */}
        {!isQuizSection && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            {doubts.length > 0 && (
              <div className="max-h-48 overflow-y-auto mb-3 space-y-3">
                {doubts.map((d, i) => (
                  <div key={i} className="space-y-2">
                    <div className="flex justify-end">
                      <div className="max-w-[80%] bg-primary-600 text-white rounded-2xl px-4 py-2 text-sm">
                        {d.question}
                      </div>
                    </div>
                    {d.answer && (
                      <div className="flex justify-start">
                        <div className="max-w-[80%] bg-gray-100 text-gray-900 rounded-2xl px-4 py-2 text-sm whitespace-pre-line">
                          {d.answer}
                        </div>
                      </div>
                    )}
                    {!d.answer && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl px-4 py-2">
                          <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={doubtEndRef} />
              </div>
            )}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={doubtInput}
                onChange={(e) => setDoubtInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && askDoubt()}
                placeholder="Ask a doubt about this product..."
                disabled={askingDoubt}
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50"
              />
              <button
                onClick={askDoubt}
                disabled={askingDoubt || !doubtInput.trim()}
                className="p-2.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ---- Sub-Components ----

function SectionContentView({ content }: { content: SectionContent }) {
  if (content.type === 'intro') {
    return (
      <div className="space-y-4">
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
          <h3 className="font-semibold text-primary-900">{content.product_name}</h3>
          <span className="text-xs text-primary-600">{content.category}</span>
        </div>
        {content.description && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Description</h4>
            <p className="text-sm text-gray-600">{content.description}</p>
          </div>
        )}
        {content.summary && (
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-700 italic">{content.summary}</p>
          </div>
        )}
      </div>
    )
  }

  if (content.type === 'faqs') {
    const faqs = (content.items as FaqItem[]) || []
    return (
      <div className="space-y-4">
        {faqs.length === 0 && <p className="text-sm text-gray-500">No FAQs available for this product.</p>}
        {faqs.map((faq, i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-900">Q: {faq.question}</p>
            {faq.answer && <p className="text-sm text-gray-600 mt-2">A: {faq.answer}</p>}
          </div>
        ))}
        {content.tip && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs text-blue-700">
              <span className="font-semibold">Pro Tip:</span> {content.tip}
            </p>
          </div>
        )}
      </div>
    )
  }

  // features, eligibility, fees, benefits
  const items = (content.items as SectionItem[]) || []
  return (
    <div className="space-y-4">
      {items.length === 0 && <p className="text-sm text-gray-500">No information available for this section.</p>}
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            {item.label ? (
              <>
                <span className="text-sm font-medium text-gray-700 min-w-[120px] shrink-0">
                  {item.label}
                </span>
                <span className="text-sm text-gray-600">{item.value}</span>
              </>
            ) : (
              <div className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 mt-1 text-primary-500 shrink-0" />
                <span className="text-sm text-gray-600">{item.value}</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {content.tip && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-xs text-blue-700">
            <span className="font-semibold">Pro Tip:</span> {content.tip}
          </p>
        </div>
      )}
    </div>
  )
}

function QuizView({
  quiz,
  quizStarted,
  quizAnswers,
  quizChecked,
  quizScore,
  currentQuizIndex,
  setCurrentQuizIndex,
  onStartQuiz,
  onAnswer,
  onCheck,
  onCalculateScore,
  description,
}: {
  quiz: QuizQuestion[]
  quizStarted: boolean
  quizAnswers: Record<number, number>
  quizChecked: Record<number, boolean>
  quizScore: number | null
  currentQuizIndex: number
  setCurrentQuizIndex: (i: number) => void
  onStartQuiz: () => void
  onAnswer: (qi: number, oi: number) => void
  onCheck: (qi: number) => void
  onCalculateScore: () => void
  description: string
}) {
  // Score screen
  if (quizScore !== null) {
    const percentage = Math.round((quizScore / quiz.length) * 100)
    return (
      <div className="text-center py-8 space-y-6">
        <div
          className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto text-3xl font-bold ${
            percentage >= 80
              ? 'bg-green-100 text-green-700'
              : percentage >= 50
              ? 'bg-amber-100 text-amber-700'
              : 'bg-red-100 text-red-700'
          }`}
        >
          {percentage}%
        </div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">
            {percentage >= 80
              ? 'Excellent! You are ready to sell!'
              : percentage >= 50
              ? 'Good effort! Review and try again.'
              : 'Keep learning! Review the training sections.'}
          </h3>
          <p className="text-gray-500 mt-2">
            You scored {quizScore} out of {quiz.length} questions correctly.
          </p>
        </div>
        {/* Answer Review */}
        <div className="text-left space-y-3 max-w-lg mx-auto">
          {quiz.map((q, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg border ${
                quizAnswers[i] === q.correct_answer
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <p className="text-sm font-medium text-gray-900">
                Q{i + 1}: {q.question}
              </p>
              <p className="text-xs text-gray-600 mt-1">{q.explanation}</p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Start screen
  if (!quizStarted) {
    return (
      <div className="text-center py-8">
        <Brain className="w-16 h-16 mx-auto mb-4 text-primary-600" />
        <h3 className="text-lg font-bold text-gray-900 mb-2">Quick Knowledge Check</h3>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">{description}</p>
        <button
          onClick={onStartQuiz}
          className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors"
        >
          Start Quiz
        </button>
      </div>
    )
  }

  // Quiz questions
  const q = quiz[currentQuizIndex]
  if (!q) return null
  const isChecked = quizChecked[currentQuizIndex] !== undefined
  const isCorrect = quizChecked[currentQuizIndex]
  const allAnswered = Object.keys(quizAnswers).length === quiz.length
  const allChecked = Object.keys(quizChecked).length === quiz.length

  return (
    <div className="space-y-6">
      {/* Question Progress */}
      <div className="flex items-center gap-2">
        {quiz.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentQuizIndex(i)}
            className={`w-8 h-8 rounded-full text-xs font-medium transition-all ${
              i === currentQuizIndex
                ? 'bg-primary-600 text-white'
                : quizChecked[i] !== undefined
                ? quizChecked[i]
                  ? 'bg-green-500 text-white'
                  : 'bg-red-500 text-white'
                : quizAnswers[i] !== undefined
                ? 'bg-primary-100 text-primary-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* Question */}
      <div>
        <p className="text-sm text-gray-500 mb-1">
          Question {currentQuizIndex + 1} of {quiz.length}
        </p>
        <h3 className="text-base font-semibold text-gray-900">{q.question}</h3>
      </div>

      {/* Options */}
      <div className="space-y-2">
        {q.options.map((option, oi) => {
          const isSelected = quizAnswers[currentQuizIndex] === oi
          const isCorrectOption = isChecked && oi === q.correct_answer
          const isWrongSelected = isChecked && isSelected && !isCorrect

          return (
            <button
              key={oi}
              onClick={() => onAnswer(currentQuizIndex, oi)}
              disabled={isChecked}
              className={`w-full text-left p-4 rounded-lg border-2 text-sm transition-all ${
                isCorrectOption
                  ? 'border-green-500 bg-green-50'
                  : isWrongSelected
                  ? 'border-red-500 bg-red-50'
                  : isSelected
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              } ${isChecked ? 'cursor-default' : 'cursor-pointer'}`}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                    isCorrectOption
                      ? 'bg-green-500 text-white'
                      : isWrongSelected
                      ? 'bg-red-500 text-white'
                      : isSelected
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {isCorrectOption ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : isWrongSelected ? (
                    <XCircle className="w-4 h-4" />
                  ) : (
                    String.fromCharCode(65 + oi)
                  )}
                </span>
                <span className="text-gray-900">{option}</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Check / Explanation */}
      {isChecked && (
        <div
          className={`p-3 rounded-lg ${isCorrect ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}
        >
          <p className="text-sm font-medium">{isCorrect ? 'Correct!' : 'Incorrect'}</p>
          <p className="text-sm mt-1">{q.explanation}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        {!isChecked && quizAnswers[currentQuizIndex] !== undefined && (
          <button
            onClick={() => onCheck(currentQuizIndex)}
            className="px-6 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Check Answer
          </button>
        )}
        {isChecked && currentQuizIndex < quiz.length - 1 && (
          <button
            onClick={() => setCurrentQuizIndex(currentQuizIndex + 1)}
            className="px-6 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Next Question
          </button>
        )}
        {allChecked && (
          <button
            onClick={onCalculateScore}
            className="px-6 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
          >
            See Final Score
          </button>
        )}
        {!isChecked && quizAnswers[currentQuizIndex] === undefined && <div />}
      </div>
    </div>
  )
}
