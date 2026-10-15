# Scraper machine setup

The scraper runs on a Windows PC (Windows 7 works), scrapes FootballTicketNet,
commits `ftn_teams_data.json` and pushes it. Railway redeploys the site on every push.

## What the machine needs

Clone the whole repo — the scraper commits and pushes from it. Of the repo, the
scraper only uses:

| File | Role |
|---|---|
| `SETUP_SCRAPER.bat` | One-time setup + first run |
| `RUN_ALL_TEAMS_ONCE.bat` | Entry point for Task Scheduler (one cycle, logs to `scraper.log`) |
| `RUN_ALL_TEAMS.bat` | Same, as a loop in a console window (every 3 h) |
| `auto_scraper_teams.py` | git pull → scrape each team → one commit → push |
| `scraper_ftn_teams.py` | Scrapes one team with Chrome: team page → upcoming home games → each game's category prices |
| `teams_list.json` | Which teams to scrape. `team_url` = the team page on FTN, `currency` = GBP/EUR/USD, `"all_games": true` for a tournament page (all games, not only home games) |
| `ftn_teams_data.json` | The price history (state) |
| `download_chromedriver.py`, `DOWNLOAD_CHROMEDRIVER.bat` | Fetch a chromedriver matching Chrome |
| `requirements_win7.txt` | Python packages |

## Install (Windows 7)

1. Install, in this order:
   - **Python 3.8.10** (last version for Windows 7) — tick "Add Python to PATH" and "py launcher".
   - **Chrome 109** (last version for Windows 7) if it is not there already.
   - **Git for Windows 2.46.x** (last line that supports Windows 7).
2. Extract `ticketlive-scraper.zip` to `C:\ticketlive`.
3. Double-click `C:\ticketlive\SETUP_SCRAPER.bat`. It links the folder to GitHub,
   creates `C:\PythonEnvs\ticketlive`, installs packages, downloads ChromeDriver,
   schedules a run every 3 hours and starts the first run.
4. On the first push Git asks for GitHub credentials: your username, and as password a
   fine-grained token (github.com → Settings → Developer settings → Fine-grained tokens,
   repository `ticketlive`, permission *Contents: Read and write*).

## Schedule it

`SETUP_SCRAPER.bat` creates the task "TicketLive Scraper" (every 3 hours, runs
`RUN_ALL_TEAMS_ONCE.bat`). Chrome needs a desktop session, so the PC must stay logged
in: turn on auto-logon and turn off sleep.

## How a run avoids the bot check

FootballTicketNet sometimes shows a Cloudflare "verify you are human" page after many game
pages in a row. It clears by itself after a few minutes. The scraper never clicks it; instead:

1. **Fewer page loads.** The team page lists every game with its cheapest price. A game's own
   page (all categories) is loaded only if the game is new, its cheapest price changed, or its
   categories are older than 12 hours (`DETAIL_MAX_AGE_HOURS`). Most runs load only a few pages.
2. **No duplicates.** A game already scraped for another team in the last 2 hours is reused.
3. **Most valuable first.** New and changed games are loaded before routine refreshes.
4. **Waits out a block.** On the check page it waits 4 minutes, retries, then 8 minutes
   (`BACKOFF_MINUTES`), then stops loading game pages for that run.
5. **Never loses a run.** Games it could not open still get their cheapest price from the
   team page (shown as the "Cheapest (team page)" line on the chart).

## When something breaks

- `scraper.log` shows each run. Exit code 1 = at least one team failed.
- A team with zero games found is treated as a failure (usually a block page) and its
  old data is kept.
- If `ftn_teams_data.json` is unreadable the scraper stops instead of overwriting it:
  `git checkout ftn_teams_data.json` to restore the last pushed version.
- If git pull fails (conflict, dirty tree), the cycle stops and says so.
  `git status` on the machine, fix, rerun.
- Chrome updated and the driver broke: rerun `DOWNLOAD_CHROMEDRIVER.bat`.
  The `.bat` files set `CHROME_MAJOR=109`; change it if the machine runs another Chrome.
