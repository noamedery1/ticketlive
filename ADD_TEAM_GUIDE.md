# How to Add Teams to the Scraper

The scraper automatically discovers and scrapes all teams. You can add teams in two ways:

## Method 1: Using `teams_list.json` (Recommended)

Edit the `teams_list.json` file and add your team entry:

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
    },
    {
      "team_key": "manchester-united",
      "team_name": "Manchester United",
      "team_url": "https://www.footballticketnet.com/manchester-united-football-tickets/filter/home_away/home-matches"
    }
  ]
}
```

### Fields:
- **team_key**: A unique identifier (lowercase, use hyphens for spaces, e.g., "manchester-united")
- **team_name**: Display name for the team
- **team_url**: The URL to the team's home matches page on FootballTicketNet

## Method 2: Using `*_prices.json` Files (Fallback)

If `teams_list.json` doesn't exist, the scraper will automatically discover teams from any `*_prices.json` files in the directory.

Create a file named `{team_key}_prices.json` with at minimum:

```json
{
  "team_name": "Manchester United",
  "team_url": "https://www.footballticketnet.com/manchester-united-football-tickets/filter/home_away/home-matches"
}
```

## Finding the Team URL

1. Go to [FootballTicketNet](https://www.footballticketnet.com/)
2. Search for your team
3. Navigate to the team's page
4. Click on "Home Matches" filter (or use the filter URL)
5. Copy the URL - it should look like:
   `https://www.footballticketnet.com/{team-name}-football-tickets/filter/home_away/home-matches`

## Running the Scraper

After adding teams, simply run:

**Windows:**
- `RUN_ALL_TEAMS.bat` - Runs continuously (every 3 hours)
- `RUN_ALL_TEAMS_ONCE.bat` - Runs once and exits

**Manual:**
```bash
python auto_scraper_teams.py        # Continuous (every 3 hours)
python auto_scraper_teams.py --once # Run once
```

The scraper will:
1. Load all teams from `teams_list.json` (or discover from `*_prices.json` files)
2. Scrape each team one by one
3. Save data to `{team_key}_prices.json` files
4. Commit and push to Git (if configured)

## Notes

- The scraper processes teams sequentially (one at a time)
- There's a 5-second delay between teams to be nice to the server
- All teams are automatically added to the dashboard UI
- No need to create separate batch files for each team!

