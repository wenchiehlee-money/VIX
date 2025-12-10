import yfinance as yf
import pandas as pd
import re
from datetime import datetime
import pytz

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

def update_readme_with_vix(vix_value):
    readme_path = "README.md"

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the placeholder with the actual value
    new_content = re.sub(r'<!-- LATEST_US_VIX_DATA -->', f'**{vix_value}**', content)

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

    print(f"Updated README.md with latest US VIX: {vix_value}")
    print(f"Updated README.md with timestamp: {timestamp}")

if __name__ == "__main__":
    print("Fetching latest US VIX data...")
    latest_us_vix = get_latest_us_vix()
    update_readme_with_vix(latest_us_vix)
