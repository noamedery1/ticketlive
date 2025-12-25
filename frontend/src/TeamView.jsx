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

  const formatPrice = (price) => {
    if (!price) return 'N/A'
    return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const prepareChartData = () => {
    if (!gamePrices || !gamePrices.prices || !Array.isArray(gamePrices.prices)) return []
    
    const chartData = []
    
    // Collect all unique categories and blocks
    const categoryBlocks = new Set()
    gamePrices.prices.forEach(snapshot => {
      if (snapshot.prices && typeof snapshot.prices === 'object') {
        Object.keys(snapshot.prices).forEach(cat => {
          if (snapshot.prices[cat] && typeof snapshot.prices[cat] === 'object') {
            // Block-based prices: {category: {block: price}}
            Object.keys(snapshot.prices[cat]).forEach(block => {
              categoryBlocks.add(`${cat} - Block ${block}`)
            })
          } else if (typeof snapshot.prices[cat] === 'number') {
            // Simple category prices: {category: price}
            categoryBlocks.add(cat)
          }
        })
      }
    })
    
    // Build chart data
    gamePrices.prices.forEach(snapshot => {
      const time = new Date(snapshot.timestamp).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
      
      const dataPoint = { time }
      
      if (snapshot.prices && typeof snapshot.prices === 'object') {
        categoryBlocks.forEach(catBlock => {
          // Check if it's a block-based category
          const [cat, blockPart] = catBlock.split(' - Block ')
          if (blockPart) {
            // Block-based price
            const block = blockPart
            if (snapshot.prices[cat] && snapshot.prices[cat][block]) {
              dataPoint[catBlock] = snapshot.prices[cat][block]
            } else {
              dataPoint[catBlock] = null
            }
          } else {
            // Simple category price
            if (snapshot.prices[cat] && typeof snapshot.prices[cat] === 'number') {
              dataPoint[cat] = snapshot.prices[cat]
            } else {
              dataPoint[cat] = null
            }
          }
        })
      }
      
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

      <div className="main-content" style={{ display: 'flex', flexDirection: 'row', flex: 1, overflow: 'hidden', width: '100%', height: '100%', position: 'relative' }}>
        {/* Games List */}
        <div className="games-sidebar" style={{ flex: '0 0 300px', minWidth: '300px', maxWidth: '300px', overflowY: 'auto' }}>
          <h2>Games {games.length > 0 && `(${games.length})`}</h2>
          {games.length === 0 ? (
            <div className="no-data" style={{ padding: '20px', textAlign: 'center' }}>
              No games found for this team.
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
                    style={{ padding: '16px', cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ 
                        fontSize: '0.85rem', 
                        color: '#6e7681', 
                        fontWeight: '600',
                        minWidth: '24px'
                      }}>
                        {index}.
                      </span>
                      <div className="game-name" style={{ flex: 1, fontSize: '1rem', fontWeight: '500', color: '#c9d1d9' }}>
                        {game.match_name}
                      </div>
                    </div>
                    {minPrice !== null && maxPrice !== null && (
                      <div style={{ 
                        marginLeft: '36px',
                        fontSize: '0.9rem',
                        color: '#8b949e'
                      }}>
                        {minPrice === maxPrice ? (
                          <span style={{ color: '#58a6ff', fontWeight: '600' }}>
                            {formatPrice(minPrice)}
                          </span>
                        ) : (
                          <span>
                            <span style={{ color: '#56d364', fontWeight: '600' }}>
                              {formatPrice(minPrice)}
                            </span>
                            <span style={{ margin: '0 8px', color: '#6e7681' }}>→</span>
                            <span style={{ color: '#ff7b72', fontWeight: '600' }}>
                              {formatPrice(maxPrice)}
                            </span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Price View - Right Side */}
        <div className="price-view" style={{ 
          flex: '1 1 0', 
          padding: '40px', 
          overflowY: 'auto', 
          backgroundColor: '#0d1117',
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'flex-start',
          minWidth: 0,
          position: 'relative',
          height: '100%'
        }}>
          {gamePrices && gamePrices.game ? (
            <>
              <div style={{ textAlign: 'center', maxWidth: '600px', width: '100%', marginBottom: '20px' }}>
                <h2 style={{ margin: '0 0 8px 0', color: '#c9d1d9', fontSize: '1.5rem', fontWeight: '600' }}>
                  {gamePrices.game.match_name}
                </h2>
                {gamePrices.game.date && (
                  <div style={{ fontSize: '0.9rem', color: '#8b949e' }}>
                    📅 {gamePrices.game.date}
                  </div>
                )}
              </div>

              {/* Price History Chart */}
              {chartData.length > 0 && (
                <div className="chart-section" style={{ marginTop: '40px', width: '100%', maxWidth: '600px' }}>
                  <h3 style={{ marginBottom: '16px', fontSize: '1rem', color: '#c9d1d9', fontWeight: '600' }}>
                    📊 Price History
                  </h3>
                  <div className="chart-container" style={{ width: '100%', height: '300px', minHeight: '300px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                          tick={{ fontSize: 9, fill: '#8b949e' }}
                          axisLine={{ stroke: '#30363d' }}
                          tickLine={{ stroke: '#30363d' }}
                        />
                        <YAxis 
                          stroke="#6e7681" 
                          tick={{ fontSize: 9, fill: '#8b949e' }}
                          width={45}
                          axisLine={{ stroke: '#30363d' }}
                          tickLine={{ stroke: '#30363d' }}
                          tickFormatter={(value) => `$${value.toLocaleString()}`}
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
                          formatter={(value) => [`$${value?.toLocaleString() || '0'}`, '']}
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
                  <p>No price history available yet.</p>
                  <p style={{ fontSize: '0.85rem', marginTop: '8px' }}>History will appear here as more prices are collected.</p>
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

