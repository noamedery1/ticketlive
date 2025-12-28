# Unified Teams Scraper

## Overview

The scraper now uses a **single unified system** to scrape all teams. No need for separate batch files per team!

## Quick Start

### 1. Add Teams

Edit `teams_list.json` and add your team:

```json
{
  "teams": [
    {
      "team_key": "arsenal",
      "team_name": "Arsenal",
      "team_url": "https://www.footballticketnet.com/arsenal-football-tickets/filter/home_away/home-matches"
    },
    {
      "team_key": "barcelona",
      "team_name": "FC Barcelona",
      "team_url": "https://www.footballticketnet.com/barcelona-football-tickets/filter/home_away/home-matches"
    }
  ]
}
```

### 2. Run the Scraper

**Windows:**
- `RUN_ALL_TEAMS.bat` - Runs continuously (every 3 hours)
- `RUN_ALL_TEAMS_ONCE.bat` - Runs once and exits

**Command Line:**
```bash
python auto_scraper_teams.py        # Continuous (every 3 hours)
python auto_scraper_teams.py --once # Run once
```

## How It Works

1. **Loads teams** from `teams_list.json` (or discovers from `*_prices.json` files as fallback)
2. **Scrapes each team** one by one sequentially
3. **Saves data** to `{team_key}_prices.json` files
4. **Commits and pushes** to Git (if configured)

## Adding More Teams

Simply add entries to `teams_list.json`. The scraper will automatically:
- Process all teams in the list
- Create/update `{team_key}_prices.json` files
- Add teams to the dashboard UI

## Files

- `teams_list.json` - Team configuration (primary source)
- `auto_scraper_teams.py` - Unified scraper script
- `scraper_ftn_teams.py` - Core scraping logic
- `RUN_ALL_TEAMS.bat` - Windows batch file (continuous)
- `RUN_ALL_TEAMS_ONCE.bat` - Windows batch file (one-time)

## Notes

- Teams are processed sequentially (one at a time)
- 5-second delay between teams
- All teams automatically appear in the dashboard
- No individual batch files needed per team!

For detailed instructions, see `ADD_TEAM_GUIDE.md`.

