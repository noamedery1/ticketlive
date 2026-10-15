import { createContext, useContext, useEffect, useState } from 'react'

const STRINGS = {
  en: {
    overview: 'Overview',
    teams: 'Teams',
    offers: 'Offers',
    switchLang: 'עברית',
    allTeams: 'All teams',
    searchGames: 'Search games',
    sortBy: 'Sort by',
    sortDate: 'Match date',
    sortCheapest: 'Cheapest first',
    sortRising: 'Biggest rise',
    sortFalling: 'Biggest drop',
    colMatch: 'Match',
    colCheapest: 'Cheapest ticket',
    colChange: '7-day change',
    colTrend: 'Trend',
    upcoming: (n) => `${n} upcoming games`,
    cheaperHint: 'Green = cheaper than 7 days ago',
    noPrice: 'No prices yet',
    loading: 'Loading…',
    loadError: 'Could not reach the server. Check that it is running and refresh.',
    noGames: 'No upcoming games. Run the team scraper to collect new fixtures.',
    noMatches: 'No games match this search.',
    daysLeft: (n) => (n === 0 ? 'Today' : n === 1 ? 'Tomorrow' : `In ${n} days`),
    dateTbc: 'Date TBC',
    team: 'Team',
    games: 'Games',
    cheapestNow: 'Cheapest now',
    change7d: 'Change, 7 days',
    categories: 'Categories',
    lastChecked: 'Last checked',
    priceHistory: 'Lowest price per category, by day',
    allTime: 'All time',
    last7: 'Last 7 days',
    last30: 'Last 30 days',
    from: 'From',
    to: 'To',
    allCategories: 'All categories',
    nCategories: (n, total) => `${n} of ${total} categories`,
    selectAll: 'Select all',
    clear: 'Clear',
    noHistory: 'No price history in this range.',
    categoryTable: 'Current prices by category',
    category: 'Category',
    priceRange: 'Price range',
    listings: 'Listings',
    blocks: 'Blocks',
    block: 'Block',
    close: 'Close',
    selectGame: 'Pick a game to see its prices.',
    viewOnSite: 'Open on FootballTicketNet',
  },
  he: {
    overview: 'סקירה',
    teams: 'קבוצות',
    offers: 'הצעות',
    switchLang: 'English',
    allTeams: 'כל הקבוצות',
    searchGames: 'חיפוש משחק',
    sortBy: 'מיון',
    sortDate: 'תאריך משחק',
    sortCheapest: 'הזול ביותר',
    sortRising: 'עלייה גדולה',
    sortFalling: 'ירידה גדולה',
    colMatch: 'משחק',
    colCheapest: 'הכרטיס הזול',
    colChange: 'שינוי ב-7 ימים',
    colTrend: 'מגמה',
    upcoming: (n) => `${n} משחקים קרובים`,
    cheaperHint: 'ירוק = זול יותר מלפני 7 ימים',
    noPrice: 'אין מחירים עדיין',
    loading: 'טוען…',
    loadError: 'אין חיבור לשרת. ודאו שהוא רץ ורעננו את הדף.',
    noGames: 'אין משחקים קרובים. הריצו את סורק הקבוצות כדי לאסוף משחקים חדשים.',
    noMatches: 'אין משחקים שמתאימים לחיפוש.',
    daysLeft: (n) => (n === 0 ? 'היום' : n === 1 ? 'מחר' : `בעוד ${n} ימים`),
    dateTbc: 'תאריך ייקבע',
    team: 'קבוצה',
    games: 'משחקים',
    cheapestNow: 'הזול כרגע',
    change7d: 'שינוי, 7 ימים',
    categories: 'קטגוריות',
    lastChecked: 'נבדק לאחרונה',
    priceHistory: 'המחיר הנמוך לכל קטגוריה, לפי יום',
    allTime: 'כל הזמן',
    last7: '7 ימים אחרונים',
    last30: '30 ימים אחרונים',
    from: 'מ-',
    to: 'עד',
    allCategories: 'כל הקטגוריות',
    nCategories: (n, total) => `${n} מתוך ${total} קטגוריות`,
    selectAll: 'בחר הכל',
    clear: 'נקה',
    noHistory: 'אין היסטוריית מחירים בטווח הזה.',
    categoryTable: 'מחירים נוכחיים לפי קטגוריה',
    category: 'קטגוריה',
    priceRange: 'טווח מחירים',
    listings: 'מודעות',
    blocks: 'בלוקים',
    block: 'בלוק',
    close: 'סגור',
    selectGame: 'בחרו משחק כדי לראות מחירים.',
    viewOnSite: 'פתח ב-FootballTicketNet',
  },
}

const LangContext = createContext(null)

function initialLang() {
  try {
    const saved = localStorage.getItem('lang')
    if (saved === 'en' || saved === 'he') return saved
  } catch { /* storage blocked */ }
  return navigator.language?.startsWith('he') ? 'he' : 'en'
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(initialLang)

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'he' ? 'rtl' : 'ltr'
    try { localStorage.setItem('lang', lang) } catch { /* storage blocked */ }
  }, [lang])

  const t = (key, ...args) => {
    const v = STRINGS[lang][key] ?? STRINGS.en[key] ?? key
    return typeof v === 'function' ? v(...args) : v
  }
  const locale = lang === 'he' ? 'he-IL' : 'en-GB'
  return (
    <LangContext.Provider value={{ lang, setLang, t, locale }}>
      {children}
    </LangContext.Provider>
  )
}

export const useLang = () => useContext(LangContext)
