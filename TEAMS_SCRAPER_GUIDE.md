# Teams Scraper Guide

## 📋 Overview

This system allows you to scrape prices for multiple football teams from FootballTicketNet. You can easily add new teams by editing a configuration file.

## 📁 Files

- **`{team_key}_prices.json`** - Team files (e.g., `arsenal_prices.json`, `barcelona_prices.json`)
  - Create these manually to add new teams
  - Contains `team_name`, `team_url`, and `games` array
- **`scraper_ftn_teams.py`** - Main scraper script (runs single team)
- **`auto_scraper_teams.py`** - Auto scraper that discovers teams from `*_prices.json` files and pushes to git
- **`RUN_ALL_TEAMS.bat`** - Windows batch file to run all teams once
- **`ftn_teams_data.json`** - Main output file with all teams data (used by UI)
- **`TEAM_TEMPLATE.json`** - Template for creating new team files
- **`CREATE_TEAM_TEMPLATE.bat`** - Interactive script to create new team files

## ➕ Adding New Teams

### Method 1: Create Team File Manually (Recommended)

Create a new file named `{team_key}_prices.json` (e.g., `manchester-united_prices.json`) with this format:

```json
{
  "team_name": "Manchester United",
  "team_url": "https://www.footballticketnet.com/manchester-united-football-tickets/filter/home_away/home-matches",
  "games": []
}
```

**Important:**
- **Filename**: Must be `{team_key}_prices.json` (e.g., `arsenal_prices.json`, `barcelona_prices.json`)
- **`team_name`**: Display name for the team (shown in UI)
- **`team_url`**: Must be the home matches filter URL (ends with `/filter/home_away/home-matches`)
- **`games`**: Leave as empty array `[]` - scraper will populate it

### Method 2: Use Template

1. Copy `TEAM_TEMPLATE.json` to `{team_key}_prices.json`
2. Edit the file and fill in `team_name` and `team_url`
3. Or use `CREATE_TEAM_TEMPLATE.bat` for interactive creation

### Example Files:
- `arsenal_prices.json` → Team key: `arsenal`
- `barcelona_prices.json` → Team key: `barcelona`
- `manchester-united_prices.json` → Team key: `manchester-united`

## 🚀 Running the Scraper

### Option 1: Run All Teams (Recommended)
Double-click **`RUN_ALL_TEAMS.bat`** or run:
```batch
python auto_scraper_teams.py --once
```

This will:
1. **Discover** all teams from `*_prices.json` files in the directory
2. **Scrape** each team's home games
3. **Collect** prices for each game
4. **Save** to:
   - `ftn_teams_data.json` (all teams in one file - used by UI)
   - Individual `{team_key}_prices.json` files (one per team)
5. **Commit and push** all JSON files to git server

### Option 2: Run Single Team
```batch
python scraper_ftn_teams.py arsenal
python scraper_ftn_teams.py barcelona
```

### Option 3: Continuous Auto-Run (Twice Daily)
```batch
python auto_scraper_teams.py
```

This runs every 12 hours automatically and pushes to git.

## 📊 Output Files

### Main File: `ftn_teams_data.json`
Contains all teams data in one file:
```json
{
  "arsenal": {
    "team_name": "Arsenal",
    "team_url": "...",
    "games": [
      {
        "match_name": "Arsenal vs Chelsea",
        "url": "...",
        "opponent": "Chelsea",
        "date": "27/12/25",
        "price_history": [...],
        "latest_prices": {...}
      }
    ],
    "last_updated": "2025-12-24T10:30:00"
  }
}
```

### Individual Team Files: `{team_key}_prices.json`
Same structure but only for that specific team (easier to access).

## 🔄 Git Push

The `auto_scraper_teams.py` automatically:
1. Commits all updated JSON files
2. Pushes to the remote git repository
3. Uses commit message: `"Auto-update teams prices - {timestamp}"`

Make sure you have:
- Git initialized in the project directory
- Remote repository configured
- Git credentials set up

## ⚙️ Configuration

### Scrape Interval
Edit `auto_scraper_teams.py`:
```python
SCRAPE_INTERVAL_HOURS = 12.0  # Change to your desired interval
```

### Output File
Edit `scraper_ftn_teams.py`:
```python
OUTPUT_FILE = 'ftn_teams_data.json'  # Change if needed
```

## 🐛 Troubleshooting

### "No teams found"
- Make sure you have at least one `*_prices.json` file in the directory
- Check the filename format: `{team_key}_prices.json` (e.g., `arsenal_prices.json`)
- Verify the JSON file has `team_name` and `team_url` fields
- Check JSON syntax is valid

### "No games found"
- Check the URL in `teams_config.json` is correct
- Make sure it's the home matches filter URL
- Verify the team page has games listed

### "Git push failed"
- Check git is initialized: `git status`
- Verify remote is set: `git remote -v`
- Check credentials are configured

## 📝 Notes

- The scraper only gets **home games** (Team vs Opponent, not Opponent vs Team)
- Prices are filtered for **"Up To 2 Seats Together"**
- Price history is preserved even if games are removed from the site
- Each team scraper takes several minutes (visits each game page)

