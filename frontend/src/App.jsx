import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import TeamView from './TeamView'
import TicketOffersManager from './TicketOffersManager'
import './App.css'

// Use local backend for development, empty for production (same origin)
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
console.log('API_URL:', API_URL, 'DEV mode:', import.meta.env.DEV)

function App() {
  const [view, setView] = useState('original') // 'original' or 'teams'
  const [matches, setMatches] = useState([])
  const [selectedMatch, setSelectedMatch] = useState(null)
  const [history, setHistory] = useState(null)
  const [timeRange, setTimeRange] = useState('24h')
  // Replace simple selectedDate with range
  const [dateRange, setDateRange] = useState({ start: null, end: null })
  const [dateFilterOpen, setDateFilterOpen] = useState(false)

  // Close date dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const dropdown = document.getElementById('app-date-dropdown-container')
      if (dropdown && !dropdown.contains(event.target)) {
        setDateFilterOpen(false)
      }
    }
    if (dateFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [dateFilterOpen])


  useEffect(() => {
    fetchMatches()
    // const interval = setInterval(fetchMatches, 120000)
    // return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedMatch) {
      fetchHistory(selectedMatch.match_url)
      // const historyInterval = setInterval(() => {
      //   fetchHistory(selectedMatch.match_url)
      // }, 120000)
      // return () => clearInterval(historyInterval)
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
    let rangeStart = 0
    let rangeEnd = Infinity

    if (dateRange.start || dateRange.end) {
      // Range filtering
      if (dateRange.start) {
        const s = new Date(dateRange.start)
        s.setHours(0, 0, 0, 0)
        rangeStart = s.getTime()
      }
      if (dateRange.end) {
        const e = new Date(dateRange.end)
        e.setHours(23, 59, 59, 999)
        rangeEnd = e.getTime()
      }
    } else {
      // Preset filtering
      cutoff = timeRange === '24h' ? now - 24 * 3600 * 1000 :
        timeRange === '7d' ? now - 7 * 24 * 3600 * 1000 : 0
      rangeStart = cutoff
    }

    const merged = {}
    const sourceKey = sourcePrefix === 'Via_' ? 'viagogo' : 'ftn'
    if (history[sourceKey] && history[sourceKey].data) {
      Object.keys(history[sourceKey].data).forEach(cat => {
        history[sourceKey].data[cat].forEach(pt => {
          const date = new Date(pt.timestamp)
          const ts = date.getTime()
          if (ts >= rangeStart && ts <= rangeEnd) {
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


  const Navigation = () => (
    <div style={{ display: 'flex', gap: '8px' }}>
      <button
        onClick={() => setView('original')}
        style={{
          padding: '6px 12px',
          borderRadius: '6px',
          border: view === 'original' ? '1px solid #58a6ff' : '1px solid #30363d',
          background: view === 'original' ? '#1f6feb' : '#21262d',
          color: 'white',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: '500'
        }}
      >
        🌍 World Cup
      </button>
      <button
        onClick={() => setView('teams')}
        style={{
          padding: '6px 12px',
          borderRadius: '6px',
          border: view === 'teams' ? '1px solid #58a6ff' : '1px solid #30363d',
          background: view === 'teams' ? '#1f6feb' : '#21262d',
          color: 'white',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: '500'
        }}
      >
        🏟️ Teams
      </button>
      <button
        onClick={() => setView('tickets')}
        style={{
          padding: '6px 12px',
          borderRadius: '6px',
          border: view === 'tickets' ? '1px solid #58a6ff' : '1px solid #30363d',
          background: view === 'tickets' ? '#1f6feb' : '#21262d',
          color: 'white',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: '500'
        }}
      >
        🎫 Tickets
      </button>
    </div>
  )

  // Render TeamView if selected
  if (view === 'teams') {
    return (
      <div className="app-container">
        <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 20px', borderBottom: '1px solid #30363d', background: '#161b22', flexShrink: 0 }}>
          <h1 style={{ margin: 0, fontSize: '1.2rem' }}>Team Ticket Prices</h1>
          <Navigation />
        </div>
        <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
          <TeamView />
        </div>
      </div>
    )
  }

  // Render TicketOffersManager if selected
  if (view === 'tickets') {
    return (
      <div className="app-container">
        <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 20px', borderBottom: '1px solid #30363d', background: '#161b22', flexShrink: 0 }}>
          <h1 style={{ margin: 0, fontSize: '1.2rem' }}>Ticket Offers Manager</h1>
          <Navigation />
        </div>
        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <TicketOffersManager />
        </div>
      </div>
    )
  }

  return (
    <div className='dashboard'>
      <div className='sidebar' style={{ width: sidebarWidth }}>
        <div className='logo' style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
          <div style={{ fontWeight: 'bold', fontSize: '1.1rem', color: '#58a6ff' }}>ViagogoMonitor</div>
        </div>
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                <h1 style={{ margin: 0 }}>{selectedMatch.match_name}</h1>
                <span className='last-updated'>Auto-refresh: Disabled</span>
              </div>

              <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                {/* Date Filter Dropdown */}
                <div id="app-date-dropdown-container" style={{ position: 'relative' }}>
                  <button
                    onClick={() => setDateFilterOpen(!dateFilterOpen)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: '1px solid #30363d',
                      background: '#0d1117',
                      color: '#c9d1d9',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      minWidth: '200px',
                      justifyContent: 'space-between',
                      transition: 'border-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = '#58a6ff'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>📅</span>
                      <span>
                        {(!dateRange.start && !dateRange.end) ? 'All Time' :
                          (dateRange.start && dateRange.end) ? `${new Date(dateRange.start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} - ${new Date(dateRange.end).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` :
                            dateRange.start ? `From ${new Date(dateRange.start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` :
                              `Until ${new Date(dateRange.end).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
                        }
                      </span>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: '#6e7681' }}>▼</span>
                  </button>

                  {dateFilterOpen && (
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      right: 0,
                      marginTop: '4px',
                      background: '#161b22',
                      border: '1px solid #30363d',
                      borderRadius: '6px',
                      padding: '12px',
                      zIndex: 1000,
                      minWidth: '280px',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
                    }}>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                        <button
                          onClick={() => {
                            setDateRange({ start: null, end: null })
                            setTimeRange('all')
                            setDateFilterOpen(false)
                          }}
                          style={{
                            flex: 1,
                            padding: '6px',
                            background: (!dateRange.start && !dateRange.end) ? '#1f6feb' : '#21262d',
                            color: (!dateRange.start && !dateRange.end) ? '#fff' : '#c9d1d9',
                            border: '1px solid #30363d',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.8rem'
                          }}
                        >
                          All Time
                        </button>
                        <button
                          onClick={() => {
                            const end = new Date().toISOString().split('T')[0]
                            const start = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0]
                            setDateRange({ start, end })
                            setTimeRange('7d')
                            setDateFilterOpen(false)
                          }}
                          style={{
                            flex: 1,
                            padding: '6px',
                            background: '#21262d',
                            color: '#c9d1d9',
                            border: '1px solid #30363d',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.8rem'
                          }}
                        >
                          Last 7 Days
                        </button>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '40px', fontSize: '0.8rem', color: '#8b949e' }}>From:</span>
                          <input
                            type="date"
                            value={dateRange.start || ''}
                            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                            style={{
                              flex: 1,
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #30363d',
                              background: '#0d1117',
                              color: '#c9d1d9',
                              fontSize: '0.8rem'
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '40px', fontSize: '0.8rem', color: '#8b949e' }}>To:</span>
                          <input
                            type="date"
                            value={dateRange.end || ''}
                            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                            style={{
                              flex: 1,
                              padding: '4px 8px',
                              borderRadius: '4px',
                              border: '1px solid #30363d',
                              background: '#0d1117',
                              color: '#c9d1d9',
                              fontSize: '0.8rem'
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <Navigation />
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
                              <stop offset='0%' stopColor='#d2a8ff' stopOpacity={0.4} />
                              <stop offset='50%' stopColor='#d2a8ff' stopOpacity={0.15} />
                              <stop offset='100%' stopColor='#d2a8ff' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradVia2' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#79c0ff' stopOpacity={0.4} />
                              <stop offset='50%' stopColor='#79c0ff' stopOpacity={0.15} />
                              <stop offset='100%' stopColor='#79c0ff' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradVia3' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#56d364' stopOpacity={0.4} />
                              <stop offset='50%' stopColor='#56d364' stopOpacity={0.15} />
                              <stop offset='100%' stopColor='#56d364' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradVia4' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#ffa657' stopOpacity={0.4} />
                              <stop offset='50%' stopColor='#ffa657' stopOpacity={0.15} />
                              <stop offset='100%' stopColor='#ffa657' stopOpacity={0} />
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
                            formatter={(value, name) => [`$${value?.toLocaleString() || '0'}`, name]}
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
                              <stop offset='0%' stopColor='#d2a8ff' stopOpacity={0.35} />
                              <stop offset='50%' stopColor='#d2a8ff' stopOpacity={0.12} />
                              <stop offset='100%' stopColor='#d2a8ff' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradFtn2' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#79c0ff' stopOpacity={0.35} />
                              <stop offset='50%' stopColor='#79c0ff' stopOpacity={0.12} />
                              <stop offset='100%' stopColor='#79c0ff' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradFtn3' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#56d364' stopOpacity={0.35} />
                              <stop offset='50%' stopColor='#56d364' stopOpacity={0.12} />
                              <stop offset='100%' stopColor='#56d364' stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id='gradFtn4' x1='0' y1='0' x2='0' y2='1'>
                              <stop offset='0%' stopColor='#ffa657' stopOpacity={0.35} />
                              <stop offset='50%' stopColor='#ffa657' stopOpacity={0.12} />
                              <stop offset='100%' stopColor='#ffa657' stopOpacity={0} />
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
                            formatter={(value, name) => [`$${value?.toLocaleString() || '0'}`, name]}
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