# Global VIX Data Collector

This project collects and merges VIX (Volatility Index) data for the **US**, **Japan**, and **Taiwan** markets.

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
*   **Japan VIX (Nikkei VI)**: Current data is not automatically retrievable. Please refer to financial news sources or the Nikkei website.
*   **Taiwan VIX (VIXTWN)**: Current data is not automatically retrievable. Please refer to financial news sources or the TAIFEX website.

### Historical Trend (Last 2 Years)

![VIX Chart](vix_chart.png)

## Data Sources & Instructions

The script automatically fetches US VIX data. For Japan and Taiwan, due to anti-scraping protections and complex site structures, you must manually download the CSV files.

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
*   **Status**: **Manual Download Required**.
*   **Steps**:
    1.  Go to the [TAIFEX Website](https://www.taifex.com.tw/cht/index).
    2.  Navigate to: **統計資料 (Statistics)** -> **臺指選擇權波動率指數 (TAIEX VIX)** -> **歷史資料下載 (Historical Data Download)**.
        *   *Note: If a direct link `https://www.taifex.com.tw/cht/3/vixDataDown` works, use that. Otherwise, use the menu.*
    3.  Select the date range (e.g., 2010/01/01 to present).
    4.  Download the CSV.
    5.  **Rename** the file to: `taifex_vix.csv`.
    6.  Place it in this project folder.

## Output
The script generates `global_vix_merged.csv` containing the combined data (aligned by date).
