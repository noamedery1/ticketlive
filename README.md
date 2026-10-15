# ticketlive

Tracks football ticket prices on the secondary market over time. Scrapers
collect listing prices per match, the API serves the history, and a React
dashboard charts it.

## How it works

```
scraper_ftn_teams.py  ──>  ftn_teams_data.json  ──>  FastAPI  ──>  React dashboard
  (Selenium, FTN)            (price history)      (RUN_SERVER_ONLY.py)
```

- **Scrapers** drive Chrome via Selenium against FootballTicketNet. Every team
  in `teams_list.json` is picked up automatically — currently Arsenal (GBP),
  FC Barcelona (EUR), Real Madrid (EUR) and the Champions League.
  `auto_scraper_teams.py` runs them on a schedule and pushes the data to git.
- **Server:** FastAPI + uvicorn (`RUN_SERVER_ONLY.py`), deployed to Railway.
  Serves the API and the built frontend; runs no scrapers.
- **Frontend:** React + Recharts (`frontend/`), English and Hebrew.
  - *Overview* — every upcoming game, cheapest ticket, 7-day change.
  - *Teams* — per-game price history by category.

## Running

Server (reads existing data, scrapes nothing):

```bash
pip install -r requirements_server.txt
python RUN_SERVER_ONLY.py
```

Frontend dev server (proxies the API to localhost:8000):

```bash
cd frontend && npm install && npm run dev
```

Scrapers: see [`SCRAPER_SETUP.md`](SCRAPER_SETUP.md).

Smoke test: `python test_server.py`

## Secrets

No configuration is needed. `.env` is gitignored and must stay that way. An earlier commit tracked it
and exposed a live key; that key has been revoked. If you leak another one,
revoke it rather than only deleting the file — the value stays in history.

## Guides

- [`ADD_TEAM_GUIDE.md`](ADD_TEAM_GUIDE.md) — adding a team to `teams_list.json`
- [`TEAMS_SCRAPER_GUIDE.md`](TEAMS_SCRAPER_GUIDE.md) — how the teams scraper works
- [`SCRAPER_SETUP.md`](SCRAPER_SETUP.md) — setting up the scraper machine

## Scraping responsibly

The scrapers hit third-party sites. Keep the polling interval conservative,
respect each site's terms of service, and don't run this at a rate that
burdens the target. It is a personal price-tracking tool, not a load test.
