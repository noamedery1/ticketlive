import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './App.css'

const API_URL = ''

function App() {
  const [matches, setMatches] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [history, setHistory] = useState(null)
  const [timeRange, setTimeRange] = useState('all')


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
      const res = await axios.get(API_URL + '/matches')
      setMatches(res.data)
      if (res.data.length > 0 && !selectedMatch) {
        setSelectedMatch(res.data[0])
      }
    } catch (err) { console.error(err) }
  }

  const fetchHistory = async (url) => {
    try {
      const res = await axios.get(API_URL + '/history', { params: { match_url: url } })
      setHistory(res.data)
    } catch (err) { console.error(err) }
  }

  const processChartData = (sourcePrefix) => {
    if (!history) return []
    const now = new Date().getTime()
    const cutoff = timeRange === '24h' ? now - 24 * 3600 * 1000 :
      timeRange === '7d' ? now - 7 * 24 * 3600 * 1000 : 0

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
            if (!merged[ts]) merged[ts] = { time: timeStr, sortTime: ts }
            // AVOID TEMPLATE LITERALS HERE due to python-bash escaping hell
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
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <span className='last-updated'>Auto-refresh: 10m</span>
                <div className='time-filters'>
                  {['24h', '7d', 'all'].map(r => (
                    <button
                      key={r} onClick={() => setTimeRange(r)}
                      className={timeRange === r ? 'active' : ''}
                      style={{
                        padding: '4px 8px', margin: '0 2px', borderRadius: '4px', border: 'none',
                        background: timeRange === r ? '#1f6feb' : '#21262d', color: 'white', cursor: 'pointer'
                      }}
                    >
                      {r}
                    </button>
                  ))}
                </div>
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
                        <LineChart data={viagogoChartData}>
                          <CartesianGrid strokeDasharray='3 3' stroke='#30363d' />
                          <XAxis dataKey='time' stroke='#8b949e' tick={{ fontSize: 10 }} hide={true} />
                          <YAxis stroke='#8b949e' tick={{ fontSize: 10 }} width={40} />
                          <Tooltip contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d' }} itemStyle={{ color: '#c9d1d9' }} />
                          <Legend wrapperStyle={{ fontSize: '11px' }} />
                          <Line name='Cat 1' type='monotone' dataKey='Via_Category 1' stroke='#d2a8ff' strokeWidth={2} dot={false} connectNulls />
                          <Line name='Cat 2' type='monotone' dataKey='Via_Category 2' stroke='#79c0ff' strokeWidth={2} dot={false} connectNulls />
                          <Line name='Cat 3' type='monotone' dataKey='Via_Category 3' stroke='#56d364' strokeWidth={2} dot={false} connectNulls />
                          <Line name='Cat 4' type='monotone' dataKey='Via_Category 4' stroke='#ffa657' strokeWidth={2} dot={false} connectNulls />
                        </LineChart>
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
                        <LineChart data={ftnChartData}>
                          <CartesianGrid strokeDasharray='3 3' stroke='#30363d' />
                          <XAxis dataKey='time' stroke='#8b949e' tick={{ fontSize: 10 }} hide={true} />
                          <YAxis stroke='#8b949e' tick={{ fontSize: 10 }} width={40} />
                          <Tooltip contentStyle={{ backgroundColor: '#161b22', borderColor: '#30363d' }} itemStyle={{ color: '#c9d1d9' }} />
                          <Legend wrapperStyle={{ fontSize: '11px' }} />
                          <Line name='Cat 1' type='monotone' dataKey='FTN_Category 1' stroke='#d2a8ff' strokeWidth={2} strokeDasharray='3 3' dot={false} connectNulls />
                          <Line name='Cat 2' type='monotone' dataKey='FTN_Category 2' stroke='#79c0ff' strokeWidth={2} strokeDasharray='3 3' dot={false} connectNulls />
                          <Line name='Cat 3' type='monotone' dataKey='FTN_Category 3' stroke='#56d364' strokeWidth={2} strokeDasharray='3 3' dot={false} connectNulls />
                          <Line name='Cat 4' type='monotone' dataKey='FTN_Category 4' stroke='#ffa657' strokeWidth={2} strokeDasharray='3 3' dot={false} connectNulls />
                        </LineChart>
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