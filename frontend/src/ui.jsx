// Small shared pieces for the Overview and Teams views.

// Lowest price in any stored shape: number, {min,max,count}, or {block: price}.
export function minPrice(value) {
  if (typeof value === 'number') return value > 0 ? value : null
  if (value && typeof value === 'object') {
    if ('min' in value) return minPrice(value.min)
    const found = Object.values(value).map(minPrice).filter((p) => p !== null)
    return found.length ? Math.min(...found) : null
  }
  return null
}

// Highest price, same shapes.
export function maxPrice(value) {
  if (typeof value === 'number') return value > 0 ? value : null
  if (value && typeof value === 'object') {
    if ('max' in value || 'min' in value) return maxPrice(value.max ?? value.min)
    const found = Object.values(value).map(maxPrice).filter((p) => p !== null)
    return found.length ? Math.max(...found) : null
  }
  return null
}

export function formatMoney(value, currency = 'USD', locale = 'en-GB', digits = 0) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'currency', currency, maximumFractionDigits: digits, minimumFractionDigits: digits,
  }).format(value)
}

// 'DD/MM/YY' (scraper format) or ISO 'YYYY-MM-DD' -> Date
export function parseDate(s) {
  if (!s) return null
  let m = /^(\d{1,2})\/(\d{1,2})\/(\d{2})$/.exec(s)
  if (m) return new Date(2000 + Number(m[3]), Number(m[2]) - 1, Number(m[1]))
  m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s)
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return null
}

export function daysUntil(date) {
  if (!date) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((date - today) / 86400000)
}

// Ticket-stub date block: the one loud element on the board.
export function DateStub({ date, locale, tbc }) {
  if (!date) {
    return <div className="stub stub-tbc"><span className="stub-month">{tbc}</span></div>
  }
  return (
    <div className="stub">
      <span className="stub-day">{date.getDate()}</span>
      <span className="stub-month">{date.toLocaleDateString(locale, { month: 'short' })}</span>
    </div>
  )
}

export function Change({ pct }) {
  if (pct === null || pct === undefined) return <span className="change flat">—</span>
  // For a buyer, a falling price is the good news.
  const cls = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat'
  const arrow = pct > 0 ? '▲' : pct < 0 ? '▼' : ''
  return (
    <span className={`change ${cls}`} dir="ltr">
      {arrow} {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

// Covers the whole history, so it stays neutral; the change column carries up/down colour.
export function Sparkline({ points, width = 112, height = 32 }) {
  if (!points || points.length < 2) return <svg width={width} height={height} aria-hidden="true" />
  const min = Math.min(...points)
  const range = Math.max(...points) - min || 1
  const step = width / (points.length - 1)
  const d = points
    .map((p, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)},${(height - 3 - ((p - min) / range) * (height - 6)).toFixed(1)}`)
    .join(' ')
  return (
    <svg width={width} height={height} className="spark" aria-hidden="true">
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
