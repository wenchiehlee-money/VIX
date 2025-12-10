# Global VIX Data Collector

![Update VIX Data Daily](https://github.com/wenchiehlee-money/VIX/actions/workflows/update-vix-data.yml/badge.svg)

This project collects and merges VIX (Volatility Index) data for the **US**, **Japan**, and **Taiwan** markets.

## 🤖 Automatic Daily Updates

This repository automatically updates VIX data **every day at 2 PM UTC** (10 PM Taiwan time) using GitHub Actions. The automation:
- ✅ Collects latest US VIX data
- ✅ Downloads new Taiwan VIX data from TAIFEX
- ✅ Regenerates the visualization chart
- ✅ Updates current VIX values in README
- ✅ Commits changes back to the repository

You can also manually trigger the update from the [Actions tab](../../actions/workflows/update-vix-data.yml).

## Prerequisites

1.  **Python 3.x**
2.  Install required libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the collection script:

```bash
python collect_vix_data.py
```

## Current VIX Data

*   **US VIX (^VIX)**: **17.42**
*   **Japan VIX (Nikkei VI)**: Manual download required. Please refer to financial news sources or the Nikkei website.
*   **Taiwan VIX (VIXTWN)**: **20.15** (as of 2025-12-10, automatically collected from TAIFEX)

### Historical Trend (Last 2 Years)

產生時間: 2025-12-10 23:08:20 CST

![VIX Chart](vix_chart.svg)

## Data Sources & Instructions

The script automatically fetches **US VIX** and **Taiwan VIX** data (recent months). Japan VIX requires manual download due to website limitations.

### 1. US VIX (`^VIX`)
*   **Status**: **Automatic**. Fetched via `yfinance`.

### 2. Japan VIX (Nikkei Stock Average Volatility Index)
*   **Status**: **Manual Download Required**.
*   **Steps**:
    1.  Go to the [Nikkei Indexes Download Center](https://indexes.nikkei.co.jp/nkave/archives/data/nk225vi_daily_jp.csv).
    2.  Download the **Daily Data (CSV)** file.
    3.  **Rename** the file to: `nk225vi_daily_jp.csv`.
    4.  Place it in this project folder.

### 3. Taiwan VIX (TAIEX Options Volatility Index)
*   **Status**: **Fully Automatic**.
*   **Automatic Download**: The script automatically downloads Taiwan VIX data from TAIFEX's official data files.
*   **Data Availability**: TAIFEX provides recent months online (typically last 3-4 months). The script downloads all available months automatically.
*   **Historical Data Accumulation**: With daily GitHub Actions automation, historical data accumulates over time. After running for several months, you'll have a complete historical dataset without any manual intervention.
*   **Manual Download** (optional, only if you need older historical data immediately):
    1.  Download monthly TXT files from TAIFEX: `https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data_eng/YYYYMMnew.txt` (replace YYYYMM with year and month, e.g., 202401new.txt for January 2024)
    2.  Combine multiple months into a CSV file with columns: Date, Close (VIX value)
    3.  Save as `taifex_vix.csv` in this project folder
    4.  The script will merge this with automatically downloaded data

## Output
The script generates `global_vix_merged.csv` containing the combined data (aligned by date).
