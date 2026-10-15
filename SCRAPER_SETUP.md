# Scraper machine setup

The scraper runs on a Windows PC (Windows 7 works), scrapes FootballTicketNet,
commits `ftn_teams_data.json` and pushes it. Railway redeploys the site on every push.

## What the machine needs

Clone the whole repo — the scraper commits and pushes from it. Of the repo, the
scraper only uses:

| File | Role |
|---|---|
| `RUN_ALL_TEAMS_ONCE.bat` | Entry point for Task Scheduler (one cycle, logs to `scraper.log`) |
| `RUN_ALL_TEAMS.bat` | Same, as a loop in a console window (every 3 h) |
| `auto_scraper_teams.py` | git pull → scrape each team → one commit → push |
| `scraper_ftn_teams.py` | Scrapes one team with Chrome |
| `teams_list.json` | Which teams to scrape — see `ADD_TEAM_GUIDE.md` |
| `ftn_teams_data.json` | The price history (state) |
| `download_chromedriver.py`, `DOWNLOAD_CHROMEDRIVER.bat` | Fetch a chromedriver matching Chrome |
| `requirements_win7.txt` | Python packages |

## Install (Windows 7)

1. **Python 3.8.10** (last version that installs on Windows 7), "Add to PATH" ticked.
2. **Chrome 109** (last version for Windows 7). Turn off auto-update.
3. **Git for Windows**, then clone and give it push access:
   ```bat
   git clone https://github.com/noamedery1/ticketlive.git C:\ticketlive
   ```
   Use a GitHub fine-grained token with *Contents: read and write* on this repo only,
   stored by Git Credential Manager on the first push.
4. Virtual env + packages:
   ```bat
   py -3.8 -m venv C:\PythonEnvs\ticketlive
   C:\PythonEnvs\ticketlive\Scripts\pip install -r C:\ticketlive\requirements_win7.txt
   ```
5. Chromedriver 109 into `C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe`:
   run `DOWNLOAD_CHROMEDRIVER.bat`.
6. Test once by hand: double-click `RUN_ALL_TEAMS_ONCE.bat`, then read `scraper.log`.

## Schedule it

Task Scheduler → Create Task:
- Trigger: daily, repeat every 3 hours.
- Action: `C:\ticketlive\RUN_ALL_TEAMS_ONCE.bat`, start in `C:\ticketlive`.
- "Run whether user is logged on or not" is **not** recommended: Chrome needs a desktop
  session. Use auto-logon and "Run only when user is logged on".
- Settings: "Stop the task if it runs longer than 4 hours".

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
