import yfinance as yf
import pandas as pd
import re
from datetime import datetime
import pytz
import os

def get_latest_us_vix():
    try:
        vix = yf.Ticker("^VIX")
        # Fetching the last day's data
        df = vix.history(period="1d")
        if not df.empty:
            latest_close = df['Close'].iloc[0]
            return f"{latest_close:.2f}"
        else:
            return "N/A (No data found)"
    except Exception as e:
        return f"Error: {e}"

def get_latest_taiwan_vix():
    """Get the latest Taiwan VIX value from the merged CSV file."""
    try:
        if os.path.exists("global_vix_merged.csv"):
            df = pd.read_csv("global_vix_merged.csv", index_col='Date', parse_dates=True)
            if 'Taiwan_VIX' in df.columns:
                # Get the last non-NaN value
                taiwan_vix = df['Taiwan_VIX'].dropna()
                if not taiwan_vix.empty:
                    latest_value = taiwan_vix.iloc[-1]
                    latest_date = taiwan_vix.index[-1].strftime('%Y-%m-%d')
                    return f"{latest_value:.2f}", latest_date
        return "N/A", "N/A"
    except Exception as e:
        return f"Error: {e}", "N/A"

def update_readme_with_vix(us_vix_value, taiwan_vix_value, taiwan_vix_date):
    readme_path = "README.md"

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update US VIX
    new_content = re.sub(r'<!-- LATEST_US_VIX_DATA -->', f'**{us_vix_value}**', content)

    # Update Taiwan VIX line
    taiwan_pattern = r'\*\s+\*\*Taiwan VIX \(VIXTWN\)\*\*:.*'
    taiwan_replacement = f'*   **Taiwan VIX (VIXTWN)**: **{taiwan_vix_value}** (as of {taiwan_vix_date}, automatically collected from TAIFEX)'
    new_content = re.sub(taiwan_pattern, taiwan_replacement, new_content)

    # Generate timestamp in CST
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S CST')
    timestamp_line = f'產生時間: {timestamp}\n\n'

    # Replace existing timestamp or add new one before the chart image
    # Pattern: Find any existing timestamp line before the chart, or just the chart line itself
    chart_pattern = r'(產生時間: .*?\n\n)?(\!\[VIX Chart\]\(vix_chart\.(png|svg)\))'
    new_content = re.sub(chart_pattern, timestamp_line + r'![VIX Chart](vix_chart.svg)', new_content)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated README.md with latest US VIX: {us_vix_value}")
    print(f"Updated README.md with latest Taiwan VIX: {taiwan_vix_value} (as of {taiwan_vix_date})")
    print(f"Updated README.md with timestamp: {timestamp}")

if __name__ == "__main__":
    print("Fetching latest VIX data...")
    latest_us_vix = get_latest_us_vix()
    latest_taiwan_vix, taiwan_vix_date = get_latest_taiwan_vix()
    update_readme_with_vix(latest_us_vix, latest_taiwan_vix, taiwan_vix_date)
