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

  // Search state
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
        raw: rawText
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

  // Update effect to add my_price to editable lines
  useEffect(() => {
    if (parsedData && parsedData.lines) {
      const linesWithIds = parsedData.lines.map((l, i) => {
        const price = parseFloat(l.price) || 0
        // Calculate initial my_price based on default commission
        const myPrice = price * (1 + (commission / 100))

        return {
          ...l,
          _id: i,
          match: l.match || parsedData.match || '',
          my_price: myPrice
        }
      })
      setEditableLines(linesWithIds)
      setIsEditable(true)
    }
  }, [parsedData, commission])

  // Recalculate my_price when commission changes
  const updateCommission = () => {
    setEditableLines(prev => prev.map(line => {
      const price = parseFloat(line.price) || 0
      const myPrice = price * (1 + (commission / 100))
      return { ...line, my_price: myPrice }
    }))
  }

  // Update my_price when base price changes manually
  const handleLineChange = (id, field, value) => {
    setEditableLines(prev => prev.map(line => {
      if (line._id === id) {
        const updated = { ...line, [field]: value }

        // If price changed, update my_price automatically
        if (field === 'price') {
          const price = parseFloat(value) || 0
          updated.my_price = price * (1 + (commission / 100))
        }

        return updated
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
        lines: finalLines,
        commission_rate: commission // store used commission rate
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
              <div className="seller-input-container">
                <input
                  type="text"
                  value={sellerInput}
                  onChange={(e) => handleSellerInputChange(e.target.value)}
                  onFocus={() => sellerInput && setShowSuggestions(true)}
                  placeholder="Enter or select seller name"
                  className="seller-input"
                />
                {showSuggestions && sellerSuggestions.length > 0 && (
                  <div className="suggestions-dropdown">
                    {sellerSuggestions.map(seller => (
                      <div
                        key={seller.id}
                        className="suggestion-item"
                        onClick={() => selectSeller(seller)}
                      >
                        <span className="suggestion-icon">✓</span>
                        {seller.name}
                      </div>
                    ))}
                  </div>
                )}
                {sellerInput && !sellers.find(s => s.name.toLowerCase() === sellerInput.toLowerCase()) && (
                  <button
                    onClick={createSeller}
                    className="create-seller-btn"
                    title="Create new seller"
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

                  <div className="commission-control" style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#21262d', padding: '4px 8px', borderRadius: '4px', border: '1px solid #30363d' }}>
                    <label style={{ fontSize: '12px', color: '#8b949e' }}>Commission:</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={commission}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0
                        setCommission(val)
                        // We need to update editable lines immediately
                        setEditableLines(prev => prev.map(line => {
                          const price = parseFloat(line.price) || 0
                          return {
                            ...line,
                            my_price: price * (1 + (val / 100))
                          }
                        }))
                      }}
                      style={{
                        width: '50px',
                        background: '#0d1117',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        borderRadius: '4px',
                        padding: '2px 5px'
                      }}
                    />
                    <span style={{ fontSize: '12px', color: '#8b949e' }}>%</span>
                  </div>

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
                            <th>My Price ({commission}%)</th>
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
                <input
                  type="text"
                  value={searchFilters.seller}
                  onChange={(e) => setSearchFilters({ ...searchFilters, seller: e.target.value })}
                  placeholder="Seller name"
                />
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
              <div className="filter-group">
                <button
                  onClick={handleSearch}
                  disabled={isSearching}
                  className="btn btn-primary search-btn"
                >
                  {isSearching ? 'Searching...' : 'Search'}
                </button>
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
                  <h3>Offer Details</h3>
                  <button
                    onClick={() => setShowDetailDrawer(false)}
                    style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '1.2em' }}
                  >
                    ×
                  </button>
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
                          <th>My Price</th>
                          <th>Currency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedOffer.lines
                          .filter(line => {
                            if (!selectedMatchFilter || selectedMatchFilter === '-' || selectedMatchFilter === 'Match -') return true
                            // If selectedMatchFilter is set, show only lines matching it
                            // Handle loose equality for string/number mismatch
                            if (!line.match) return false // Hide lines without match if we are filtering for a match
                            return parseInt(line.match) === parseInt(selectedMatchFilter)
                          })
                          .map((line, i) => (
                            <tr key={i}>
                              <td>{line.category}</td>
                              <td>{line.quantity ? `${line.quantity} tickets` : '-'}</td>
                              <td>{line.price.toFixed(2)}</td>
                              <td style={{ color: '#56d364', fontWeight: 'bold' }}>{line.my_price ? line.my_price.toFixed(2) : '-'}</td>
                              <td>{line.currency}</td>
                            </tr>
                          ))}
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
