import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useLang } from './i18n'
import { Change, DateStub, formatMoney, maxPrice, minPrice, parseDate } from './ui'

const SERIES_COLORS = ['#5aa9e6', '#f2b544', '#3dbe8b', '#c792ea', '#f07167', '#7fd1c7', '#e8a87c', '#9aa8ff', '#d4e157', '#f48fb1', '#a1887f', '#90a4ae']
const dayKey = (ts) => ts.slice(0, 10)

// Listing count for one category in latest_prices, any stored shape.
function countListings(value) {
  if (typeof value === 'number') return 1
  if (value && typeof value === 'object') {
    if ('min' in value) return value.count || 1
    return Object.values(value).reduce((n, v) => n + countListings(v), 0)
  }
  return 0
}

export default function TeamView({ target }) {
  const { t, locale } = useLang()
  const [teams, setTeams] = useState([])
  const [teamKey, setTeamKey] = useState(target?.teamKey || null)
  const [games, setGames] = useState([])
  const [gameIndex, setGameIndex] = useState(null)
  const [detail, setDetail] = useState(null)
  const [range, setRange] = useState({ preset: 'all', start: '', end: '' })
  const [hidden, setHidden] = useState([]) // categories toggled off
  const [modal, setModal] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    axios.get('/teams').then((res) => {
      setTeams(res.data)
      setTeamKey((k) => k || res.data[0]?.key || null)
    }).catch(() => setError(true))
  }, [])

  useEffect(() => {
    if (!teamKey) return
    setGames([])
    setGameIndex(null)
    axios.get(`/teams/${encodeURIComponent(teamKey)}`).then((res) => {
      setGames(res.data)
      const wanted = target?.teamKey === teamKey ? res.data.findIndex((g) => g.url === target.url) : -1
      setGameIndex(res.data.length ? Math.max(wanted, 0) : null)
    }).catch(() => setError(true))
  }, [teamKey, target])

  useEffect(() => {
    if (!teamKey || gameIndex === null) return
    setDetail(null)
    setHidden([])
    setRange({ preset: 'all', start: '', end: '' })
    axios.get(`/teams/${encodeURIComponent(teamKey)}/game/${gameIndex}`)
      .then((res) => setDetail(res.data))
      .catch(() => setError(true))
  }, [teamKey, gameIndex])

  const currency = detail?.currency || teams.find((x) => x.key === teamKey)?.currency || 'USD'

  // Daily lowest price per category.
  const { chartData, categories } = useMemo(() => {
    const byDay = {}
    const cats = new Set()
    let start = range.start, end = range.end
    if (range.preset !== 'all' && range.preset !== 'custom') {
      start = new Date(Date.now() - Number(range.preset) * 86400000).toISOString().slice(0, 10)
      end = ''
    }
    for (const snap of detail?.prices || []) {
      const day = dayKey(snap.timestamp || '')
      if (!day || (start && day < start) || (end && day > end)) continue
      for (const [cat, value] of Object.entries(snap.prices || {})) {
        const p = minPrice(value)
        if (p === null) continue
        cats.add(cat)
        byDay[day] ??= { day }
        byDay[day][cat] = Math.min(byDay[day][cat] ?? Infinity, p)
      }
    }
    return { chartData: Object.values(byDay).sort((a, b) => a.day.localeCompare(b.day)), categories: [...cats].sort() }
  }, [detail, range])

  const categoryRows = useMemo(() => Object.entries(detail?.latest_prices || {})
    .map(([category, value]) => ({
      category,
      min: minPrice(value),
      max: maxPrice(value),
      count: countListings(value),
      blocks: value && typeof value === 'object' && !('min' in value)
        ? Object.entries(value).map(([block, v]) => ({ block, min: minPrice(v), max: maxPrice(v), count: countListings(v) }))
          .filter((b) => b.min !== null).sort((a, b) => a.min - b.min)
        : [],
    }))
    .filter((r) => r.min !== null)
    .sort((a, b) => a.min - b.min), [detail])

  const money = (v, digits = 0) => formatMoney(v, currency, locale, digits)
  const fmtDay = (d) => new Date(d).toLocaleDateString(locale, { day: 'numeric', month: 'short' })
  const range2 = (r) => (r.min === r.max ? money(r.min) : `${money(r.min)} – ${money(r.max)}`)

  if (error) return <div className="empty">{t('loadError')}</div>

  return (
    <div className="team-layout">
      <aside className="game-list">
        <label className="field-label" htmlFor="team-select">{t('team')}</label>
        <select id="team-select" className="field" value={teamKey || ''} onChange={(e) => setTeamKey(e.target.value)}>
          {teams.map((tm) => <option key={tm.key} value={tm.key}>{tm.name} ({tm.game_count})</option>)}
        </select>
        <h2 className="list-title">{t('games')}</h2>
        {games.length === 0 && <p className="muted small">{t('noGames')}</p>}
        <ul>
          {games.map((g, i) => (
            <li key={g.url}>
              <button className={i === gameIndex ? 'game on' : 'game'} onClick={() => setGameIndex(i)} aria-current={i === gameIndex}>
                <DateStub date={parseDate(g.date)} locale={locale} tbc={t('dateTbc')} />
                <span className="game-text">
                  <span className="game-name">{g.opponent || g.match_name}</span>
                  <span className="game-price">{g.cheapest ? money(g.cheapest) : t('noPrice')}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="game-detail">
        {!detail?.game ? (
          <div className="empty">{gameIndex === null ? t('selectGame') : t('loading')}</div>
        ) : (
          <>
            <header className="detail-head">
              <div>
                <h1>{detail.game.match_name}</h1>
                <p className="muted">
                  {parseDate(detail.game.date)?.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) || t('dateTbc')}
                  {detail.game.url && <> · <a href={detail.game.url} target="_blank" rel="noopener noreferrer">{t('viewOnSite')}</a></>}
                </p>
              </div>
            </header>

            <dl className="kpis">
              <div><dt>{t('cheapestNow')}</dt><dd className="kpi-main">{money(detail.summary?.current)}</dd></div>
              <div><dt>{t('change7d')}</dt><dd><Change pct={detail.summary?.pct} /></dd></div>
              <div><dt>{t('categories')}</dt><dd>{categoryRows.length}</dd></div>
              <div><dt>{t('lastChecked')}</dt><dd>{detail.game.last_scraped ? new Date(detail.game.last_scraped).toLocaleString(locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'}</dd></div>
            </dl>

            <div className="panel">
              <div className="panel-head">
                <h2>{t('priceHistory')}</h2>
                <div className="segmented" role="group">
                  {[['all', t('allTime')], ['7', t('last7')], ['30', t('last30')]].map(([k, label]) => (
                    <button key={k} className={range.preset === k ? 'on' : ''} onClick={() => setRange({ preset: k, start: '', end: '' })}>{label}</button>
                  ))}
                </div>
                <div className="date-range">
                  <label>{t('from')} <input type="date" className="field" value={range.start} onChange={(e) => setRange({ ...range, preset: 'custom', start: e.target.value })} /></label>
                  <label>{t('to')} <input type="date" className="field" value={range.end} onChange={(e) => setRange({ ...range, preset: 'custom', end: e.target.value })} /></label>
                </div>
              </div>

              {categories.length > 0 && (
                <div className="legend" role="group" aria-label={t('categories')}>
                  {categories.map((c, i) => (
                    <button key={c} className={hidden.includes(c) ? 'legend-item off' : 'legend-item'} aria-pressed={!hidden.includes(c)}
                      onClick={() => setHidden(hidden.includes(c) ? hidden.filter((x) => x !== c) : [...hidden, c])}>
                      <span className="swatch" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />{c}
                    </button>
                  ))}
                  <button className="link-btn" onClick={() => setHidden(hidden.length ? [] : categories)}>
                    {hidden.length ? t('selectAll') : t('clear')}
                  </button>
                </div>
              )}

              {chartData.length === 0 ? (
                <div className="empty small">{t('noHistory')}</div>
              ) : (
                <div className="chart" dir="ltr">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid stroke="var(--line)" strokeDasharray="3 5" vertical={false} />
                      <XAxis dataKey="day" tickFormatter={fmtDay} stroke="var(--faint)" tick={{ fontSize: 12, fill: 'var(--muted)' }} minTickGap={24} />
                      <YAxis tickFormatter={(v) => money(v)} stroke="var(--faint)" tick={{ fontSize: 12, fill: 'var(--muted)' }} width={72} />
                      <Tooltip
                        labelFormatter={fmtDay}
                        formatter={(v, name) => [money(v), name]}
                        contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--line)', borderRadius: 8 }}
                        labelStyle={{ color: 'var(--text-strong)', fontWeight: 600 }}
                        itemStyle={{ padding: 0 }}
                      />
                      {categories.map((c, i) => !hidden.includes(c) && (
                        <Line key={c} dataKey={c} name={c} type="monotone" stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                          strokeWidth={2} dot={chartData.length < 20} connectNulls isAnimationActive={false} />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {categoryRows.length > 0 && (
              <div className="panel">
                <h2>{t('categoryTable')}</h2>
                <table className="data-table">
                  <thead>
                    <tr><th>{t('category')}</th><th className="num">{t('priceRange')}</th><th className="num">{t('listings')}</th></tr>
                  </thead>
                  <tbody>
                    {categoryRows.map((r) => (
                      <tr key={r.category} className={r.blocks.length ? 'clickable' : ''}
                        onClick={() => r.blocks.length && setModal(r)}
                        onKeyDown={(e) => e.key === 'Enter' && r.blocks.length && setModal(r)}
                        tabIndex={r.blocks.length ? 0 : undefined}>
                        <td>{r.category}</td>
                        <td className="num">{range2(r)}</td>
                        <td className="num">{r.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label={modal.category} onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>{modal.category}</h2>
              <button className="icon-btn" onClick={() => setModal(null)} aria-label={t('close')} autoFocus>×</button>
            </div>
            <p className="muted">{range2(modal)} · {modal.count} {t('listings')}</p>
            <table className="data-table">
              <thead><tr><th>{t('block')}</th><th className="num">{t('priceRange')}</th><th className="num">{t('listings')}</th></tr></thead>
              <tbody>
                {modal.blocks.map((b) => (
                  <tr key={b.block}><td>{b.block}</td><td className="num">{range2(b)}</td><td className="num">{b.count}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
