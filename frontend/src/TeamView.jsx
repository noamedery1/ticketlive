import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
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
  const [selectedCategories, setSelectedCategories] = useState([]) // Array of selected categories
  const [availableCategories, setAvailableCategories] = useState([])

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

  // Currency conversion rates (USD is base currency in storage)
  const CURRENCY_RATES = {
    'USD': 1.0,
    'GBP': 0.79,  // 1 USD = 0.79 GBP (approximate)
    'EUR': 0.95   // 1 USD = 0.95 EUR (approximate)
  }

  const getCurrencySymbol = (currency) => {
    const symbols = {
      'USD': '$',
      'GBP': '£',
      'EUR': '€'
    }
    return symbols[currency] || '$'
  }

  const convertPrice = (priceUSD, targetCurrency) => {
    if (!priceUSD || !targetCurrency) return priceUSD
    const rate = CURRENCY_RATES[targetCurrency] || 1.0
    return priceUSD * rate
  }

  const formatPrice = (price, currency = 'USD') => {
    if (!price) return 'N/A'
    const convertedPrice = convertPrice(price, currency)
    const symbol = getCurrencySymbol(currency)
    return `${symbol}${convertedPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
      setSelectedCategories([])
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
            // Block-based prices: {category: {block: price}}
            Object.keys(snapshot.prices[cat]).forEach(block => {
              const blockKey = block
              if (!dailyData[dayKey].prices[cat][blockKey]) {
                dailyData[dayKey].prices[cat][blockKey] = []
              }
              dailyData[dayKey].prices[cat][blockKey].push(snapshot.prices[cat][block])
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
              // Convert to target currency
              const convertedAvg = convertPrice(avg, currency)
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
              // Convert to target currency
              const convertedAvg = convertPrice(avg, currency)
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
              <div style={{ textAlign: 'center', maxWidth: '800px', width: '100%', marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #30363d' }}>
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
                <div className="chart-section" style={{ marginTop: '20px', width: '100%', maxWidth: '900px', background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
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
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <label style={{ fontSize: '0.9rem', color: '#8b949e', fontWeight: '500' }}>Categories:</label>
                          <select
                            multiple
                            value={selectedCategories}
                            onChange={(e) => {
                              const selected = Array.from(e.target.selectedOptions, option => option.value)
                              setSelectedCategories(selected.length > 0 ? selected : availableCategories)
                            }}
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
                              maxHeight: '120px'
                            }}
                            onMouseEnter={(e) => e.target.style.borderColor = '#58a6ff'}
                            onMouseLeave={(e) => e.target.style.borderColor = '#30363d'}
                          >
                            {availableCategories.map(cat => (
                              <option key={cat} value={cat}>
                                {cat}
                              </option>
                            ))}
                          </select>
                          <span style={{ fontSize: '0.75rem', color: '#6e7681' }}>
                            ({selectedCategories.length}/{availableCategories.length})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
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
                            borderRadius: '8px',
                            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                            padding: '12px'
                          }} 
                          itemStyle={{ color: '#c9d1d9', fontSize: '13px', marginBottom: '4px' }}
                          labelStyle={{ color: '#f0f6fc', fontWeight: '600', fontSize: '12px', marginBottom: '8px' }}
                          formatter={(value, name) => {
                            const currency = gamePrices?.currency || selectedTeam?.currency || 'USD'
                            const symbol = getCurrencySymbol(currency)
                            return [`${symbol}${value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0'}`, name]
                          }}
                          labelFormatter={(label) => `${label} (Daily Average)`}
                        />
                        <Legend 
                          wrapperStyle={{ fontSize: '11px', paddingTop: '15px' }}
                          iconType="line"
                          iconSize={12}
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

