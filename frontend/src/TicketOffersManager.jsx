import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import './editable-preview.css'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

function TicketOffersManager() {
  const [activeTab, setActiveTab] = useState('add')
  const [sellers, setSellers] = useState([])
  const [sellerInput, setSellerInput] = useState('')
  const [sellerSuggestions, setSellerSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [rawText, setRawText] = useState('')
  const [parsedData, setParsedData] = useState(null)
  const [isParsing, setIsParsing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [toast, setToast] = useState(null)

  // Options
  const [useAI, setUseAI] = useState(true)

  // Search state
  const [showSearchSellerSuggestions, setShowSearchSellerSuggestions] = useState(false) // New state for search dropdown
  const [searchFilters, setSearchFilters] = useState({
    match: '',
    seller: '',
    category: '',
    min_price: '',
    max_price: '',
    min_quantity: '',
    max_quantity: '',
    keyword: '',
    range: 'all'
  })
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedOffer, setSelectedOffer] = useState(null)
  const [showDetailDrawer, setShowDetailDrawer] = useState(false)
  const [selectedMatchFilter, setSelectedMatchFilter] = useState(null)


  useEffect(() => {
    fetchSellers()
  }, [])

  const fetchSellers = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/tickets/sellers`)
      setSellers(res.data)
    } catch (err) {
      console.error('Error fetching sellers:', err)
      showToast('Error loading sellers', 'error')
    }
  }

  const handleSellerInputChange = (value) => {
    setSellerInput(value)
    if (value.trim()) {
      const filtered = sellers.filter(s =>
        s.name.toLowerCase().includes(value.toLowerCase())
      )
      setSellerSuggestions(filtered)
      setShowSuggestions(true)
    } else {
      setShowSuggestions(false)
    }
  }

  const selectSeller = (seller) => {
    setSellerInput(seller.name)
    setShowSuggestions(false)
  }

  const createSeller = async () => {
    if (!sellerInput.trim()) return

    try {
      const res = await axios.post(`${API_URL}/api/tickets/sellers`, {
        name: sellerInput.trim()
      })
      await fetchSellers()
      setSellerInput(res.data.name)
      setShowSuggestions(false)
      showToast('Seller created', 'success')
    } catch (err) {
      console.error('Error creating seller:', err)
      showToast('Error creating seller', 'error')
    }
  }

  const handleParse = async () => {
    if (!rawText.trim()) {
      showToast('Please enter a message to parse', 'error')
      return
    }

    if (!sellerInput.trim()) {
      showToast('Please enter or select a seller', 'error')
      return
    }

    setIsParsing(true)
    try {
      const res = await axios.post(`${API_URL}/api/tickets/offers/parse`, {
        seller: sellerInput.trim(),
        raw: rawText,
        use_ai: useAI
      })
      setParsedData(res.data)
    } catch (err) {
      console.error('Error parsing:', err)
      showToast('Error parsing message', 'error')
    } finally {
      setIsParsing(false)
    }
  }

  // Editable state
  const [editableLines, setEditableLines] = useState([])
  const [isEditable, setIsEditable] = useState(false)

  // Commission state
  const [commission, setCommission] = useState(20)

  // Update effect to add default my_price to lines (but keep it blank/0 if not set)
  useEffect(() => {
    if (parsedData && parsedData.lines) {
      const linesWithIds = parsedData.lines.map((l, i) => {
        return {
          ...l,
          _id: i,
          match: l.match || parsedData.match || '',
          // Initialize my_price as empty or 0, user must edit it manually
          my_price: l.my_price || ''
        }
      })
      setEditableLines(linesWithIds)
      setIsEditable(true)
    }
  }, [parsedData])

  // Removed auto-commission calculation effects

  // Update my_price when base price changes manually
  const handleLineChange = (id, field, value) => {
    setEditableLines(prev => prev.map(line => {
      if (line._id === id) {
        return { ...line, [field]: value }
      }
      return line
    }))
  }

  const handleDeleteLine = (id) => {
    setEditableLines(prev => prev.filter(l => l._id !== id))
  }

  const handleAddLine = () => {
    const newLine = {
      _id: Date.now(),
      match: parsedData.match || '',
      category: '',
      quantity: 4,
      price: 0,
      my_price: 0,
      currency: 'USD'
    }
    setEditableLines(prev => [...prev, newLine])
  }

  const handleSave = async () => {
    if (!rawText.trim()) {
      showToast('Please enter a message', 'error')
      return
    }

    if (!sellerInput.trim()) {
      showToast('Please enter or select a seller', 'error')
      return
    }

    if (!parsedData) {
      showToast('Please parse the message first', 'error')
      return
    }

    setIsSaving(true)
    try {
      // Reconstruct parsed object from editable lines
      const uniqueMatches = [...new Set(editableLines.map(l => l.match).filter(m => m))]
      const topLevelMatch = uniqueMatches.length === 1 ? parseInt(uniqueMatches[0]) : null

      const finalLines = editableLines.map(({ _id, ...rest }) => ({
        ...rest,
        match: rest.match ? parseInt(rest.match) : null,
        quantity: rest.quantity ? parseInt(rest.quantity) : null,
        price: parseFloat(rest.price) || 0,
        my_price: parseFloat(rest.my_price) || 0
      }))

      const finalParsed = {
        ...parsedData,
        match: topLevelMatch,
        lines: finalLines
      }

      await axios.post(`${API_URL}/api/tickets/offers`, {
        seller: sellerInput.trim(),
        raw: rawText,
        parsed: finalParsed
      })
      showToast('Offer saved successfully!', 'success')
      setRawText('')
      setParsedData(null)
      setEditableLines([])
      setSellerInput('')
    } catch (err) {
      console.error('Error saving offer:', err)
      showToast('Error saving offer', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // Group lines by match for display
  const groupedLines = editableLines.reduce((acc, line) => {
    const matchKey = line.match ? `Match ${line.match}` : 'Unknown Match'
    if (!acc[matchKey]) acc[matchKey] = []
    acc[matchKey].push(line)
    return acc
  }, {})



  /* Split offers by match for display */
  const splitOffersByMatch = (offers) => {
    if (!Array.isArray(offers)) return []
    const splitResults = []

    offers.forEach(offer => {
      if (!offer) return

      const lines = offer.lines || []

      // Determine if revisions/lines dictate a split
      // We group lines by match ID to see if we have multiple matches
      const matchGroups = {}
      let hasSpecificMatches = false

      lines.forEach(line => {
        // line.match might be string or int
        const m = line.match
        if (m) {
          hasSpecificMatches = true
          // Normalize key
          const key = String(m)
          if (!matchGroups[key]) matchGroups[key] = []
          matchGroups[key].push(line)
        } else {
          if (!matchGroups['other']) matchGroups['other'] = []
          matchGroups['other'].push(line)
        }
      })

      const distinctMatchKeys = Object.keys(matchGroups).filter(k => k !== 'other')

      // CASE 1: Multiple distinct matches found in lines -> SPLIT (Mixed Offer)
      // This overrides offer.display_match if it was set to a single one incorrectly
      if (distinctMatchKeys.length > 1) {
        distinctMatchKeys.forEach(mKey => {
          splitResults.push({
            ...offer,
            display_match: parseInt(mKey),
            display_lines: matchGroups[mKey],
            unique_id: `${offer.id}_${mKey}`
          })
        })
        // Handle 'other' (lines with no match) if any
        if (matchGroups['other']) {
          splitResults.push({
            ...offer,
            display_match: '-',
            display_lines: matchGroups['other'],
            unique_id: `${offer.id}_other`
          })
        }
      }
      // CASE 2: Single distinct match found in lines
      else if (distinctMatchKeys.length === 1) {
        const mKey = distinctMatchKeys[0]

        // If there are also 'other' lines, we technically have mixed content (matched + unmatched)
        // ideally we should show them separately or together? 
        // Usually safe to show them together under the main match if it's the only one found.
        // But for strictness let's assume 'other' belongs to that match or create separate row.
        // Let's merge 'other' into this match for simplicity unless explicitly different.

        const allLinesForRow = [...matchGroups[mKey], ...(matchGroups['other'] || [])]

        splitResults.push({
          ...offer,
          display_match: parseInt(mKey),
          display_lines: allLinesForRow,
          unique_id: `${offer.id}_${mKey}`
        })
      }
      // CASE 3: No specific matches in lines (all 'other' or empty)
      else {
        // Fallback to top-level offer.match if available, otherwise '-'
        splitResults.push({
          ...offer,
          display_match: offer.match ? parseInt(offer.match) : '-',
          display_lines: lines,
          unique_id: `${offer.id}_main`
        })
      }
    })

    return splitResults
  }

  // Sorting state
  const [sortConfig, setSortConfig] = useState({ key: 'created_at', direction: 'desc' })

  const handleSort = (key) => {
    let direction = 'asc'
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    }
    setSortConfig({ key, direction })

    const sorted = sortList(searchResults, key, direction)
    setSearchResults(sorted)
  }

  const sortList = (list, key, direction) => {
    if (!list) return []
    return [...list].sort((a, b) => {
      if (!a || !b) return 0

      let valA, valB

      switch (key) {
        case 'price':
          // Sort by minimum base price
          const aLines = a.display_lines || a.lines || []
          const bLines = b.display_lines || b.lines || []

          valA = aLines.length ? Math.min(...aLines.map(l => (l && l.price) || Infinity)) : Infinity
          valB = bLines.length ? Math.min(...bLines.map(l => (l && l.price) || Infinity)) : Infinity

          if (valA === Infinity) valA = 999999
          if (valB === Infinity) valB = 999999
          break
        case 'seller':
          valA = (a.seller || '').toLowerCase()
          valB = (b.seller || '').toLowerCase()
          break
        case 'created_at':
          valA = new Date(a.created_at || 0).getTime()
          valB = new Date(b.created_at || 0).getTime()
          break
        case 'match':
          const mA = a.display_match || a.match
          const mB = b.display_match || b.match
          valA = parseInt(mA) || ((mA === '-' || !mA) ? -1 : 0)
          valB = parseInt(mB) || ((mB === '-' || !mB) ? -1 : 0)
          break
        default:
          return 0
      }

      if (valA < valB) return direction === 'asc' ? -1 : 1
      if (valA > valB) return direction === 'asc' ? 1 : -1
      return 0
    })
  }

  // Wrapper for initial sort
  const sortResults = (results) => {
    return sortList(results, sortConfig.key, sortConfig.direction)
  }

  /* Export Handler */
  const handleExport = async () => {
    try {
      showToast('Preparing export...', 'info')
      const params = {}
      if (searchFilters.match) params.match = parseInt(searchFilters.match)
      if (searchFilters.seller) params.seller = searchFilters.seller
      if (searchFilters.category) params.category = searchFilters.category
      params.range = searchFilters.range

      // Trigger download
      const queryString = new URLSearchParams(params).toString()
      window.location.href = `${API_URL}/api/tickets/export?${queryString}`

      // Note: window.location.href is simple but doesn't handle errors gracefully if backend fails JSON response.
      // But for export it's standard.
    } catch (err) {
      console.error('Error exporting:', err)
      showToast('Error exporting data', 'error')
    }
  }

  /* Edit Handlers in Drawer */
  const updateOfferLinePrice = (lineIndex, newVal) => {
    if (!selectedOffer) return
    const val = parseFloat(newVal)

    // We update the specific line in the full lines array
    const updatedLines = [...selectedOffer.lines]
    if (updatedLines[lineIndex]) {
      // We use '_id' logic or just key update
      // If no _id exists on loaded lines, we assume index is stable for this session
      // Backend expects lines to have some identifier if possible, but our PUT endpoint 
      // maps by index if we send all lines, or we need to align.
      // Let's send index as _id for the backend update map if backend uses it.
      // Current backend implementation: `updates_map = {str(l.get('_id')): ...}`
      // BUT loaded offers usually don't have _id unless we add it on load.
      // Let's ensure we add _id on load or use index assuming stable.

      updatedLines[lineIndex] = {
        ...updatedLines[lineIndex],
        my_price: isNaN(val) ? '' : val,
        // Ensure _id exists for backend mapping
        _id: updatedLines[lineIndex]._id !== undefined ? updatedLines[lineIndex]._id : lineIndex
      }

      setSelectedOffer({
        ...selectedOffer,
        lines: updatedLines
      })
    }
  }

  const saveOfferChanges = async () => {
    if (!selectedOffer) return
    try {
      // Prepare payload: list of lines with _id and my_price
      // We must ensure _id matches what backend expects (index)
      const linesPayload = selectedOffer.lines.map((l, i) => ({
        _id: l._id !== undefined ? l._id : i,
        my_price: l.my_price
      }))

      await axios.put(`${API_URL}/api/tickets/offers/${selectedOffer.id}`, {
        lines: linesPayload
      })

      showToast('Offer prices updated!', 'success')
      // Optionally refresh search results to reflect changes in table
      handleSearch()
    } catch (err) {
      console.error('Error saving changes:', err)
      showToast('Error saving changes', 'error')
    }
  }

  const handleDeleteOffer = async () => {
    if (!selectedOffer) return
    if (!confirm('Are you sure you want to delete this offer? This cannot be undone.')) return

    try {
      await axios.delete(`${API_URL}/api/tickets/offers/${selectedOffer.id}`)
      showToast('Offer deleted', 'success')
      setShowDetailDrawer(false)
      setSelectedOffer(null)
      handleSearch()
    } catch (err) {
      console.error('Error deleting offer:', err)
      showToast('Error deleting offer', 'error')
    }
  }

  const handleSearch = async () => {
    setIsSearching(true)
    try {
      const params = {}
      if (searchFilters.match) params.match = parseInt(searchFilters.match)
      if (searchFilters.seller) params.seller = searchFilters.seller
      if (searchFilters.category) params.category = searchFilters.category
      if (searchFilters.min_price) params.min_price = parseFloat(searchFilters.min_price)
      if (searchFilters.max_price) params.max_price = parseFloat(searchFilters.max_price)
      if (searchFilters.min_quantity) params.min_quantity = parseInt(searchFilters.min_quantity)
      if (searchFilters.max_quantity) params.max_quantity = parseInt(searchFilters.max_quantity)
      if (searchFilters.keyword) params.keyword = searchFilters.keyword
      params.range = searchFilters.range

      const res = await axios.get(`${API_URL}/api/tickets/offers/search`, { params })
      let splitResults = splitOffersByMatch(res.data)

      // Client-side filter: If searching for specific match, only show that match's rows
      // This is needed because the API returns the whole offer if *any* line matches
      if (searchFilters.match) {
        const targetMatch = parseInt(searchFilters.match)
        splitResults = splitResults.filter(
          r => r.display_match === targetMatch
            || r.display_match === '-' // Optional: keep mixed rows if uncertain? Prefer exact match.
        )
        // Refine: strictly keep only rows where display_match matches target
        splitResults = splitResults.filter(r => r.display_match === targetMatch)
      }

      const sortedResults = sortResults(splitResults)
      setSearchResults(sortedResults)
    } catch (err) {
      console.error('Error searching:', err)
      showToast('Error searching offers', 'error')
    } finally {
      setIsSearching(false)
    }
  }

  // Helper for sort icon
  const getSortIcon = (columnKey) => {
    if (sortConfig.key !== columnKey) return '↕'
    return sortConfig.direction === 'asc' ? '↑' : '↓'
  }

  const getPriceSummary = (offer) => {
    if (!offer) return 'No prices'
    const lines = offer.display_lines || offer.lines || []
    if (!lines || lines.length === 0) return 'No prices'

    // Base Prices
    const prices = lines.map(l => l.price).filter(p => p != null)
    const min = prices.length ? Math.min(...prices) : 0
    const max = prices.length ? Math.max(...prices) : 0

    // My Prices
    const myPrices = lines.map(l => l.my_price || l.price).filter(p => p != null)
    const myMin = myPrices.length ? Math.min(...myPrices) : min
    const myMax = myPrices.length ? Math.max(...myPrices) : max

    const currency = lines[0]?.currency || 'USD'

    let baseStr = ''
    if (min === max) baseStr = `${min.toFixed(0)}`
    else baseStr = `${min.toFixed(0)} - ${max.toFixed(0)}`

    let myStr = ''
    if (myMin === myMax) myStr = `${myMin.toFixed(0)}`
    else myStr = `${myMin.toFixed(0)} - ${myMax.toFixed(0)}`

    return (
      <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.85em' }}>
        <span>Original: <b>{currency} {baseStr}</b></span>
        <span style={{ color: '#56d364' }}>My Price: <b>{currency} {myStr}</b></span>
      </div>
    )
  }

  const getQuantitySummary = (offer) => {
    if (!offer) return '-'
    const lines = offer.display_lines || offer.lines || []
    if (!lines || lines.length === 0) return '-'
    const quantities = lines.map(l => l.quantity).filter(q => q != null)
    if (quantities.length === 0) return '-'
    const total = quantities.reduce((a, b) => a + b, 0)
    return total
  }

  const handleRowClick = async (offerId, matchFilter) => {
    try {
      const res = await axios.get(`${API_URL}/api/tickets/offers/${offerId}`)
      setSelectedOffer(res.data)
      setSelectedMatchFilter(matchFilter) // Capture the exact match we clicked on
      setShowDetailDrawer(true)
    } catch (err) {
      console.error('Error fetching offer:', err)
      showToast('Error loading offer details', 'error')
    }
  }

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const formatDate = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="ticket-offers-manager">
      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab-button ${activeTab === 'add' ? 'active' : ''}`}
          onClick={() => setActiveTab('add')}
        >
          Add Offer
        </button>
        <button
          className={`tab-button ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Search Offers
        </button>
      </div>

      {/* Add Offer Tab */}
      {activeTab === 'add' && (
        <div className="tab-content add-offer-tab">
          <div className="add-offer-header">
            <h2>📝 Add New Ticket Offer</h2>
            <p className="subtitle">Paste your WhatsApp message and let us parse it automatically</p>
          </div>

          <div className="form-card">
            <div className="form-section">
              <label className="form-label">
                <span className="label-icon">👤</span>
                Seller
              </label>
              <div className="seller-input-container" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  type="text"
                  value={sellerInput}
                  onChange={(e) => handleSellerInputChange(e.target.value)}
                  onFocus={() => {
                    // specific behavior: if empty, show all. if has text, show filtered.
                    if (sellerInput) {
                      setShowSuggestions(true)
                    } else {
                      setSellerSuggestions(sellers)
                      setShowSuggestions(true)
                    }
                  }}
                  placeholder="Enter or select seller name"
                  className="seller-input"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={() => {
                    if (showSuggestions) {
                      setShowSuggestions(false)
                    } else {
                      setSellerSuggestions(sellers)
                      setShowSuggestions(true)
                    }
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#8b949e',
                    cursor: 'pointer',
                    padding: '0 8px',
                    fontSize: '0.8rem',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Show all sellers"
                >
                  ▼
                </button>

                {showSuggestions && (
                  <div className="suggestions-dropdown" style={{ top: '100%', left: 0, right: 0, position: 'absolute', zIndex: 10 }}>
                    {sellerSuggestions.length > 0 ? sellerSuggestions.map(seller => (
                      <div
                        key={seller.id}
                        className="suggestion-item"
                        onClick={() => selectSeller(seller)}
                      >
                        <span className="suggestion-icon">✓</span>
                        {seller.name}
                      </div>
                    )) : (
                      <div style={{ padding: '8px', color: '#8b949e', fontStyle: 'italic' }}>No sellers found</div>
                    )}
                  </div>
                )}
                {/* Create button logic */}
                {sellerInput && !sellers.find(s => s.name.toLowerCase() === sellerInput.toLowerCase()) && (
                  <button
                    onClick={createSeller}
                    className="create-seller-btn"
                    title="Create new seller"
                    style={{ marginLeft: '8px' }}
                  >
                    <span>+</span> Create
                  </button>
                )}
              </div>
            </div>

            <div className="form-section">
              <label className="form-label">
                <span className="label-icon">💬</span>
                WhatsApp Message
              </label>
              <div className="textarea-wrapper">
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Paste your WhatsApp message here...&#10;&#10;Example:&#10;match 34&#10;cat1:100&#10;cat2:200&#10;cat3:150"
                  rows={8}
                  className="raw-text-input"
                />
                <div className="char-count">{rawText.length} characters</div>
              </div>

              <div style={{ marginTop: '10px' }}>
                <label className="checkbox-container" style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input
                    type="checkbox"
                    checked={useAI}
                    onChange={(e) => setUseAI(e.target.checked)}
                    style={{ marginRight: '8px' }}
                  />
                  ✨ Use AI Parsing (Recommended)
                </label>
              </div>
            </div>

            <div className="form-actions">
              <button
                onClick={handleParse}
                disabled={isParsing || !rawText.trim()}
                className="btn btn-primary btn-large"
              >
                {isParsing ? (
                  <>
                    <span className="btn-spinner">⏳</span> Parsing...
                  </>
                ) : (
                  <>
                    <span className="btn-icon">🔍</span> Parse Message
                  </>
                )}
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving || !parsedData || !rawText.trim()}
                className="btn btn-success btn-large"
              >
                {isSaving ? (
                  <>
                    <span className="btn-spinner">💾</span> Saving...
                  </>
                ) : (
                  <>
                    <span className="btn-icon">💾</span> Save Offer
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Parse Preview */}
          {parsedData && (
            <div className="parse-preview-card">
              <div className="parse-preview-header">
                <h3>✅ Parse Preview (Editable)</h3>
                <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>

                  <span className={`status-badge status-${parsedData.parse_status}`}>
                    {parsedData.parse_status.toUpperCase()}
                  </span>
                  <button className="btn-small" onClick={handleAddLine} title="Add Line">
                    + Add Line
                  </button>
                </div>
              </div>
              <div className="parse-status">
                {parsedData.warnings && parsedData.warnings.length > 0 && (
                  <div className="warnings">
                    <strong>Warnings:</strong>
                    <ul>
                      {parsedData.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="parse-lines-editable">
                  {Object.entries(groupedLines).map(([groupName, lines]) => (
                    <div key={groupName} className="match-group">
                      <h4 className="group-title">{groupName}</h4>
                      <table className="parse-table editable-table">
                        <thead>
                          <tr>
                            <th style={{ width: '60px' }}>Match</th>
                            <th style={{ width: '60px' }}>Qty</th>
                            <th>Category</th>
                            <th>Base Price</th>
                            <th>My Price</th>
                            <th style={{ width: '50px' }}>Curr</th>
                            <th style={{ width: '40px' }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {lines.map((line) => (
                            <tr key={line._id}>
                              <td>
                                <input
                                  type="number"
                                  className="edit-input"
                                  value={line.match}
                                  onChange={(e) => handleLineChange(line._id, 'match', e.target.value)}
                                  placeholder="#"
                                />
                              </td>
                              <td>
                                <input
                                  type="number"
                                  className="edit-input"
                                  value={line.quantity || ''}
                                  onChange={(e) => handleLineChange(line._id, 'quantity', e.target.value)}
                                />
                              </td>
                              <td>
                                <input
                                  type="text"
                                  className="edit-input"
                                  value={line.category}
                                  onChange={(e) => handleLineChange(line._id, 'category', e.target.value)}
                                />
                              </td>
                              <td>
                                <input
                                  type="number"
                                  step="0.01"
                                  className="edit-input"
                                  value={line.price}
                                  onChange={(e) => handleLineChange(line._id, 'price', e.target.value)}
                                />
                              </td>
                              <td>
                                <input
                                  type="number"
                                  step="0.01"
                                  className="edit-input"
                                  value={line.my_price ? line.my_price.toFixed(2) : ''}
                                  style={{ borderColor: '#56d364' }}
                                  onChange={(e) => handleLineChange(line._id, 'my_price', e.target.value)}
                                />
                              </td>
                              <td>{line.currency}</td>
                              <td>
                                <button
                                  className="delete-line-btn"
                                  onClick={() => handleDeleteLine(line._id)}
                                  title="Remove line"
                                >
                                  ×
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                  {editableLines.length === 0 && (
                    <div className="empty-lines">No lines found. Add one?</div>
                  )}
                </div>

              </div>
            </div>
          )}
        </div>
      )}

      {/* Search Tab */}
      {activeTab === 'search' && (
        <div className="tab-content">
          <div className="search-filters">
            <div className="filter-row">
              <div className="filter-group">
                <label>Match Number</label>
                <input
                  type="number"
                  value={searchFilters.match}
                  onChange={(e) => setSearchFilters({ ...searchFilters, match: e.target.value })}
                  placeholder="e.g. 32"
                />
              </div>
              <div className="filter-group">
                <label>Seller</label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchFilters.seller}
                    onChange={(e) => setSearchFilters({ ...searchFilters, seller: e.target.value })}
                    onFocus={() => {
                      // Optional: auto-open on focus if desired, or just leave manual
                      setShowSearchSellerSuggestions(true)
                    }}
                    placeholder="Seller name"
                    style={{ flex: 1, paddingRight: '25px' }} // Space for arrow
                  />
                  <button
                    type="button"
                    onClick={() => setShowSearchSellerSuggestions(!showSearchSellerSuggestions)}
                    style={{
                      position: 'absolute',
                      right: '0',
                      top: '0',
                      bottom: '0',
                      background: 'transparent',
                      border: 'none',
                      color: '#8b949e',
                      cursor: 'pointer',
                      padding: '0 8px',
                      fontSize: '0.8rem'
                    }}
                  >
                    ▼
                  </button>
                  {showSearchSellerSuggestions && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      background: '#161b22',
                      border: '1px solid #30363d',
                      borderRadius: '4px',
                      maxHeight: '200px',
                      overflowY: 'auto',
                      zIndex: 100,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
                    }}>
                      {sellers
                        .filter(s => s.name.toLowerCase().includes((searchFilters.seller || '').toLowerCase()))
                        .map(s => (
                          <div
                            key={s.id}
                            onClick={() => {
                              setSearchFilters({ ...searchFilters, seller: s.name })
                              setShowSearchSellerSuggestions(false)
                            }}
                            style={{
                              padding: '6px 10px',
                              cursor: 'pointer',
                              borderBottom: '1px solid #21262d',
                              fontSize: '0.9rem'
                            }}
                            onMouseEnter={(e) => e.target.style.background = '#21262d'}
                            onMouseLeave={(e) => e.target.style.background = 'transparent'}
                          >
                            {s.name}
                          </div>
                        ))}
                      {sellers.length === 0 && <div style={{ padding: '8px', color: '#8b949e' }}>No sellers</div>}
                    </div>
                  )}
                </div>
              </div>
              <div className="filter-group">
                <label>Category</label>
                <input
                  type="text"
                  value={searchFilters.category}
                  onChange={(e) => setSearchFilters({ ...searchFilters, category: e.target.value })}
                  placeholder="e.g. 1"
                />
              </div>
            </div>
            <div className="filter-row">
              <div className="filter-group">
                <label>Min Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={searchFilters.min_price}
                  onChange={(e) => setSearchFilters({ ...searchFilters, min_price: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div className="filter-group">
                <label>Max Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={searchFilters.max_price}
                  onChange={(e) => setSearchFilters({ ...searchFilters, max_price: e.target.value })}
                  placeholder="9999.99"
                />
              </div>
              <div className="filter-group">
                <label>Min Quantity</label>
                <input
                  type="number"
                  value={searchFilters.min_quantity}
                  onChange={(e) => setSearchFilters({ ...searchFilters, min_quantity: e.target.value })}
                  placeholder="e.g. 2"
                />
              </div>
            </div>
            <div className="filter-row">
              <div className="filter-group">
                <label>Max Quantity</label>
                <input
                  type="number"
                  value={searchFilters.max_quantity}
                  onChange={(e) => setSearchFilters({ ...searchFilters, max_quantity: e.target.value })}
                  placeholder="e.g. 4"
                />
              </div>
              <div className="filter-group">
                <label>Keyword</label>
                <input
                  type="text"
                  value={searchFilters.keyword}
                  onChange={(e) => setSearchFilters({ ...searchFilters, keyword: e.target.value })}
                  placeholder="Search in raw text"
                />
              </div>
              <div className="filter-group">
                {/* Empty space for alignment */}
              </div>
            </div>
            <div className="filter-row">
              <div className="filter-group">
                <label>Time Range</label>
                <select
                  value={searchFilters.range}
                  onChange={(e) => setSearchFilters({ ...searchFilters, range: e.target.value })}
                >
                  <option value="all">All Time</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                </select>
              </div>
              <div className="filter-group" style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                <button
                  onClick={handleSearch}
                  disabled={isSearching}
                  className="btn btn-primary search-btn"
                  style={{ flex: 2, height: '38px', justifyContent: 'center' }}
                >
                  {isSearching ? 'Searching...' : 'Search'}
                </button>
                {searchResults.length > 0 && (
                  <button
                    onClick={handleExport}
                    className="btn btn-secondary"
                    title="Export filtered results to Excel"
                    style={{ flex: 1, height: '38px', justifyContent: 'center', whiteSpace: 'nowrap' }}
                  >
                    📥 Export ({searchResults.length})
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Search Results */}
          <div className="search-results">
            <div className="results-header">
              <h3>Results ({searchResults.length})</h3>
            </div>
            {searchResults.length > 0 ? (
              <div className="results-table-container">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('created_at')} className="sortable-th">
                        Created {getSortIcon('created_at')}
                      </th>
                      <th onClick={() => handleSort('seller')} className="sortable-th">
                        Seller {getSortIcon('seller')}
                      </th>
                      <th onClick={() => handleSort('match')} className="sortable-th">
                        Match {getSortIcon('match')}
                      </th>
                      <th onClick={() => handleSort('price')} className="sortable-th">
                        Price Summary {getSortIcon('price')}
                      </th>
                      <th>Quantity</th>
                      <th>Categories</th>
                      <th>Raw Snippet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.map((offer) => {
                      if (!offer) return null
                      const rawSnippet = offer.raw ? offer.raw.substring(0, 60) + '...' : ''
                      const priceSummary = getPriceSummary(offer)
                      const quantitySummary = getQuantitySummary(offer)
                      // Use display_lines for categories
                      const lines = offer.display_lines || offer.lines || []
                      const categories = lines.map(l => l.category).join(', ') || '-'

                      return (
                        <tr
                          key={offer.unique_id || offer.id}
                          onClick={() => handleRowClick(offer.id, offer.display_match)}
                          className="result-row"
                        >
                          <td className="date-cell">{formatDate(offer.created_at)}</td>
                          <td className="seller-cell">{offer.seller}</td>
                          <td className="match-cell">{offer.display_match || offer.match || '-'}</td>
                          <td className="price-summary-cell">
                            <span className="price-badge">{priceSummary}</span>
                          </td>
                          <td className="quantity-cell">{quantitySummary}</td>
                          <td className="categories-cell">{categories}</td>
                          <td className="raw-snippet">{rawSnippet}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="no-results">
                {isSearching ? (
                  <div className="loading-state">
                    <span className="spinner">⏳</span>
                    <span>Searching...</span>
                  </div>
                ) : (
                  <div className="empty-state">
                    <span className="empty-icon">🔍</span>
                    <p>No results found. Try adjusting your filters.</p>
                  </div>
                )}
              </div>
            )}

            {/* ... */}

            {/* Detail Drawer / Section */}
            {showDetailDrawer && selectedOffer && (
              <div className="offer-details-container" style={{ marginTop: '20px', borderTop: '1px solid #30363d', paddingTop: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                  <h3>Offer Details (Editable)</h3>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      onClick={saveOfferChanges}
                      className="btn btn-success btn-small"
                    >
                      💾 Save Changes
                    </button>
                    <button
                      onClick={handleDeleteOffer}
                      className="btn btn-danger btn-small"
                      style={{ background: '#d73a49', border: '1px solid #cb2431', color: 'white' }}
                    >
                      🗑️ Delete
                    </button>
                    <button
                      onClick={() => setShowDetailDrawer(false)}
                      style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '1.2em' }}
                    >
                      ×
                    </button>
                  </div>
                </div>

                {selectedOffer.lines && selectedOffer.lines.length > 0 && (
                  <div className="detail-section">
                    <strong>Category/Price Lines {selectedMatchFilter && selectedMatchFilter !== '-' ? `(Match ${selectedMatchFilter})` : ''}:</strong>
                    <table className="detail-table">
                      <thead>
                        <tr>
                          <th>Category</th>
                          <th>Quantity</th>
                          <th>Base Price</th>
                          <th style={{ width: '150px' }}>My Price</th>
                          <th>Currency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedOffer.lines
                          .map((line, i) => {
                            // Only show relevant lines if filter active
                            if (selectedMatchFilter && selectedMatchFilter !== '-' && selectedMatchFilter !== 'Match -') {
                              if (!line.match || parseInt(line.match) !== parseInt(selectedMatchFilter)) return null
                            }

                            // We need to match the line in the full array index to update state correctly
                            // Since map might skip, we pass actual index 'i' to handler
                            return (
                              <tr key={i}>
                                <td>{line.category}</td>
                                <td>{line.quantity ? `${line.quantity} tickets` : '-'}</td>
                                <td>{line.price.toFixed(2)}</td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={line.my_price || ''}
                                    onChange={(e) => updateOfferLinePrice(i, e.target.value)}
                                    className="edit-input"
                                    style={{ borderColor: '#56d364', width: '100%' }}
                                    placeholder="Set Price"
                                  />
                                </td>
                                <td>{line.currency}</td>
                              </tr>
                            )
                          })}
                      </tbody>
                    </table>
                  </div>
                )}

                {selectedOffer.warnings && selectedOffer.warnings.length > 0 && (
                  <div className="detail-section">
                    <strong>Warnings:</strong>
                    <ul>
                      {selectedOffer.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="detail-section">
                  <strong>Raw Message:</strong>
                  <pre className="raw-message">{selectedOffer.raw}</pre>
                </div>
              </div>
            )}


          </div>
        </div>
      )}
    </div>
  )
}

export default TicketOffersManager
