# ticketlive

Tracks football ticket prices on the secondary market over time. Scrapers
collect listing prices per match, the API serves the history, and a React
dashboard charts it.

## How it works

```
auto_scraper*.py  ──>  prices.json.gz / prices_ftn.json.gz  ──>  FastAPI  ──>  React dashboard
   (Selenium)              (price history)                    (RUN_SERVER_ONLY.py)
```

- **Scrapers** drive headless Chrome via Selenium. `scrape_game_prices()` is
  shared, so a team added to `teams_list.json` is picked up automatically —
  currently Arsenal (GBP), FC Barcelona (EUR) and Real Madrid (EUR).
  `auto_scraper_worldcup.py` handles World Cup fixtures.
- **Price history** lives in gzipped JSON (`prices.json.gz`,
  `prices_ftn.json.gz`) to stay under GitHub's file size limits. The
  uncompressed `prices.json` is gitignored.
- **Server:** FastAPI + uvicorn (`RUN_SERVER_ONLY.py`), deployed to Railway.
  It serves the API and the built frontend, and runs no scrapers.
- **Frontend:** React + axios + Recharts (`frontend/`).

## Running

Everything (scrapers + server):

```bash
python RUN_EVERYTHING.py
```

Server only — reads existing price history, scrapes nothing:

```bash
pip install -r requirements_server.txt
python RUN_SERVER_ONLY.py
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

## Configuration

```bash
cp .env.example .env
```

Then set `GEMINI_API_KEY` — get one at
[Google AI Studio](https://aistudio.google.com/apikey).

`.env` is gitignored and must stay that way. An earlier commit tracked it
and exposed a live key; that key has been revoked. If you leak another one,
revoke it rather than only deleting the file — the value stays in history.

## Chromedriver

The scrapers need a Chromedriver matching your installed Chrome:

```bash
python download_chromedriver.py
```

If it breaks after a Chrome update, see `FIX_CHROMEDRIVER.md` and the
`FIX_CHROMEDRIVER*.bat` helpers.

## Guides

- [`ADD_TEAM_GUIDE.md`](ADD_TEAM_GUIDE.md) — adding a team to `teams_list.json`
- [`TEAMS_SCRAPER_GUIDE.md`](TEAMS_SCRAPER_GUIDE.md) — how the teams scraper works
- [`TICKET_OFFERS_MANAGER.md`](TICKET_OFFERS_MANAGER.md) — offers management
- [`DEPLOYMENT_READY.md`](DEPLOYMENT_READY.md) — deployment checklist
- [`INSTALL_WINDOWS7.md`](INSTALL_WINDOWS7.md), [`MANUAL_PIP_INSTALL.md`](MANUAL_PIP_INSTALL.md) — install notes

## Scraping responsibly

The scrapers hit third-party sites. Keep the polling interval conservative,
respect each site's terms of service, and don't run this at a rate that
burdens the target. It is a personal price-tracking tool, not a load test.
