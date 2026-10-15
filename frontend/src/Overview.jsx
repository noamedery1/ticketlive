import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { useLang } from './i18n'
import { Change, DateStub, Sparkline, daysUntil, formatMoney, parseDate } from './ui'

export default function Overview({ onOpenGame }) {
  const { t, locale } = useLang()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(false)
  const [team, setTeam] = useState('all')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('date')

  useEffect(() => {
    axios.get('/teams/overview')
      .then((res) => setRows(res.data || []))
      .catch(() => setError(true))
  }, [])

  const teams = useMemo(() => {
    const seen = new Map()
    for (const r of rows || []) seen.set(r.team_key, { key: r.team_key, name: r.team_name, count: (seen.get(r.team_key)?.count || 0) + 1 })
    return [...seen.values()]
  }, [rows])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = (rows || []).filter((r) =>
      (team === 'all' || r.team_key === team) &&
      (!q || `${r.match_name} ${r.team_name}`.toLowerCase().includes(q)))
    const val = (r, k, empty) => r.summary?.[k] ?? empty
    const sorters = {
      date: () => 0, // server already sorts by date
      cheapest: (a, b) => val(a, 'current', Infinity) - val(b, 'current', Infinity),
      rising: (a, b) => val(b, 'pct', -Infinity) - val(a, 'pct', -Infinity),
      falling: (a, b) => val(a, 'pct', Infinity) - val(b, 'pct', Infinity),
    }
    return [...list].sort(sorters[sort])
  }, [rows, team, query, sort])

  if (error) return <div className="empty">{t('loadError')}</div>
  if (!rows) return <div className="empty">{t('loading')}</div>
  if (!rows.length) return <div className="empty">{t('noGames')}</div>

  return (
    <div className="page">
      <div className="toolbar">
        <div className="chips" role="group" aria-label={t('team')}>
          <button className={team === 'all' ? 'chip on' : 'chip'} onClick={() => setTeam('all')}>
            {t('allTeams')} <span className="count">{rows.length}</span>
          </button>
          {teams.map((tm) => (
            <button key={tm.key} className={team === tm.key ? 'chip on' : 'chip'} onClick={() => setTeam(tm.key)}>
              {tm.name} <span className="count">{tm.count}</span>
            </button>
          ))}
        </div>
        <div className="toolbar-end">
          <input type="search" className="field" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder={t('searchGames')} aria-label={t('searchGames')} />
          <select className="field" value={sort} onChange={(e) => setSort(e.target.value)} aria-label={t('sortBy')}>
            <option value="date">{t('sortDate')}</option>
            <option value="cheapest">{t('sortCheapest')}</option>
            <option value="rising">{t('sortRising')}</option>
            <option value="falling">{t('sortFalling')}</option>
          </select>
        </div>
      </div>

      <div className="board">
        <div className="board-head" aria-hidden="true">
          <span className="col-stub" />
          <span>{t('colMatch')}</span>
          <span className="num">{t('colCheapest')}</span>
          <span className="num">{t('colChange')}</span>
          <span className="col-trend">{t('colTrend')}</span>
        </div>
        {visible.length === 0 && <div className="empty">{t('noMatches')}</div>}
        {visible.map((r) => {
          const date = parseDate(r.date)
          const days = daysUntil(date)
          const s = r.summary
          return (
            <button key={`${r.team_key}|${r.url}`} className="board-row" onClick={() => onOpenGame(r.team_key, r.url)}>
              <span className="col-stub"><DateStub date={date} locale={locale} tbc={t('dateTbc')} /></span>
              <span className="match">
                <span className="match-name">{r.match_name}</span>
                <span className="match-meta">{r.team_name}{days !== null && days >= 0 ? ` · ${t('daysLeft', days)}` : ''}</span>
              </span>
              <span className="num price">
                {s ? formatMoney(s.current, r.currency, locale) : <span className="muted">{t('noPrice')}</span>}
              </span>
              <span className="num"><Change pct={s?.pct} /></span>
              <span className="col-trend"><Sparkline points={s?.spark} /></span>
            </button>
          )
        })}
      </div>
      <p className="footnote">{t('upcoming', visible.length)} · {t('cheaperHint')}</p>
    </div>
  )
}
