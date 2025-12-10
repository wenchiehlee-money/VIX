# Project Context: VIX

## Project Overview
This is a **Python-based** workspace dedicated to the **Global VIX (Volatility Index) Data Collection and Analysis**.

The project collects, merges, and visualizes volatility index data from three major markets:
- **US VIX (^VIX)** - CBOE Volatility Index (fully automated via yfinance)
- **Japan VIX (Nikkei VI)** - Nikkei Stock Average Volatility Index (manual CSV download required)
- **Taiwan VIX (VIXTWN)** - TAIEX Options Volatility Index (fully automated for recent months via TAIFEX direct download)

**Current Status:** Active Development. Core data collection, visualization, and update functionality implemented. **Automated daily updates via GitHub Actions**.

## Directory Overview

### Core Scripts
*   **`collect_vix_data.py`**: Main data collection script that fetches US VIX automatically and merges with manually downloaded Japan/Taiwan VIX data. Outputs `global_vix_merged.csv`.
*   **`update_current_vix.py`**: Updates current VIX values in README.md with latest data.
*   **`visualize_vix.py`**: Generates historical trend visualization (`vix_chart.png`) for the last 2 years.

### Configuration & Data
*   **`requirements.txt`**: Python dependencies (FinMind, yfinance, pandas, requests, beautifulsoup4, matplotlib)
*   **`.env`**: Environment configuration (API keys, credentials)
*   **`global_vix_data.csv`** & **`global_vix_merged.csv`**: Merged VIX data from all three markets
*   **`vix_chart.png`**: 2-year historical trend visualization

### Documentation
*   **`README.md`**: Comprehensive usage instructions, data sources, and manual download steps
*   **`LICENSE`**: MIT License (Copyright 2025 wenchiehlee-money)
*   **`GEMINI.md`**: This context file

## Usage & Conventions

### Setup
```bash
pip install -r requirements.txt
```

### Data Collection
```bash
python collect_vix_data.py
```
**Note:** Requires manual download of Japan and Taiwan VIX CSV files (see README.md for instructions)

### Update Current Values
```bash
python update_current_vix.py
```

### Generate Visualization
```bash
python visualize_vix.py
```

## Technical Stack
- **Language**: Python 3.x
- **Data Sources**: yfinance (US), Nikkei Indexes (Japan), TAIFEX (Taiwan)
- **Libraries**: pandas (data manipulation), matplotlib (visualization), FinMind, requests, beautifulsoup4

## Automation
The project includes **GitHub Actions automation** (`.github/workflows/update-vix-data.yml`) that:
- Runs daily at 2 PM UTC (10 PM Taiwan time)
- Automatically collects US and Taiwan VIX data
- Regenerates visualization chart
- Updates README with current values
- Commits changes back to repository
- Can be manually triggered via GitHub Actions interface

## Task History
*   **2025-12-10**: Initial context file `GEMINI.md` generated
*   **2025-12-10**: Implemented VIX data collection, visualization, and README updates
*   **2025-12-10**: Updated GEMINI.md to reflect current project state
*   **2025-12-10**: Implemented **fully automatic Taiwan VIX download** via direct TAIFEX TXT file downloads (format: `https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data_eng/YYYYMMnew.txt`). Supports recent months (typically last 3-4 months available from TAIFEX).
*   **2025-12-10**: Added **GitHub Actions workflow** for daily automatic data collection and repository updates
