import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import './App.css'

const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

function TeamView() {
  const [teams, setTeams] = useState([])
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [games, setGames] = useState([])
  const [selectedGame, setSelectedGame] = useState(null)
  const [gamePrices, setGamePrices] = useState(null)
  const [selectedDate, setSelectedDate] = useState(null)
  const [availableDates, setAvailableDates] = useState([])
  const [availableCategories, setAvailableCategories] = useState([])
  const [selectedCategories, setSelectedCategories] = useState([])
  const [categoryFilterOpen, setCategoryFilterOpen] = useState(false)
  const [modalCategory, setModalCategory] = useState(null)

  // Close category dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const dropdown = document.getElementById('category-dropdown-container')
      if (dropdown && !dropdown.contains(event.target)) {
        setCategoryFilterOpen(false)
      }
    }
    if (categoryFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [categoryFilterOpen])

  useEffect(() => {
    fetchTeams()
  }, [])

  useEffect(() => {
    if (selectedTeam) {
      fetchTeamGames(selectedTeam.key)
    }
  }, [selectedTeam])

  useEffect(() => {
    if (selectedTeam && selectedGame !== null) {
      console.log('useEffect triggered - fetching prices for game index:', selectedGame)
      setSelectedDate(null) // Reset date filter when game changes
      fetchGamePrices(selectedTeam.key, selectedGame)
    } else {
      console.log('useEffect - conditions not met:', { selectedTeam: !!selectedTeam, selectedGame })
    }
  }, [selectedTeam, selectedGame])

  const fetchTeams = async () => {
    try {
      console.log('Fetching teams from:', `${API_URL}/teams`)
      const res = await axios.get(`${API_URL}/teams`)
      console.log('Teams received:', res.data)
      setTeams(res.data)
      if (res.data.length > 0) {
        setSelectedTeam(res.data[0])
      } else {
        console.warn('No teams found')
      }
    } catch (err) {
      console.error('Error fetching teams:', err)
      console.error('API_URL:', API_URL)
    }
  }

  const fetchTeamGames = async (teamKey) => {
    try {
      console.log('Fetching games for team:', teamKey)
      const res = await axios.get(`${API_URL}/teams/${teamKey}`)
      console.log('Games received:', res.data)
      setGames(res.data)
      if (res.data.length > 0) {
        console.log('Setting selectedGame to 0')
        setSelectedGame(0)
      } else {
        console.warn('No games found for team:', teamKey)
        setSelectedGame(null)
      }
    } catch (err) {
      console.error('Error fetching games:', err)
      setSelectedGame(null)
    }
  }

  const fetchGamePrices = async (teamKey, gameIndex) => {
    try {
      console.log('Fetching game prices for:', teamKey, 'game index:', gameIndex)
      const url = `${API_URL}/teams/${teamKey}/game/${gameIndex}`
      console.log('API URL:', url)
      const res = await axios.get(url)
      console.log('Game prices response:', res.data)
      console.log('Has game:', !!res.data.game)
      console.log('Has latest_prices:', !!res.data.latest_prices)
      console.log('Latest prices keys:', res.data.latest_prices ? Object.keys(res.data.latest_prices) : 'none')
      setGamePrices(res.data)
    } catch (err) {
      console.error('Error fetching game prices:', err)
      console.error('Error details:', err.response?.data || err.message)
      setGamePrices(null)
    }
  }

  const getCurrencySymbol = (currency) => {
    const symbols = {
      'USD': '$',
      'GBP': '£',
      'EUR': '€'
    }
    return symbols[currency] || '$'
  }

  const formatPrice = (price, currency = 'USD') => {
    // Prices are now stored in original currency, no conversion needed
    if (!price) return 'N/A'
    const symbol = getCurrencySymbol(currency)
    return `${symbol}${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  // Extract available dates and categories from price history
  useEffect(() => {
    if (gamePrices && gamePrices.prices && Array.isArray(gamePrices.prices)) {
      const dates = new Set()
      const categories = new Set()
      
      gamePrices.prices.forEach(snapshot => {
        const date = new Date(snapshot.timestamp)
        const dateStr = date.toISOString().split('T')[0] // YYYY-MM-DD
        dates.add(dateStr)
        
        // Extract categories
        if (snapshot.prices && typeof snapshot.prices === 'object') {
          Object.keys(snapshot.prices).forEach(cat => {
            if (snapshot.prices[cat] && typeof snapshot.prices[cat] === 'object') {
              // Block-based: add category and category-block combinations
              categories.add(cat)
              Object.keys(snapshot.prices[cat]).forEach(block => {
                categories.add(`${cat} - Block ${block}`)
              })
            } else {
              // Simple category
              categories.add(cat)
            }
          })
        }
      })
      
      const sortedDates = Array.from(dates).sort()
      const sortedCategories = Array.from(categories).sort()
      
      setAvailableDates(sortedDates)
      setAvailableCategories(sortedCategories)
      
      // Select all categories by default
      if (sortedCategories.length > 0 && selectedCategories.length === 0) {
        setSelectedCategories(sortedCategories)
      }
      
      if (sortedDates.length > 0 && !selectedDate) {
        setSelectedDate(sortedDates[sortedDates.length - 1]) // Default to latest date
      }
    } else {
      setAvailableDates([])
      setAvailableCategories([])
      setSelectedDate(null)
    }
  }, [gamePrices])

  const prepareChartData = () => {
    if (!gamePrices || !gamePrices.prices || !Array.isArray(gamePrices.prices)) return []
    
    // Filter by selected date if specified
    let filteredSnapshots = gamePrices.prices
    if (selectedDate) {
      filteredSnapshots = gamePrices.prices.filter(snapshot => {
        const snapshotDate = new Date(snapshot.timestamp).toISOString().split('T')[0]
        return snapshotDate === selectedDate
      })
    }
    
    if (filteredSnapshots.length === 0) return []
    
    // Get currency from gamePrices or default to USD
    const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
    
    // Group by day
    const dailyData = {}
    
    filteredSnapshots.forEach(snapshot => {
      const date = new Date(snapshot.timestamp)
      const dayKey = date.toISOString().split('T')[0] // YYYY-MM-DD
      
      if (!dailyData[dayKey]) {
        dailyData[dayKey] = {
          date: dayKey,
          displayDate: date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
          }),
          prices: {}
        }
      }
      
      // Collect all prices for each category/block
      if (snapshot.prices && typeof snapshot.prices === 'object') {
        Object.keys(snapshot.prices).forEach(cat => {
          if (!dailyData[dayKey].prices[cat]) {
            dailyData[dayKey].prices[cat] = {}
          }
          
          if (snapshot.prices[cat] && typeof snapshot.prices[cat] === 'object') {
            // Block-based prices: {category: {block: price}} or {category: {block: {min, max, count}}}
            Object.keys(snapshot.prices[cat]).forEach(block => {
              const blockKey = block
              if (!dailyData[dayKey].prices[cat][blockKey]) {
                dailyData[dayKey].prices[cat][blockKey] = []
              }
              const priceValue = snapshot.prices[cat][block]
              // Handle both old format (number) and new format (dict with min/max/count)
              if (typeof priceValue === 'number') {
                dailyData[dayKey].prices[cat][blockKey].push(priceValue)
              } else if (priceValue && typeof priceValue === 'object' && 'min' in priceValue) {
                // New format: store min for chart, but we have access to max/count
                dailyData[dayKey].prices[cat][blockKey].push(priceValue.min)
              }
            })
          } else if (typeof snapshot.prices[cat] === 'number') {
            // Simple category prices: {category: price}
            if (!dailyData[dayKey].prices[cat]['_simple']) {
              dailyData[dayKey].prices[cat]['_simple'] = []
            }
            dailyData[dayKey].prices[cat]['_simple'].push(snapshot.prices[cat])
          }
        })
      }
    })
    
    // Collect all unique categories and blocks
    const categoryBlocks = new Set()
    Object.values(dailyData).forEach(day => {
      Object.keys(day.prices).forEach(cat => {
        Object.keys(day.prices[cat]).forEach(block => {
          if (block === '_simple') {
            categoryBlocks.add(cat)
          } else {
            categoryBlocks.add(`${cat} - Block ${block}`)
          }
        })
      })
    })
    
    // Filter categoryBlocks by selectedCategories
    const filteredCategoryBlocks = Array.from(categoryBlocks).filter(catBlock => {
      return selectedCategories.length === 0 || selectedCategories.includes(catBlock)
    })
    
    // Build chart data with daily averages
    const chartData = []
    Object.keys(dailyData).sort().forEach(dayKey => {
      const day = dailyData[dayKey]
      const dataPoint = { time: day.displayDate, date: dayKey }
      
      filteredCategoryBlocks.forEach(catBlock => {
        const [cat, blockPart] = catBlock.split(' - Block ')
        if (blockPart) {
          // Block-based price - calculate average
          const block = blockPart
          if (day.prices[cat] && day.prices[cat][block] && day.prices[cat][block].length > 0) {
            const prices = day.prices[cat][block].filter(p => typeof p === 'number')
            if (prices.length > 0) {
              const avg = prices.reduce((a, b) => a + b, 0) / prices.length
              // Prices already in correct currency, no conversion needed
              const convertedAvg = avg
              dataPoint[catBlock] = Math.round(convertedAvg * 100) / 100
            } else {
              dataPoint[catBlock] = null
            }
          } else {
            dataPoint[catBlock] = null
          }
        } else {
          // Simple category price - calculate average
          if (day.prices[cat] && day.prices[cat]['_simple'] && day.prices[cat]['_simple'].length > 0) {
            const prices = day.prices[cat]['_simple'].filter(p => typeof p === 'number')
            if (prices.length > 0) {
              const avg = prices.reduce((a, b) => a + b, 0) / prices.length
              // Prices already in correct currency, no conversion needed
              const convertedAvg = avg
              dataPoint[cat] = Math.round(convertedAvg * 100) / 100
            } else {
              dataPoint[cat] = null
            }
          } else {
            dataPoint[cat] = null
          }
        }
      })
      
      chartData.push(dataPoint)
    })
    
    return chartData
  }

  const chartData = prepareChartData()
  const colors = ['#d2a8ff', '#79c0ff', '#56d364', '#ffa657', '#ff7b72', '#a5a5ff']

  if (teams.length === 0) {
    return (
      <div className="app-container">
        <div className="header">
          <h1>🏟️ Team Ticket Prices</h1>
        </div>
        <div className="no-data" style={{ padding: '40px', textAlign: 'center' }}>
          <p>Loading teams...</p>
          <p style={{ fontSize: '12px', color: '#6e7681', marginTop: '10px' }}>
            If this persists, check the browser console for errors.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      {/* Team Selector in header area */}
      <div style={{ padding: '10px 20px', borderBottom: '1px solid #30363d', backgroundColor: '#161b22', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
        <select 
          value={selectedTeam?.key || ''} 
          onChange={(e) => {
            const team = teams.find(t => t.key === e.target.value)
            setSelectedTeam(team)
          }}
          className="team-selector"
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #30363d',
            background: '#0d1117',
            color: '#c9d1d9',
            fontSize: '0.9rem',
            cursor: 'pointer'
          }}
        >
          {teams.map(team => (
            <option key={team.key} value={team.key}>
              {team.name} ({team.game_count} games)
            </option>
          ))}
        </select>
      </div>

      <div className="main-content team-view-content">
        {/* Games List */}
        <div className="games-sidebar">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '15px', paddingBottom: '12px', borderBottom: '1px solid #30363d' }}>
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#c9d1d9', fontWeight: '600' }}>
              Games
            </h2>
            {games.length > 0 && (
              <span style={{ 
                fontSize: '0.85rem', 
                color: '#8b949e', 
                background: '#21262d',
                padding: '4px 8px',
                borderRadius: '12px',
                fontWeight: '500'
              }}>
                {games.length}
              </span>
            )}
          </div>
          {games.length === 0 ? (
            <div className="no-data" style={{ padding: '20px', textAlign: 'center' }}>
              <p style={{ color: '#8b949e', fontSize: '0.9rem' }}>No games found for this team.</p>
            </div>
          ) : (
            <div className="games-list">
              {games.map((game, index) => {
                // Calculate price range from all prices
                let minPrice = null
                let maxPrice = null
                
                if (game.latest_prices && Object.keys(game.latest_prices).length > 0) {
                  const allPrices = []
                  Object.values(game.latest_prices).forEach(priceData => {
                    if (priceData && typeof priceData === 'object' && !Array.isArray(priceData)) {
                      // Block-based prices - collect all block prices
                      Object.values(priceData).forEach(price => {
                        if (typeof price === 'number') {
                          allPrices.push(price)
                        } else if (price && typeof price === 'object' && 'min' in price) {
                          // New format with min/max
                          allPrices.push(price.min)
                          if ('max' in price) {
                            allPrices.push(price.max)
                          }
                        }
                      })
                    } else if (typeof priceData === 'number') {
                      allPrices.push(priceData)
                    }
                  })
                  
                  if (allPrices.length > 0) {
                    minPrice = Math.min(...allPrices)
                    maxPrice = Math.max(...allPrices)
                  }
                }
                
                return (
                  <div
                    key={index}
                    className={`game-item ${selectedGame === index ? 'selected' : ''}`}
                    onClick={() => setSelectedGame(index)}
                    style={{ 
                      padding: '14px', 
                      cursor: 'pointer',
                      borderRadius: '6px',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '8px' }}>
                      <span style={{ 
                        fontSize: '0.8rem', 
                        color: selectedGame === index ? '#fff' : '#6e7681', 
                        fontWeight: '600',
                        minWidth: '20px',
                        paddingTop: '2px'
                      }}>
                        {index + 1}.
                      </span>
                      <div style={{ flex: 1 }}>
                        <div className="game-name" style={{ 
                          fontSize: '0.95rem', 
                          fontWeight: '500', 
                          color: selectedGame === index ? '#fff' : '#c9d1d9',
                          lineHeight: '1.4',
                          marginBottom: '6px'
                        }}>
                          {game.match_name}
                        </div>
                        {game.date && (
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: selectedGame === index ? '#c9d1d9' : '#8b949e',
                            marginBottom: '4px'
                          }}>
                            📅 {game.date}
                          </div>
                        )}
                        {minPrice !== null && maxPrice !== null && (
                          <div style={{ 
                            fontSize: '0.85rem',
                            marginTop: '4px'
                          }}>
                            {(() => {
                              const currency = selectedTeam?.currency || 'USD'
                              return minPrice === maxPrice ? (
                                <span style={{ color: selectedGame === index ? '#fff' : '#58a6ff', fontWeight: '600' }}>
                                  {formatPrice(minPrice, currency)}
                                </span>
                              ) : (
                                <span>
                                  <span style={{ color: selectedGame === index ? '#fff' : '#56d364', fontWeight: '600' }}>
                                    {formatPrice(minPrice, currency)}
                                  </span>
                                  <span style={{ margin: '0 6px', color: selectedGame === index ? '#c9d1d9' : '#6e7681' }}>→</span>
                                  <span style={{ color: selectedGame === index ? '#fff' : '#ff7b72', fontWeight: '600' }}>
                                    {formatPrice(maxPrice, currency)}
                                  </span>
                                </span>
                              )
                            })()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Price View - Right Side */}
        <div className="price-view team-price-view">
          {gamePrices && gamePrices.game ? (
            <>
              <div style={{ textAlign: 'center', maxWidth: '900px', width: '100%', margin: '0 auto 30px auto', paddingBottom: '20px', borderBottom: '1px solid #30363d' }}>
                <h2 style={{ margin: '0 0 8px 0', color: '#c9d1d9', fontSize: '1.75rem', fontWeight: '600' }}>
                  {gamePrices.game.match_name}
                </h2>
                {gamePrices.game.date && (
                  <div style={{ fontSize: '1rem', color: '#8b949e', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                    <span>📅</span>
                    <span>{gamePrices.game.date}</span>
                  </div>
                )}
              </div>

              {/* Price History Chart */}
              {chartData.length > 0 && (
                <div className="chart-section" style={{ marginTop: '20px', width: '100%', maxWidth: '900px', margin: '0 auto', background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px', boxSizing: 'border-box' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#c9d1d9', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>📊</span>
                      <span>Daily Price History</span>
                      {gamePrices?.currency && (
                        <span style={{ fontSize: '0.85rem', color: '#8b949e', fontWeight: '400', marginLeft: '8px' }}>
                          ({getCurrencySymbol(gamePrices.currency)})
                        </span>
                      )}
                    </h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                      {availableDates.length > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <label style={{ fontSize: '0.9rem', color: '#8b949e', fontWeight: '500' }}>Date:</label>
                          <select
                            value={selectedDate || ''}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              border: '1px solid #30363d',
                              background: '#0d1117',
                              color: '#c9d1d9',
                              fontSize: '0.85rem',
                              cursor: 'pointer',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => e.target.style.borderColor = '#58a6ff'}
                            onMouseLeave={(e) => e.target.style.borderColor = '#30363d'}
                          >
                            <option value="">All dates</option>
                            {availableDates.map(date => {
                              const dateObj = new Date(date)
                              const displayDate = dateObj.toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })
                              return (
                                <option key={date} value={date}>
                                  {displayDate}
                                </option>
                              )
                            })}
                          </select>
                        </div>
                      )}
                      {availableCategories.length > 0 && (
                        <div style={{ position: 'relative' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label style={{ fontSize: '0.9rem', color: '#8b949e', fontWeight: '500' }}>Categories:</label>
                            <div id="category-dropdown-container" style={{ position: 'relative', display: 'inline-block' }}>
                              <button
                                onClick={() => setCategoryFilterOpen(!categoryFilterOpen)}
                                type="button"
                                style={{
                                  padding: '6px 10px',
                                  borderRadius: '6px',
                                  border: '1px solid #30363d',
                                  background: '#0d1117',
                                  color: '#c9d1d9',
                                  fontSize: '0.85rem',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s',
                                  minWidth: '200px',
                                  textAlign: 'left',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: '8px'
                                }}
                                onMouseEnter={(e) => e.target.style.borderColor = '#58a6ff'}
                                onMouseLeave={(e) => e.target.style.borderColor = '#30363d'}
                              >
                                <span>
                                  {selectedCategories.length === availableCategories.length 
                                    ? 'All categories' 
                                    : selectedCategories.length === 0
                                    ? 'No categories'
                                    : `${selectedCategories.length} selected`}
                                </span>
                                <span style={{ fontSize: '0.7rem', color: '#6e7681' }}>▼</span>
                              </button>
                              {categoryFilterOpen && (
                                <div
                                  style={{
                                    position: 'absolute',
                                    top: '100%',
                                    left: 0,
                                    marginTop: '4px',
                                    background: '#0d1117',
                                    border: '1px solid #30363d',
                                    borderRadius: '6px',
                                    padding: '6px',
                                    maxHeight: '250px',
                                    overflowY: 'auto',
                                    zIndex: 1000,
                                    minWidth: '250px',
                                    boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
                                  }}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <div style={{ 
                                    padding: '4px 6px', 
                                    marginBottom: '6px', 
                                    borderBottom: '1px solid #30363d',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                  }}>
                                    <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>
                                      {selectedCategories.length} of {availableCategories.length}
                                    </span>
                                    <button
                                      onClick={() => {
                                        if (selectedCategories.length === availableCategories.length) {
                                          setSelectedCategories([])
                                        } else {
                                          setSelectedCategories([...availableCategories])
                                        }
                                      }}
                                      style={{
                                        background: 'transparent',
                                        border: '1px solid #30363d',
                                        color: '#58a6ff',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        fontSize: '0.65rem',
                                        cursor: 'pointer'
                                      }}
                                    >
                                      {selectedCategories.length === availableCategories.length ? 'Deselect All' : 'Select All'}
                                    </button>
                                  </div>
                                  {availableCategories.map(cat => {
                                    const isSelected = selectedCategories.includes(cat)
                                    return (
                                      <label
                                        key={cat}
                                        style={{
                                          display: 'flex',
                                          alignItems: 'center',
                                          padding: '4px 6px',
                                          cursor: 'pointer',
                                          borderRadius: '4px',
                                          transition: 'background 0.15s',
                                          backgroundColor: isSelected ? '#1f6feb20' : 'transparent',
                                          fontSize: '0.8rem'
                                        }}
                                        onMouseEnter={(e) => {
                                          if (!isSelected) e.currentTarget.style.backgroundColor = '#21262d'
                                        }}
                                        onMouseLeave={(e) => {
                                          if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'
                                        }}
                                      >
                                        <input
                                          type="checkbox"
                                          checked={isSelected}
                                          onChange={(e) => {
                                            if (e.target.checked) {
                                              setSelectedCategories([...selectedCategories, cat])
                                            } else {
                                              setSelectedCategories(selectedCategories.filter(c => c !== cat))
                                            }
                                          }}
                                          style={{
                                            marginRight: '6px',
                                            cursor: 'pointer',
                                            accentColor: '#58a6ff'
                                          }}
                                        />
                                        <span style={{ 
                                          color: isSelected ? '#c9d1d9' : '#8b949e',
                                          flex: 1
                                        }}>
                                          {cat}
                                        </span>
                                      </label>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Close dropdown when clicking outside */}
                  {categoryFilterOpen && (
                    <div
                      style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        zIndex: 999
                      }}
                      onClick={() => setCategoryFilterOpen(false)}
                    />
                  )}
                  {selectedDate && (
                    <div style={{ marginBottom: '12px', padding: '8px 12px', background: '#1f6feb20', border: '1px solid #1f6feb40', borderRadius: '4px', fontSize: '0.85rem', color: '#58a6ff' }}>
                      📍 Showing data for: <strong>{new Date(selectedDate).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</strong>
                    </div>
                  )}
                  {!selectedDate && availableDates.length > 1 && (
                    <div style={{ marginBottom: '12px', padding: '8px 12px', background: '#21262d', border: '1px solid #30363d', borderRadius: '4px', fontSize: '0.85rem', color: '#8b949e' }}>
                      💡 Showing daily averages across all dates. Use the date selector to focus on a specific day.
                    </div>
                  )}
                  <div className="chart-container" style={{ width: '100%', height: '450px', minHeight: '450px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
                        <defs>
                          {Array.from(new Set(chartData.flatMap(d => Object.keys(d).filter(k => k !== 'time')))).map((cat, i) => (
                            <linearGradient key={cat} id={`grad${i}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={colors[i % colors.length]} stopOpacity={0.4}/>
                              <stop offset="50%" stopColor={colors[i % colors.length]} stopOpacity={0.12}/>
                              <stop offset="100%" stopColor={colors[i % colors.length]} stopOpacity={0}/>
                            </linearGradient>
                          ))}
                        </defs>
                        <CartesianGrid strokeDasharray="2 4" stroke="#21262d" opacity={0.4} vertical={false} />
                        <XAxis 
                          dataKey="time" 
                          stroke="#6e7681" 
                          tick={{ fontSize: 10, fill: '#8b949e' }}
                          axisLine={{ stroke: '#30363d' }}
                          tickLine={{ stroke: '#30363d' }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis 
                          stroke="#6e7681" 
                          tick={{ fontSize: 9, fill: '#8b949e' }}
                          width={45}
                          axisLine={{ stroke: '#30363d' }}
                          tickLine={{ stroke: '#30363d' }}
                          tickFormatter={(value) => {
                            const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                            const symbol = getCurrencySymbol(currency)
                            return `${symbol}${value.toLocaleString()}`
                          }}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#0d1117', 
                            border: '1px solid #30363d',
                            borderRadius: '6px',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                            padding: '8px 10px'
                          }} 
                          itemStyle={{ color: '#c9d1d9', fontSize: '11px', marginBottom: '2px', padding: '2px 0' }}
                          labelStyle={{ color: '#f0f6fc', fontWeight: '600', fontSize: '11px', marginBottom: '4px' }}
                          formatter={(value, name) => {
                            if (!value) return null
                            const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                            const symbol = getCurrencySymbol(currency)
                            // Show only category name (remove " - Block X" part for cleaner display)
                            const displayName = name.split(' - Block ')[0]
                            return [`${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, displayName]
                          }}
                          labelFormatter={(label) => label}
                          separator=": "
                        />
                        {Array.from(new Set(chartData.flatMap(d => Object.keys(d).filter(k => k !== 'time')))).map((cat, i) => (
                          <Area
                            key={cat}
                            name={cat}
                            type="basis"
                            dataKey={cat}
                            stroke={colors[i % colors.length]}
                            strokeWidth={2}
                            fill={`url(#grad${i})`}
                            fillOpacity={0.3}
                            dot={{ fill: colors[i % colors.length], r: 4, strokeWidth: 2, stroke: '#fff', display: 'block' }}
                            activeDot={{ r: 7, fill: colors[i % colors.length], stroke: '#fff', strokeWidth: 2.5, filter: `drop-shadow(0 0 4px ${colors[i % colors.length]})` }}
                            connectNulls
                          />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Category Summary Table - Compact */}
              {gamePrices && gamePrices.latest_prices && Object.keys(gamePrices.latest_prices).length > 0 && (
                <div className="chart-section" style={{ marginTop: '20px', width: '100%', maxWidth: '900px', margin: '20px auto 0 auto', background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '12px', boxSizing: 'border-box' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', color: '#c9d1d9', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>📋</span>
                    <span>Category Price Summary</span>
                    {gamePrices?.currency && (
                      <span style={{ fontSize: '0.75rem', color: '#8b949e', fontWeight: '400', marginLeft: '6px' }}>
                        ({getCurrencySymbol(gamePrices.currency)})
                      </span>
                    )}
                  </h3>
                  <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #30363d' }}>
                          <th style={{ padding: '6px 8px', textAlign: 'left', color: '#8b949e', fontWeight: '600', fontSize: '0.7rem', textTransform: 'uppercase' }}>Category</th>
                          <th style={{ padding: '6px 8px', textAlign: 'right', color: '#8b949e', fontWeight: '600', fontSize: '0.7rem', textTransform: 'uppercase' }}>Price Range</th>
                          <th style={{ padding: '6px 8px', textAlign: 'right', color: '#8b949e', fontWeight: '600', fontSize: '0.7rem', textTransform: 'uppercase' }}>Listings</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(gamePrices.latest_prices).map(([category, blocks], idx) => {
                          if (!blocks || typeof blocks !== 'object') return null
                          
                          const blockEntries = Object.entries(blocks)
                          if (blockEntries.length === 0) return null
                          
                          // Calculate category-wide min/max and total listings
                          let catMin = Infinity
                          let catMax = -Infinity
                          let totalListings = 0
                          
                          blockEntries.forEach(([block, price]) => {
                            let min, max, count
                            if (typeof price === 'number') {
                              min = max = price
                              count = 1
                            } else if (price && typeof price === 'object' && 'min' in price) {
                              min = price.min
                              max = price.max || price.min
                              count = price.count || 1
                            } else {
                              return
                            }
                            
                            catMin = Math.min(catMin, min)
                            catMax = Math.max(catMax, max)
                            totalListings += count
                          })
                          
                          if (catMin === Infinity) return null
                          
                          const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                          
                          return (
                            <tr 
                              key={category} 
                              style={{ borderBottom: '1px solid #21262d', transition: 'background 0.2s', cursor: 'pointer' }} 
                              onMouseEnter={(e) => e.currentTarget.style.background = '#1c2128'} 
                              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                              onClick={() => {
                                // Collect all block details for this category
                                const blockDetails = blockEntries.map(([block, price]) => {
                                  let min, max, count
                                  if (typeof price === 'number') {
                                    min = max = price
                                    count = 1
                                  } else if (price && typeof price === 'object' && 'min' in price) {
                                    min = price.min
                                    max = price.max || price.min
                                    count = price.count || 1
                                  } else {
                                    return null
                                  }
                                  return { block, min, max, count }
                                }).filter(Boolean)
                                
                                setModalCategory({
                                  category,
                                  blocks: blockDetails,
                                  min: catMin,
                                  max: catMax,
                                  totalListings: totalListings
                                })
                              }}
                            >
                              <td style={{ padding: '6px 8px', color: '#c9d1d9', fontWeight: '500', fontSize: '0.8rem' }}>{category}</td>
                              <td style={{ padding: '6px 8px', textAlign: 'right', color: '#c9d1d9', fontSize: '0.8rem' }}>
                                {catMin === catMax ? (
                                  <span style={{ fontWeight: '600', color: '#58a6ff' }}>
                                    {formatPrice(catMin, currency)}
                                  </span>
                                ) : (
                                  <span>
                                    <span style={{ fontWeight: '600', color: '#56d364' }}>
                                      {formatPrice(catMin, currency)}
                                    </span>
                                    <span style={{ margin: '0 4px', color: '#6e7681' }}>→</span>
                                    <span style={{ fontWeight: '600', color: '#ff7b72' }}>
                                      {formatPrice(catMax, currency)}
                                    </span>
                                  </span>
                                )}
                              </td>
                              <td style={{ padding: '6px 8px', textAlign: 'right', color: '#8b949e', fontSize: '0.75rem' }}>
                                {totalListings}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {chartData.length === 0 && gamePrices && gamePrices.game && (
                <div style={{ padding: '40px', textAlign: 'center', color: '#6e7681', fontSize: '1rem' }}>
                  <p>
                    {selectedDate 
                      ? `No price data available for ${new Date(selectedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}.`
                      : 'No price history available yet.'}
                  </p>
                  <p style={{ fontSize: '0.85rem', marginTop: '8px' }}>
                    {selectedDate 
                      ? 'Try selecting a different date or view all dates.'
                      : 'History will appear here as more prices are collected.'}
                  </p>
                </div>
              )}

              {/* Category Details Modal */}
              {modalCategory && (
                <div
                  style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 2000,
                    padding: '20px'
                  }}
                  onClick={() => setModalCategory(null)}
                >
                  <div
                    style={{
                      background: '#161b22',
                      border: '1px solid #30363d',
                      borderRadius: '8px',
                      padding: '20px',
                      maxWidth: '600px',
                      width: '100%',
                      maxHeight: '80vh',
                      overflowY: 'auto',
                      boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#c9d1d9', fontWeight: '600' }}>
                        {modalCategory.category}
                      </h3>
                      <button
                        onClick={() => setModalCategory(null)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#8b949e',
                          fontSize: '1.5rem',
                          cursor: 'pointer',
                          padding: '0',
                          width: '24px',
                          height: '24px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        ×
                      </button>
                    </div>
                    
                    <div style={{ marginBottom: '16px', padding: '12px', background: '#0d1117', borderRadius: '6px', border: '1px solid #30363d' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ color: '#8b949e', fontSize: '0.85rem' }}>Price Range:</span>
                        <span style={{ color: '#c9d1d9', fontWeight: '600' }}>
                          {(() => {
                            const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                            return modalCategory.min === modalCategory.max 
                              ? formatPrice(modalCategory.min, currency)
                              : `${formatPrice(modalCategory.min, currency)} → ${formatPrice(modalCategory.max, currency)}`
                          })()}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: '#8b949e', fontSize: '0.85rem' }}>Total Listings:</span>
                        <span style={{ color: '#c9d1d9', fontWeight: '600' }}>{modalCategory.totalListings}</span>
                      </div>
                    </div>

                    <div>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#8b949e', fontWeight: '600', textTransform: 'uppercase' }}>
                        Blocks ({modalCategory.blocks.length})
                      </h4>
                      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid #30363d' }}>
                              <th style={{ padding: '8px', textAlign: 'left', color: '#8b949e', fontWeight: '600', fontSize: '0.75rem' }}>Block</th>
                              <th style={{ padding: '8px', textAlign: 'right', color: '#8b949e', fontWeight: '600', fontSize: '0.75rem' }}>Price Range</th>
                              <th style={{ padding: '8px', textAlign: 'right', color: '#8b949e', fontWeight: '600', fontSize: '0.75rem' }}>Listings</th>
                            </tr>
                          </thead>
                          <tbody>
                            {modalCategory.blocks.map((block, idx) => {
                              const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                              return (
                                <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                                  <td style={{ padding: '8px', color: '#c9d1d9' }}>{block.block}</td>
                                  <td style={{ padding: '8px', textAlign: 'right', color: '#c9d1d9' }}>
                                    {block.min === block.max 
                                      ? formatPrice(block.min, currency)
                                      : `${formatPrice(block.min, currency)} → ${formatPrice(block.max, currency)}`
                                    }
                                  </td>
                                  <td style={{ padding: '8px', textAlign: 'right', color: '#8b949e' }}>{block.count}</td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : selectedGame !== null ? (
            <div className="no-data" style={{ padding: '40px', textAlign: 'center' }}>
              <p>Loading prices...</p>
              <p style={{ fontSize: '12px', color: '#6e7681', marginTop: '10px' }}>
                {gamePrices ? 'No price data available' : 'Fetching price data...'}
              </p>
            </div>
          ) : (
            <div className="no-data" style={{ padding: '40px', textAlign: 'center' }}>
              <p>Select a game from the list to view prices</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TeamView

