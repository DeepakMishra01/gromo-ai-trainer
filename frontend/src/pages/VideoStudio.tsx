import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { authFetch } from '../api/authFetch'
import {
  Film,
  ChevronRight,
  ChevronLeft,
  Upload,
  Check,
  User,
  Mic,
  Star,
  CheckCircle,
  Package,
  Clock,
} from 'lucide-react'

type Mode = 'single_product' | 'category_overview' | 'comparison' | 'ppt_mode' | 'gamma_ppt'

interface Product {
  id: string
  category_id: string
  category_name: string
  name: string
  payout: string | null
  sub_type: string | null
  description: string | null
}

interface Category {
  id: string
  name: string
  product_count: number
}

interface Avatar {
  id: string
  name: string
  image_path: string
  is_default: boolean
}

interface Voice {
  id: string
  name: string
  language: string
  is_default: boolean
}

const steps = [
  'Select Mode',
  'Select Products',
  'Choose Language',
  'Avatar & Voice',
  'Review & Generate',
]

const avatarColors = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-teal-500',
  'bg-indigo-500',
  'bg-red-500',
]

const languageBadgeColors: Record<string, string> = {
  hinglish: 'bg-purple-100 text-purple-700',
  hindi: 'bg-orange-100 text-orange-700',
  english: 'bg-blue-100 text-blue-700',
}

function getInitials(name: string) {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getAvatarColor(name: string) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

export default function VideoStudio() {
  const [currentStep, setCurrentStep] = useState(0)
  const [mode, setMode] = useState<Mode>('single_product')

  // Step 2: Products
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([])
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('')
  const [productsLoading, setProductsLoading] = useState(false)

  // Step 3: Language & Duration
  const [language, setLanguage] = useState('hinglish')
  const [targetDuration, setTargetDuration] = useState<number | null>(null)

  // Step 4: Avatar & Voice
  const [avatars, setAvatars] = useState<Avatar[]>([])
  const [voices, setVoices] = useState<Voice[]>([])
  const [selectedAvatarId, setSelectedAvatarId] = useState<string>('')
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>('')

  // Step 2 (PPT mode): File upload
  const [pptFile, setPptFile] = useState<File | null>(null)

  // Step 5: Generate
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState(false)
  const [error, setError] = useState('')

  const modes = [
    {
      value: 'single_product' as Mode,
      label: 'Single Product',
      desc: 'Create a detailed video for one product',
      maxProducts: 1,
    },
    {
      value: 'category_overview' as Mode,
      label: 'Category Overview',
      desc: 'Overview video for an entire category',
      maxProducts: 20,
    },
    {
      value: 'comparison' as Mode,
      label: 'Comparison',
      desc: 'Compare multiple products side by side',
      maxProducts: 3,
    },
    {
      value: 'ppt_mode' as Mode,
      label: 'PPT Upload',
      desc: 'Generate video from a PowerPoint presentation',
      maxProducts: 0,
    },
    {
      value: 'gamma_ppt' as Mode,
      label: 'Gamma AI PPT',
      desc: 'Auto-generate professional PPT via Gamma AI, then create video',
      maxProducts: 1,
    },
  ]

  const currentMode = modes.find((m) => m.value === mode)!

  // Fetch products when entering step 2
  useEffect(() => {
    if (currentStep === 1 && products.length === 0 && mode !== 'ppt_mode' || (mode === 'gamma_ppt' && products.length === 0 && currentStep === 1)) {
      setProductsLoading(true)
      Promise.all([
        authFetch('/api/products').then((r) => r.json()),
        authFetch('/api/categories').then((r) => r.json()),
      ])
        .then(([prods, cats]) => {
          setProducts(prods)
          setCategories(cats)
        })
        .catch(() => {})
        .finally(() => setProductsLoading(false))
    }
  }, [currentStep])

  // Fetch avatars/voices when entering step 4
  useEffect(() => {
    if (currentStep === 3) {
      Promise.all([
        authFetch('/api/avatars').then((r) => r.json()),
        authFetch('/api/voices').then((r) => r.json()),
      ])
        .then(([avs, vcs]) => {
          setAvatars(avs)
          setVoices(vcs)
          // Pre-select defaults
          const defaultAvatar = avs.find((a: Avatar) => a.is_default)
          if (defaultAvatar && !selectedAvatarId) setSelectedAvatarId(defaultAvatar.id)
          const defaultVoice = vcs.find((v: Voice) => v.is_default)
          if (defaultVoice && !selectedVoiceId) setSelectedVoiceId(defaultVoice.id)
        })
        .catch(() => {})
    }
  }, [currentStep])

  const toggleProduct = (id: string) => {
    if (mode === 'single_product') {
      setSelectedProductIds([id])
      return
    }
    setSelectedProductIds((prev) => {
      if (prev.includes(id)) return prev.filter((p) => p !== id)
      if (mode === 'comparison' && prev.length >= 3) return prev
      return [...prev, id]
    })
  }

  const selectCategory = (categoryId: string) => {
    const catProducts = products.filter((p) => p.category_id === categoryId)
    setSelectedProductIds(catProducts.map((p) => p.id))
  }

  const filteredProducts = selectedCategoryFilter
    ? products.filter((p) => p.category_id === selectedCategoryFilter)
    : products

  const getSelectedProductNames = () => {
    return products
      .filter((p) => selectedProductIds.includes(p.id))
      .map((p) => p.name)
  }

  const generateTitle = () => {
    const names = getSelectedProductNames()
    if (mode === 'single_product' && names.length > 0) {
      return `${names[0]} - Product Overview`
    }
    if (mode === 'comparison' && names.length >= 2) {
      return `${names.join(' vs ')} - Comparison`
    }
    if (mode === 'category_overview' && selectedProductIds.length > 0) {
      const catName = products.find((p) => selectedProductIds.includes(p.id))?.category_name
      const selectedCat = categories.find((c) => c.id === selectedCategoryFilter)
      return `${selectedCat?.name || catName || 'Category'} - Category Overview`
    }
    if (mode === 'ppt_mode' && pptFile) {
      const baseName = pptFile.name.replace(/\.pptx$/i, '')
      return `${baseName} - PPT Training Video`
    }
    if (mode === 'gamma_ppt' && names.length > 0) {
      return `${names[0]} - Gamma AI Training Video`
    }
    return `Video - ${mode.replace('_', ' ')}`
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError('')
    try {
      let res: Response

      if (mode === 'ppt_mode') {
        // PPT mode: use FormData to upload the file
        if (!pptFile) {
          throw new Error('No PPT file selected')
        }
        const formData = new FormData()
        formData.append('file', pptFile)
        formData.append('language', language)
        if (selectedAvatarId) formData.append('avatar_id', selectedAvatarId)
        if (selectedVoiceId) formData.append('voice_id', selectedVoiceId)
        if (targetDuration) formData.append('target_duration', targetDuration.toString())

        res = await authFetch('/api/video-jobs/ppt-upload', {
          method: 'POST',
          body: formData,
        })
      } else {
        // Standard mode: JSON body
        res = await authFetch('/api/video-jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: generateTitle(),
            job_type: mode,
            product_ids: selectedProductIds,
            avatar_id: selectedAvatarId || null,
            voice_id: selectedVoiceId || null,
            language,
            target_duration: targetDuration,
          }),
        })
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to create video job')
      }
      setGenerated(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setGenerating(false)
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return true
      case 1:
        if (mode === 'ppt_mode') return pptFile !== null
        if (mode === 'single_product' || mode === 'gamma_ppt') return selectedProductIds.length === 1
        if (mode === 'comparison') return selectedProductIds.length >= 2
        return selectedProductIds.length > 0
      case 2:
        return true
      case 3:
        return true
      case 4:
        return !generating && !generated
      default:
        return true
    }
  }

  return (
    <div className="space-y-6">
      {/* Step Progress */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          {steps.map((step, i) => (
            <div key={step} className="flex items-center">
              <div className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    i < currentStep
                      ? 'bg-green-500 text-white'
                      : i === currentStep
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {i < currentStep ? <Check className="w-4 h-4" /> : i + 1}
                </div>
                <span
                  className={`text-sm hidden lg:inline ${
                    i <= currentStep ? 'text-gray-900 font-medium' : 'text-gray-500'
                  }`}
                >
                  {step}
                </span>
              </div>
              {i < steps.length - 1 && (
                <ChevronRight className="w-4 h-4 text-gray-300 mx-2 lg:mx-4" />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Select Mode */}
        {currentStep === 0 && (
          <div className="grid grid-cols-2 gap-4">
            {modes.map((m) => (
              <button
                key={m.value}
                onClick={() => {
                  setMode(m.value)
                  setSelectedProductIds([])
                  setPptFile(null)
                }}
                className={`p-6 rounded-xl border-2 text-left transition-all ${
                  mode === m.value
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h3 className="font-semibold text-gray-900">{m.label}</h3>
                <p className="text-sm text-gray-500 mt-1">{m.desc}</p>
              </button>
            ))}
          </div>
        )}

        {/* Step 2: Select Products */}
        {currentStep === 1 && (
          <div>
            {mode === 'ppt_mode' ? (
              <div className="space-y-4">
                <label
                  htmlFor="ppt-upload"
                  className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer block transition-all ${
                    pptFile
                      ? 'border-primary-400 bg-primary-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <Upload className={`w-12 h-12 mx-auto mb-3 ${pptFile ? 'text-primary-500' : 'text-gray-300'}`} />
                  {pptFile ? (
                    <div>
                      <p className="font-medium text-gray-900">{pptFile.name}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {(pptFile.size / 1024).toFixed(1)} KB
                      </p>
                      <p className="text-xs text-primary-600 mt-2">Click to change file</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-500">
                        Click to select a PowerPoint file (.pptx)
                      </p>
                      <p className="text-xs text-gray-400 mt-1">Only .pptx files are supported</p>
                    </div>
                  )}
                  <input
                    id="ppt-upload"
                    type="file"
                    accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    className="hidden"
                    onChange={(e) => {
                      const selected = e.target.files?.[0] || null
                      setPptFile(selected)
                    }}
                  />
                </label>
              </div>
            ) : productsLoading ? (
              <div className="text-center py-8">
                <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-500">Loading products...</p>
              </div>
            ) : products.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Package className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>No products found. Sync products from the Products page first.</p>
              </div>
            ) : mode === 'category_overview' ? (
              /* ── Category Overview: Show category cards ── */
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">Select a Category</h3>
                  <span className="text-sm text-gray-500">
                    {selectedProductIds.length > 0
                      ? `${selectedProductIds.length} products selected`
                      : 'Pick a category to generate overview'}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categories.map((cat) => {
                    const catProducts = products.filter((p) => p.category_id === cat.id)
                    const isSelected = catProducts.length > 0 && catProducts.every((p) => selectedProductIds.includes(p.id))
                    return (
                      <button
                        key={cat.id}
                        onClick={() => {
                          setSelectedCategoryFilter(cat.id)
                          selectCategory(cat.id)
                        }}
                        className={`p-5 rounded-xl border-2 text-left transition-all ${
                          isSelected
                            ? 'border-primary-500 bg-primary-50 shadow-sm'
                            : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-semibold text-gray-900">{cat.name}</h4>
                            <p className="text-sm text-gray-500 mt-1">{cat.product_count} products</p>
                          </div>
                          <div
                            className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                              isSelected
                                ? 'bg-primary-600'
                                : 'bg-gray-100'
                            }`}
                          >
                            {isSelected && <Check className="w-4 h-4 text-white" />}
                          </div>
                        </div>
                        {catProducts.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1">
                            {catProducts.slice(0, 3).map((p) => (
                              <span key={p.id} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full truncate max-w-[140px]">
                                {p.name}
                              </span>
                            ))}
                            {catProducts.length > 3 && (
                              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                                +{catProducts.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              /* ── Standard product selection (single, comparison, gamma) ── */
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedCategoryFilter}
                      onChange={(e) => setSelectedCategoryFilter(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">All Categories</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name} ({cat.product_count})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">
                      {selectedProductIds.length} selected
                    </span>
                    {(mode === 'single_product' || mode === 'gamma_ppt') && (
                      <span className="text-xs text-gray-400">(select 1)</span>
                    )}
                    {mode === 'comparison' && (
                      <span className="text-xs text-gray-400">(2-3 required)</span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[400px] overflow-y-auto pr-1">
                  {filteredProducts.map((product) => {
                    const isSelected = selectedProductIds.includes(product.id)
                    return (
                      <button
                        key={product.id}
                        onClick={() => toggleProduct(product.id)}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${
                          isSelected
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-gray-900 text-sm truncate">
                              {product.name}
                            </h4>
                            <span className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full mt-1 inline-block">
                              {product.category_name}
                            </span>
                          </div>
                          <div
                            className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ml-2 mt-0.5 ${
                              isSelected
                                ? 'bg-primary-600 border-primary-600'
                                : 'border-gray-300'
                            }`}
                          >
                            {isSelected && <Check className="w-3 h-3 text-white" />}
                          </div>
                        </div>
                        {product.description && (
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                            {product.description}
                          </p>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Language & Duration */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="space-y-4">
              <h3 className="font-medium text-gray-900">Select Language</h3>
              {['hinglish', 'hindi', 'english'].map((lang) => (
                <label
                  key={lang}
                  className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    language === lang
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="language"
                    value={lang}
                    checked={language === lang}
                    onChange={() => setLanguage(lang)}
                    className="text-primary-600"
                  />
                  <span className="capitalize font-medium text-gray-900">{lang}</span>
                  {lang === 'hinglish' && (
                    <span className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full">
                      Recommended
                    </span>
                  )}
                </label>
              ))}
            </div>

            {/* Duration Selector */}
            <div className="space-y-4 pt-2 border-t border-gray-200">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-500" />
                <h3 className="font-medium text-gray-900">Video Duration</h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { value: null, label: 'Auto', desc: 'AI decides (~60-90s)' },
                  { value: 30, label: '30s', desc: 'Quick overview' },
                  { value: 60, label: '1 min', desc: 'Standard' },
                  { value: 90, label: '1.5 min', desc: 'Detailed' },
                  { value: 120, label: '2 min', desc: 'In-depth' },
                  { value: 180, label: '3 min', desc: 'Comprehensive' },
                  { value: 240, label: '4 min', desc: 'Full training' },
                  { value: 300, label: '5 min', desc: 'Extended' },
                ].map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => setTargetDuration(opt.value)}
                    className={`p-3 rounded-xl border-2 text-center transition-all ${
                      targetDuration === opt.value
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <p className="font-semibold text-gray-900 text-sm">{opt.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
                  </button>
                ))}
              </div>
              {targetDuration && (
                <p className="text-xs text-gray-500">
                  The AI will generate a script and adjust speech pace to fit approximately {targetDuration} seconds.
                  Actual duration may vary slightly.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 4: Avatar & Voice */}
        {currentStep === 3 && (
          <div className="space-y-8">
            {/* Avatars */}
            <div>
              <h3 className="font-medium text-gray-900 mb-4">Select Avatar</h3>
              {avatars.length === 0 ? (
                <div className="text-center py-6 text-gray-500 bg-gray-50 rounded-lg">
                  <User className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No avatars available. Add one from the Avatars page.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {avatars.map((avatar) => (
                    <button
                      key={avatar.id}
                      onClick={() => setSelectedAvatarId(avatar.id)}
                      className={`p-4 rounded-xl border-2 text-center transition-all ${
                        selectedAvatarId === avatar.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div
                        className={`w-14 h-14 rounded-full ${getAvatarColor(avatar.name)} flex items-center justify-center mx-auto mb-2`}
                      >
                        <span className="text-lg font-bold text-white">
                          {getInitials(avatar.name)}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{avatar.name}</p>
                      {avatar.is_default && (
                        <span className="inline-flex items-center gap-1 text-xs text-yellow-600 mt-1">
                          <Star className="w-3 h-3" fill="currentColor" />
                          Default
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Voices */}
            <div>
              <h3 className="font-medium text-gray-900 mb-4">Select Voice</h3>
              {voices.length === 0 ? (
                <div className="text-center py-6 text-gray-500 bg-gray-50 rounded-lg">
                  <Mic className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No voices available. Add one from the Voices page.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {voices.map((voice) => (
                    <button
                      key={voice.id}
                      onClick={() => setSelectedVoiceId(voice.id)}
                      className={`p-4 rounded-xl border-2 text-center transition-all ${
                        selectedVoiceId === voice.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-2">
                        <Mic className="w-6 h-6 text-primary-600" />
                      </div>
                      <p className="text-sm font-medium text-gray-900">{voice.name}</p>
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mt-1 capitalize ${
                          languageBadgeColors[voice.language] || 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {voice.language}
                      </span>
                      {voice.is_default && (
                        <span className="flex items-center justify-center gap-1 text-xs text-yellow-600 mt-1">
                          <Star className="w-3 h-3" fill="currentColor" />
                          Default
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 5: Review & Generate */}
        {currentStep === 4 && (
          <div>
            {generated ? (
              <div className="text-center py-8">
                <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
                <h3 className="text-xl font-semibold text-gray-900">Video Job Created!</h3>
                <p className="text-gray-500 mt-2">
                  Your video is being generated. Track its progress in the Video Queue.
                </p>
                <Link
                  to="/video-queue"
                  className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
                >
                  Go to Video Queue
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            ) : (
              <div className="space-y-6">
                <h3 className="font-medium text-gray-900 text-lg">Review Your Selections</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Mode */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">Mode</p>
                    <p className="font-medium text-gray-900 capitalize">
                      {mode.replace(/_/g, ' ')}
                    </p>
                  </div>

                  {/* Language */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">Language</p>
                    <p className="font-medium text-gray-900 capitalize">{language}</p>
                  </div>

                  {/* Duration */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">Duration</p>
                    <p className="font-medium text-gray-900">
                      {targetDuration
                        ? targetDuration >= 60
                          ? `${(targetDuration / 60).toFixed(targetDuration % 60 === 0 ? 0 : 1)} min`
                          : `${targetDuration}s`
                        : 'Auto (~60-90s)'}
                    </p>
                  </div>

                  {/* Gamma AI Badge */}
                  {mode === 'gamma_ppt' && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <p className="text-xs text-purple-500 uppercase font-medium mb-1">AI Engine</p>
                      <p className="font-medium text-purple-700">
                        Gamma AI — Auto-generating professional PPT presentation
                      </p>
                      <p className="text-xs text-purple-500 mt-1">
                        Gamma will create slides, then video pipeline processes audio + composition
                      </p>
                    </div>
                  )}

                  {/* Products / PPT File */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    {mode === 'ppt_mode' ? (
                      <>
                        <p className="text-xs text-gray-500 uppercase font-medium mb-1">
                          PPT File
                        </p>
                        {pptFile ? (
                          <div>
                            <p className="text-sm font-medium text-gray-900">{pptFile.name}</p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {(pptFile.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">No file selected</p>
                        )}
                      </>
                    ) : (
                      <>
                        <p className="text-xs text-gray-500 uppercase font-medium mb-1">
                          Products ({selectedProductIds.length})
                        </p>
                        <div className="space-y-1">
                          {getSelectedProductNames().map((name) => (
                            <p key={name} className="text-sm text-gray-900">
                              {name}
                            </p>
                          ))}
                          {selectedProductIds.length === 0 && (
                            <p className="text-sm text-gray-400">None selected</p>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Avatar */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">Avatar</p>
                    <p className="font-medium text-gray-900">
                      {avatars.find((a) => a.id === selectedAvatarId)?.name || 'None selected'}
                    </p>
                  </div>

                  {/* Voice */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">Voice</p>
                    <p className="font-medium text-gray-900">
                      {voices.find((v) => v.id === selectedVoiceId)?.name || 'None selected'}
                    </p>
                  </div>

                  {/* Title */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500 uppercase font-medium mb-1">
                      Auto-generated Title
                    </p>
                    <p className="font-medium text-gray-900">{generateTitle()}</p>
                  </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <div className="text-center pt-4">
                  <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium text-lg inline-flex items-center gap-2"
                  >
                    <Film className="w-5 h-5" />
                    {generating ? 'Generating...' : 'Generate Video'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        {!generated && (
          <div className="flex justify-between mt-8 pt-6 border-t border-gray-200">
            <button
              onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
              disabled={currentStep === 0}
              className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 text-sm font-medium"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            {currentStep < steps.length - 1 && (
              <button
                onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
                disabled={!canProceed()}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
