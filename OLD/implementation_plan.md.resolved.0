# Viagogo Benchmark Agent - Implementation Plan

## Goal Description
Develop an automated data agent to scrape "lowest available price" per category for FIFA World Cup 2026 matches from Viagogo. The agent will read a list of matches, scrape pricing data, and export the results to both JSON (for structured data) and CSV (for easy import to Google Sheets/Excel).

## User Review Required
> [!NOTE]
> **Blocking detection**: Viagogo has anti-bot measures. I will use `playwright-stealth` or standard Playwright with user-agent spoofing, but heavy usage might still trigger captchas. For this implementation, I will focus on the logic. If blocked, we may need to discuss advanced evasion techniques (out of scope for basic script).

## Proposed Changes

### Project Structure
Directory: `scratch/viagogo_benchmark/`

#### [NEW] [requirements.txt](file:///C:/Users/noam.edery/.gemini/antigravity/scratch/viagogo_benchmark/requirements.txt)
- `playwright`
- `pandas` (for easy CSV handling)

#### [NEW] [input.json](file:///C:/Users/noam.edery/.gemini/antigravity/scratch/viagogo_benchmark/input.json)
- Sample input file based on the prompt's specifications.

#### [NEW] [viagogo_agent.py](file:///C:/Users/noam.edery/.gemini/antigravity/scratch/viagogo_benchmark/viagogo_agent.py)
**Core Logic:**
1.  **Load Input**: Read `input.json`.
2.  **Browser Setup**: Initialize Playwright (Chromium).
3.  **Iterate Matches**:
    *   Navigate to `url`.
    *   Wait for listing container (`div[data-testid="listing-card"]` or fallback).
    *   **Scrape Listings**:
        *   Extract raw category name.
        *   Extract raw price string.
        *   Detect currency symbol.
    *   **Normalize**: Convert prices to float.
    *   **Aggregate**: Group by Category + Currency -> Find Min Price.
4.  **Generate Output**:
    *   Save `output.json`.
    *   Convert nested JSON to flat CSV structure for `benchmark_results.csv`.

**CSV Structure:**
Columns: `Match ID`, `Match Name`, `Date`, `City`, `Category`, `Min Price`, `Currency`
*One row per category per match.*

## Verification Plan

### Automated Tests
- Run `python viagogo_agent.py`.
- Check if `output.json` exists and is valid JSON.
- Check if `benchmark_results.csv` exists and has data.

### Manual Verification
- Inspect the generated CSV to ensure prices and categories look reasonable (e.g., no "$0" or "NaN" unless valid).
