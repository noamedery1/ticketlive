import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import './App.css'

// Use local backend for development, empty for production (same origin)
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
console.log('API_URL:', API_URL, 'DEV mode:', import.meta.env.DEV)

function App() {
  const [matches, setMatches] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [history, setHistory] = useState(null)
  const [timeRange, setTimeRange] = useState('all')
  const [selectedDate, setSelectedDate] = useState(null)


  useEffect(() => {
    fetchMatches()
    const interval = setInterval(fetchMatches, 120000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedMatch) {
      fetchHistory(selectedMatch.match_url)
      const historyInterval = setInterval(() => {
        fetchHistory(selectedMatch.match_url)
      }, 120000)
      return () => clearInterval(historyInterval)
    }
  }, [selectedMatch])

  const fetchMatches = async () => {
    try {
      const url = API_URL + '/matches'
      console.log('Fetching matches from:', url)
      const res = await axios.get(url)
      console.log('Matches received:', res.data.length)
      setMatches(res.data)
      if (res.data.length > 0 && !selectedMatch) {
        setSelectedMatch(res.data[0])
      }
    } catch (err) { 
      console.error('Error fetching matches:', err)
      console.error('API_URL was:', API_URL)
    }
  }

  const fetchHistory = async (url) => {
    try {
      const apiUrl = API_URL + '/history'
      console.log('Fetching history from:', apiUrl, 'for match:', url)
      const res = await axios.get(apiUrl, { params: { match_url: url } })
      console.log('History received:', res.data)
      setHistory(res.data)
    } catch (err) { 
      console.error('Error fetching history:', err)
      console.error('API_URL was:', API_URL)
    }
  }

  const processChartData = (sourcePrefix) => {
    if (!history) return []
    const now = new Date().getTime()
    let cutoff = 0
    
    if (selectedDate) {
      // Jump to specific date - show data for that day
      const selected = new Date(selectedDate)
      selected.setHours(0, 0, 0, 0)
      const dayStart = selected.getTime()
      const dayEnd = dayStart + 24 * 3600 * 1000
      cutoff = dayStart
      // Filter to only show data within the selected day
      const merged = {}
      const sourceKey = sourcePrefix === 'Via_' ? 'viagogo' : 'ftn'
      if (history[sourceKey] && history[sourceKey].data) {
        Object.keys(history[sourceKey].data).forEach(cat => {
          history[sourceKey].data[cat].forEach(pt => {
            const date = new Date(pt.timestamp)
            const ts = date.getTime()
            if (ts >= dayStart && ts < dayEnd) {
              const timeStr = date.toLocaleString('en-US', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
              })
              if (!merged[ts]) merged[ts] = { time: timeStr, sortTime: ts, isNewPrice: true }
              const key = sourcePrefix + cat
              merged[ts][key] = pt.price
            }
          })
        })
      }
      return Object.values(merged).sort((a, b) => a.sortTime - b.sortTime)
    } else {
      // Normal time range filtering
      cutoff = timeRange === '24h' ? now - 24 * 3600 * 1000 :
        timeRange === '7d' ? now - 7 * 24 * 3600 * 1000 : 0
    }

    const merged = {}
    const sourceKey = sourcePrefix === 'Via_' ? 'viagogo' : 'ftn'
    if (history[sourceKey] && history[sourceKey].data) {
      Object.keys(history[sourceKey].data).forEach(cat => {
        history[sourceKey].data[cat].forEach(pt => {
          const date = new Date(pt.timestamp)
          const ts = date.getTime()
          if (ts >= cutoff) {
            const timeStr = date.toLocaleString('en-US', {
              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            })
            if (!merged[ts]) merged[ts] = { time: timeStr, sortTime: ts, isNewPrice: true }
            const key = sourcePrefix + cat
            merged[ts][key] = pt.price
          }
        })
      })
    }
    return Object.values(merged).sort((a, b) => a.sortTime - b.sortTime)
  }

  const viagogoChartData = processChartData('Via_')
  const ftnChartData = processChartData('FTN_')

  const getLatestPrice = (source, cat) => {
    if (!history || !history[source] || !history[source].data || !history[source].data[cat]) return null
    const pts = history[source].data[cat]
    if (pts.length === 0) return null
    return pts[pts.length - 1].price
  }

  const formatPrice = (val) => {
    if (val === null || val === undefined) return '-'
    return '$' + val.toLocaleString()
  }

  const [sidebarWidth, setSidebarWidth] = useState(250)
  const [isResizing, setIsResizing] = useState(false)

  // Resizable Sidebar Logic
  const startResizing = React.useCallback((mouseDownEvent) => {
    setIsResizing(true)
  }, [])

  const stopResizing = React.useCallback(() => {
    setIsResizing(false)
  }, [])

  const resize = React.useCallback((mouseMoveEvent) => {
    if (isResizing) {
      let newWidth = mouseMoveEvent.clientX
      if (newWidth < 150) newWidth = 150
      if (newWidth > 600) newWidth = 600
      setSidebarWidth(newWidth)
    }
  }, [isResizing])

  useEffect(() => {
    window.addEventListener("mousemove", resize)
    window.addEventListener("mouseup", stopResizing)
    return () => {
      window.removeEventListener("mousemove", resize)
      window.removeEventListener("mouseup", stopResizing)
    }
  }, [resize, stopResizing])

  return (
    <div className='dashboard'>
      <div className='sidebar' style={{ width: sidebarWidth }}>
        <div className='logo'>ViagogoMonitor</div>
        <div className='match-list'>
          {matches.map(m => (
            <div
              key={m.match_url}
              className={'match-item ' + (selectedMatch?.match_url === m.match_url ? 'active' : '')}
              onClick={() => setSelectedMatch(m)}
            >
              <div className='match-name'>{m.match_name}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Resizer Handle */}
      <div
        className='resizer'
        onMouseDown={startResizing}
      />

      <div className='main-content'>
        {selectedMatch && (
          <>
            <div className='header'>
              <h1>{selectedMatch.match_name}</h1>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <span className='last-updated'>Auto-refresh: 10m</span>
                <div className='time-filters' style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
                  {['24h', '7d', 'all'].map(r => (
                    <button
                      key={r} onClick={() => { setTimeRange(r); setSelectedDate(null); }}
                      className={timeRange === r && !selectedDate ? 'active' : ''}
                      style={{
                        padding: '4px 8px', margin: '0 2px', borderRadius: '4px', border: 'none',
                        background: timeRange === r && !selectedDate ? '#1f6feb' : '#21262d', 
                        color: 'white', cursor: 'pointer'
                      }}
                    >
                      {r}
                    </button>
                  ))}
                </div>
                <input
                  type='date'
                  value={selectedDate || ''}
                  onChange={(e) => {
                    if (e.target.value) {
                      setSelectedDate(e.target.value)
                      setTimeRange('all')
                    } else {
                      setSelectedDate(null)
                    }
                  }}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    border: '1px solid #30363d',
                    background: '#161b22',
                    color: '#c9d1d9',
                    fontSize: '0.85rem'
                  }}
                  title='Jump to specific day'
                />
                {selectedDate && (
                  <button
                    onClick={() => { setSelectedDate(null); setTimeRange('all'); }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      background: '#d1242f',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '0.85rem'
                    }}
                  >
                    Clear Date
                  </button>
                )}
              </div>
            </div>

            <div className='split-container'>
              {/* --- LEFT: VIAGOGO --- */}
              <div className='split-pane'>
                <div className='pane-title viagogo-title'>Viagogo</div>

                <div className='stats-grid'>
                  {['Category 1', 'Category 2', 'Category 3', 'Category 4'].map((cat, i) => (
                    <div key={cat} className='stat-card' style={{ borderColor: '#30363d' }}>
                      <div className='stat-label'>{cat}</div>
                      <div className='stat-value' style={{ color: i === 0 ? '#d2a8ff' : i === 1 ? '#79c0ff' : i === 2 ? '#56d364' : '#ffa657' }}>
                        {formatPrice(getLatestPrice('viagogo', cat))}
                      </div>
                    </div>
                  ))}
                </div>

                <div className='chart-section'>
                  <div className='chart-container-inner'>
                    {viagogoChartData.length > 0 ? (
                      <ResponsiveContainer width='100%' height='100%'>
                        <AreaChart data={viagogoChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id='gradVia1' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#d2a8ff' stopOpacity={0.4}/>
                              <stop offset='50%' stopColor='#d2a8ff' stopOpacity={0.15}/>
                              <stop offset='100%' stopColor='#d2a8ff' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradVia2' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#79c0ff' stopOpacity={0.4}/>
                              <stop offset='50%' stopColor='#79c0ff' stopOpacity={0.15}/>
                              <stop offset='100%' stopColor='#79c0ff' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradVia3' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#56d364' stopOpacity={0.4}/>
                              <stop offset='50%' stopColor='#56d364' stopOpacity={0.15}/>
                              <stop offset='100%' stopColor='#56d364' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradVia4' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#ffa657' stopOpacity={0.4}/>
                              <stop offset='50%' stopColor='#ffa657' stopOpacity={0.15}/>
                              <stop offset='100%' stopColor='#ffa657' stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray='2 4' stroke='#21262d' opacity={0.4} vertical={false} />
                          <XAxis 
                            dataKey='time' 
                            stroke='#6e7681' 
                            tick={{ fontSize: 9, fill: '#8b949e' }}
                            axisLine={{ stroke: '#30363d' }}
                            tickLine={{ stroke: '#30363d' }}
                          />
                          <YAxis 
                            stroke='#6e7681' 
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
                            iconType='line'
                            iconSize={12}
                          />
                          <Area 
                            name='Cat 1' 
                            type='basis' 
                            dataKey='Via_Category 1' 
                            stroke='#d2a8ff' 
                            strokeWidth={2.5}
                            fill='url(#gradVia1)' 
                            fillOpacity={1}
                            dot={{ fill: '#d2a8ff', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#d2a8ff', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #d2a8ff)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 2' 
                            type='basis' 
                            dataKey='Via_Category 2' 
                            stroke='#79c0ff' 
                            strokeWidth={2.5}
                            fill='url(#gradVia2)' 
                            fillOpacity={1}
                            dot={{ fill: '#79c0ff', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#79c0ff', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #79c0ff)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 3' 
                            type='basis' 
                            dataKey='Via_Category 3' 
                            stroke='#56d364' 
                            strokeWidth={2.5}
                            fill='url(#gradVia3)' 
                            fillOpacity={1}
                            dot={{ fill: '#56d364', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#56d364', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #56d364)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 4' 
                            type='basis' 
                            dataKey='Via_Category 4' 
                            stroke='#ffa657' 
                            strokeWidth={2.5}
                            fill='url(#gradVia4)' 
                            fillOpacity={1}
                            dot={{ fill: '#ffa657', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#ffa657', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #ffa657)' }} 
                            connectNulls 
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e' }}>No Data</div>}
                  </div>
                </div>
              </div>

              {/* --- RIGHT: FTN --- */}
              <div className='split-pane'>
                <div className='pane-title ftn-title'>Football Ticket Net</div>

                <div className='stats-grid'>
                  {['Category 1', 'Category 2', 'Category 3', 'Category 4'].map((cat, i) => (
                    <div key={cat} className='stat-card' style={{ borderColor: '#30363d' }}>
                      <div className='stat-label'>{cat}</div>
                      <div className='stat-value' style={{ color: i === 0 ? '#d2a8ff' : i === 1 ? '#79c0ff' : i === 2 ? '#56d364' : '#ffa657' }}>
                        {formatPrice(getLatestPrice('ftn', cat))}
                      </div>
                    </div>
                  ))}
                </div>

                <div className='chart-section'>
                  <div className='chart-container-inner'>
                    {ftnChartData.length > 0 ? (
                      <ResponsiveContainer width='100%' height='100%'>
                        <AreaChart data={ftnChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id='gradFtn1' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#d2a8ff' stopOpacity={0.35}/>
                              <stop offset='50%' stopColor='#d2a8ff' stopOpacity={0.12}/>
                              <stop offset='100%' stopColor='#d2a8ff' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradFtn2' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#79c0ff' stopOpacity={0.35}/>
                              <stop offset='50%' stopColor='#79c0ff' stopOpacity={0.12}/>
                              <stop offset='100%' stopColor='#79c0ff' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradFtn3' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#56d364' stopOpacity={0.35}/>
                              <stop offset='50%' stopColor='#56d364' stopOpacity={0.12}/>
                              <stop offset='100%' stopColor='#56d364' stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id='gradFtn4' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#ffa657' stopOpacity={0.35}/>
                              <stop offset='50%' stopColor='#ffa657' stopOpacity={0.12}/>
                              <stop offset='100%' stopColor='#ffa657' stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray='2 4' stroke='#21262d' opacity={0.4} vertical={false} />
                          <XAxis 
                            dataKey='time' 
                            stroke='#6e7681' 
                            tick={{ fontSize: 9, fill: '#8b949e' }}
                            axisLine={{ stroke: '#30363d' }}
                            tickLine={{ stroke: '#30363d' }}
                          />
                          <YAxis 
                            stroke='#6e7681' 
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
                            iconType='line'
                            iconSize={12}
                          />
                          <Area 
                            name='Cat 1' 
                            type='basis' 
                            dataKey='FTN_Category 1' 
                            stroke='#d2a8ff' 
                            strokeWidth={2.5}
                            strokeDasharray='6 4'
                            fill='url(#gradFtn1)' 
                            fillOpacity={1}
                            dot={{ fill: '#d2a8ff', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#d2a8ff', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #d2a8ff)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 2' 
                            type='basis' 
                            dataKey='FTN_Category 2' 
                            stroke='#79c0ff' 
                            strokeWidth={2.5}
                            strokeDasharray='6 4'
                            fill='url(#gradFtn2)' 
                            fillOpacity={1}
                            dot={{ fill: '#79c0ff', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#79c0ff', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #79c0ff)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 3' 
                            type='basis' 
                            dataKey='FTN_Category 3' 
                            stroke='#56d364' 
                            strokeWidth={2.5}
                            strokeDasharray='6 4'
                            fill='url(#gradFtn3)' 
                            fillOpacity={1}
                            dot={{ fill: '#56d364', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#56d364', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #56d364)' }} 
                            connectNulls 
                          />
                          <Area 
                            name='Cat 4' 
                            type='basis' 
                            dataKey='FTN_Category 4' 
                            stroke='#ffa657' 
                            strokeWidth={2.5}
                            strokeDasharray='6 4'
                            fill='url(#gradFtn4)' 
                            fillOpacity={1}
                            dot={{ fill: '#ffa657', r: 3, strokeWidth: 1.5, stroke: '#fff' }}
                            activeDot={{ r: 6, fill: '#ffa657', stroke: '#fff', strokeWidth: 2, filter: 'drop-shadow(0 0 4px #ffa657)' }} 
                            connectNulls 
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e' }}>No Data</div>}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default App