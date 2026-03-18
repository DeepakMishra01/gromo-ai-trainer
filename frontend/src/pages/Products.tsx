import { useEffect, useState } from 'react'
import { RefreshCw, Search, Package, X, ChevronRight, IndianRupee } from 'lucide-react'

interface ProductListItem {
  id: string
  category_id: string
  category_name: string
  name: string
  payout: string | null
  sub_type: string | null
  description: string | null
  synced_at: string | null
}

interface ProductDetail {
  id: string
  category_id: string
  category_name: string
  name: string
  payout: string | null
  sub_type: string | null
  benefits_text: string | null
  how_works_text: string | null
  terms_conditions_text: string | null
  description: string | null
  synced_at: string | null
}

interface Category {
  id: string
  name: string
  product_count: number
}

interface SyncResult {
  status: string
  source: string
  products_synced: number
  categories_synced: number
  categories_excluded: number
  products_excluded: number
  message: string
}

export default function Products() {
  const [products, setProducts] = useState<ProductListItem[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<ProductDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    fetchProducts()
    fetchCategories()
  }, [selectedCategory, search])

  const fetchProducts = () => {
    const params = new URLSearchParams()
    if (selectedCategory) params.set('category_id', selectedCategory)
    if (search) params.set('search', search)
    fetch(`/api/products?${params}`)
      .then((r) => r.json())
      .then(setProducts)
      .catch(() => {})
  }

  const fetchCategories = () => {
    fetch('/api/categories')
      .then((r) => r.json())
      .then(setCategories)
      .catch(() => {})
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await fetch('/api/sync', { method: 'POST' })
      const data = await res.json()
      setSyncResult(data)
      fetchProducts()
      fetchCategories()
    } finally {
      setSyncing(false)
    }
  }

  const openProduct = async (id: string) => {
    setLoadingDetail(true)
    try {
      const res = await fetch(`/api/products/${id}`)
      const data = await res.json()
      setSelectedProduct(data)
    } finally {
      setLoadingDetail(false)
    }
  }

  const renderTextSection = (label: string, text: string | null) => {
    if (!text) return null
    const lines = text.split('\n').filter((l) => l.trim())
    return (
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{label}</h4>
        <div className="space-y-1.5">
          {lines.map((line, i) => (
            <div key={i} className="text-sm text-gray-600 flex items-start gap-2">
              <ChevronRight className="w-3 h-3 mt-1 text-primary-500 shrink-0" />
              <span>{line}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Sync Result Banner */}
      {syncResult && (
        <div className={`rounded-lg p-4 flex items-center justify-between ${syncResult.status === 'completed' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          <div>
            <p className={`text-sm font-medium ${syncResult.status === 'completed' ? 'text-green-800' : 'text-red-800'}`}>
              {syncResult.message}
            </p>
            {syncResult.source && (
              <p className="text-xs text-gray-500 mt-1">
                Source: {syncResult.source === 'api' ? 'Live GroMo API' : 'Demo Data'}
              </p>
            )}
          </div>
          <button onClick={() => setSyncResult(null)} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Actions Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search products..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name} ({cat.product_count})
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-500">{products.length} products</span>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
        >
          <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Syncing from GroMo...' : 'Sync Products'}
        </button>
      </div>

      <div className="flex gap-6">
        {/* Products Table */}
        <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${selectedProduct ? 'flex-1' : 'w-full'}`}>
          {products.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Package className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No products found. Click "Sync Products" to fetch from GroMo API.</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Product</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Payout</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {products.map((product) => (
                  <tr
                    key={product.id}
                    onClick={() => openProduct(product.id)}
                    className={`hover:bg-gray-50 cursor-pointer transition-colors ${selectedProduct?.id === product.id ? 'bg-primary-50' : ''}`}
                  >
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{product.name}</td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-0.5 bg-primary-50 text-primary-700 rounded-full text-xs font-medium">
                        {product.category_name}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {product.payout ? (
                        <span className="flex items-center gap-1 text-sm font-semibold text-green-700">
                          <IndianRupee className="w-3 h-3" />
                          {product.payout.replace(/₹|Rs\.?/gi, '').trim()}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Product Detail Panel */}
        {selectedProduct && (
          <div className="w-[440px] bg-white rounded-xl shadow-sm border border-gray-200 overflow-y-auto max-h-[calc(100vh-14rem)]">
            <div className="p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{selectedProduct.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full">
                      {selectedProduct.category_name}
                    </span>
                    {selectedProduct.payout && (
                      <span className="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full font-medium">
                        Payout: {selectedProduct.payout}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedProduct(null)}
                  className="p-1 rounded-lg hover:bg-gray-100"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              {selectedProduct.synced_at && (
                <p className="text-xs text-gray-400 mt-2">
                  Last synced: {new Date(selectedProduct.synced_at).toLocaleString()}
                </p>
              )}
            </div>
            <div className="p-6 space-y-6">
              {renderTextSection('Benefits & Features', selectedProduct.benefits_text)}
              {renderTextSection('How It Works', selectedProduct.how_works_text)}
              {renderTextSection('Terms & Conditions', selectedProduct.terms_conditions_text)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
