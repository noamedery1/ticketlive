import { useState } from 'react'
import Overview from './Overview'
import TeamView from './TeamView'
import { LangProvider, useLang } from './i18n'
import './App.css'

function Shell() {
  const { t, lang, setLang } = useLang()
  const [view, setView] = useState('overview')
  const [target, setTarget] = useState(null) // game opened from the overview

  const tabs = [['overview', t('overview')], ['teams', t('teams')]]

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <svg width="26" height="18" viewBox="0 0 26 18" aria-hidden="true">
            <path d="M2 1h22a1 1 0 0 1 1 1v4a3 3 0 0 0 0 6v4a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-4a3 3 0 0 0 0-6V2a1 1 0 0 1 1-1z" fill="var(--stub)" />
            <path d="M17 3v12" stroke="var(--stub-ink)" strokeWidth="1.4" strokeDasharray="2 2" />
          </svg>
          <span>TicketLive</span>
        </div>
        <nav className="tabs">
          {tabs.map(([key, label]) => (
            <button key={key} className={view === key ? 'tab on' : 'tab'} aria-current={view === key ? 'page' : undefined}
              onClick={() => { setView(key); if (key === 'teams') setTarget(null) }}>
              {label}
            </button>
          ))}
        </nav>
        <button className="lang-btn" onClick={() => setLang(lang === 'he' ? 'en' : 'he')}>{t('switchLang')}</button>
      </header>

      <main className="main">
        {view === 'overview' && <Overview onOpenGame={(teamKey, url) => { setTarget({ teamKey, url }); setView('teams') }} />}
        {view === 'teams' && <TeamView key={target ? `${target.teamKey}|${target.url}` : 'teams'} target={target} />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <LangProvider>
      <Shell />
    </LangProvider>
  )
}
