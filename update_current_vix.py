import sys
sys.stdout.reconfigure(encoding="utf-8")
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
        if os.path.exists("raw_vix_merged.csv"):
            df = pd.read_csv("raw_vix_merged.csv", index_col='Date', parse_dates=True)
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

def get_vix_sentiment(value):
    """Return sentiment label based on VIX value."""
    try:
        val = float(value)
        if val <= 15:
            return "平穩"
        elif val <= 20:
            return "溫和波動"
        elif val <= 25:
            return "市場關注"
        elif val <= 30:
            return "市場動盪"
        else:
            return "加重動盪"
    except:
        return ""

def get_latest_cnn_fear_greed():
    """Get the latest CNN Fear & Greed Index from the CSV file."""
    try:
        if os.path.exists("cnn_fear_greed.csv"):
            df = pd.read_csv("cnn_fear_greed.csv", index_col='Date')
            if not df.empty:
                latest_value = df['Fear_Greed_Value'].iloc[-1]
                latest_rating = df['Rating'].iloc[-1]
                latest_date = df.index[-1]
                return f"{latest_value:.2f}", latest_rating, latest_date
        return "N/A", "N/A", "N/A"
    except Exception as e:
        return f"Error: {e}", "N/A", "N/A"

def update_readme_with_vix(us_vix_value, taiwan_vix_value, taiwan_vix_date, cnn_fg_value, cnn_fg_rating, cnn_fg_date):
    readme_path = "README.md"

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    us_sentiment = get_vix_sentiment(us_vix_value)
    taiwan_sentiment = get_vix_sentiment(taiwan_vix_value)

    us_display = f'**{us_vix_value}** ({us_sentiment})' if us_sentiment else f'**{us_vix_value}**'
    taiwan_display = f'**{taiwan_vix_value}** ({taiwan_sentiment})' if taiwan_sentiment else f'**{taiwan_vix_value}**'
    cnn_display = f'**{cnn_fg_value}** ({cnn_fg_rating})' if cnn_fg_rating != "N/A" else f'**{cnn_fg_value}**'

    # Update US VIX
    if '<!-- LATEST_US_VIX_DATA -->' in content:
        new_content = re.sub(r'<!-- LATEST_US_VIX_DATA -->', us_display, content)
    else:
        us_pattern = r'\*\s+\*\*US VIX \(\^VIX\)\*\*:.*'
        us_replacement = f'*   **US VIX (^VIX)**: {us_display}'
        new_content = re.sub(us_pattern, us_replacement, content)

    # Update Taiwan VIX line
    taiwan_pattern = r'\*\s+\*\*Taiwan VIX \(VIXTWN\)\*\*:.*'
    taiwan_replacement = f'*   **Taiwan VIX (VIXTWN)**: {taiwan_display} (as of {taiwan_vix_date}, automatically collected from TAIFEX)'
    new_content = re.sub(taiwan_pattern, taiwan_replacement, new_content)

    # Update CNN Fear & Greed Index (add if not exists, or update if exists)
    cnn_pattern = r'\*\s+\*\*CNN Fear & Greed Index\*\*:.*'
    cnn_replacement = f'*   **CNN Fear & Greed Index**: {cnn_display} (as of {cnn_fg_date}, automatically collected from CNN)'
    
    if re.search(cnn_pattern, new_content):
        new_content = re.sub(cnn_pattern, cnn_replacement, new_content)
    else:
        # Insert after Taiwan VIX line
        new_content = re.sub(taiwan_pattern, taiwan_replacement + f'\n{cnn_replacement}', new_content)

    # Generate timestamp in CST
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S CST')
    timestamp_line = f'產生時間: {timestamp}\n\n'

    # Clean up ANY existing "產生時間" lines before adding the new one
    new_content = re.sub(r'產生時間: .*?\n\n', '', new_content)

    # Insert the new timestamp before the chart image
    chart_pattern = r'(\!\[VIX Chart\]\(vix_chart\.(png|svg)\))'
    new_content = re.sub(chart_pattern, timestamp_line + r'![VIX Chart](vix_chart.svg)', new_content)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated README.md with latest US VIX: {us_vix_value}")
    print(f"Updated README.md with latest Taiwan VIX: {taiwan_vix_value} (as of {taiwan_vix_date})")
    print(f"Updated README.md with CNN Fear & Greed Index: {cnn_fg_value} ({cnn_fg_rating})")
    print(f"Updated README.md with timestamp: {timestamp}")

def get_vix_risk_level(us_vix, tw_vix, cnn_fg):
    """計算複合風險分數 (0-100) 與配置建議。"""
    try:
        u = float(us_vix)
        us_score = 10 if u < 15 else (30 if u < 20 else (55 if u < 25 else (75 if u < 30 else 95)))
    except: us_score = 50
    try:
        t = float(tw_vix)
        tw_score = 10 if t < 20 else (35 if t < 30 else (55 if t < 40 else (75 if t < 50 else 95)))
    except: tw_score = 50
    try:
        c = float(cnn_fg)
        cnn_score = 90 if c < 15 else (65 if c < 25 else (45 if c < 45 else (25 if c < 55 else (35 if c < 75 else 60))))
    except: cnn_score = 35
    composite = round(us_score * 0.4 + tw_score * 0.4 + cnn_score * 0.2)
    if composite < 25:   level, park_pct = "低風險",    70
    elif composite < 50: level, park_pct = "中低風險",  55
    elif composite < 70: level, park_pct = "中高風險",  35
    elif composite < 85: level, park_pct = "高風險",    15
    else:                level, park_pct = "進場訊號",   0
    return composite, level, park_pct, 100 - park_pct


def write_current_vix_csv(us_vix, tw_vix, tw_date, cnn_fg, cnn_rating, cnn_date):
    """輸出 current_vix.csv 供 Google Sheets IMPORTDATA 使用（僅原始指數）。"""
    cst = pytz.timezone('Asia/Taipei')
    updated = datetime.now(cst).strftime('%Y-%m-%d %H:%M')
    lines = [
        "metric,value,sentiment,date",
        f"US_VIX,{us_vix},{get_vix_sentiment(us_vix)},{updated}",
        f"TW_VIX,{tw_vix},{get_vix_sentiment(tw_vix)},{tw_date}",
        f"CNN_FG,{cnn_fg},{cnn_rating},{cnn_date}",
    ]
    with open("current_vix.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"寫入 current_vix.csv（US={us_vix}, TW={tw_vix}, CNN={cnn_fg}）")


def update_readme_placeholders(us_vix, tw_vix, tw_date, cnn_fg, cnn_rating, cnn_date):
    """用 HTML comment 標籤更新 README 中的佔位值。"""
    readme_path = "README.md"
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def replace_tag(text, tag, value):
        return re.sub(rf'<!-- {tag} -->.*?<!-- /{tag} -->', f'<!-- {tag} -->{value}<!-- /{tag} -->', text, flags=re.DOTALL)

    us_sent  = get_vix_sentiment(us_vix)
    tw_sent  = get_vix_sentiment(tw_vix)
    composite, level, park_pct, bank_pct = get_vix_risk_level(us_vix, tw_vix, cnn_fg)

    content = replace_tag(content, "US_VIX_VAL",  f"**{us_vix}**")
    content = replace_tag(content, "US_VIX_SENT", us_sent)
    content = replace_tag(content, "TW_VIX_VAL",  f"**{tw_vix}**")
    content = replace_tag(content, "TW_VIX_SENT", tw_sent)
    content = replace_tag(content, "TW_VIX_DATE", tw_date)
    content = replace_tag(content, "CNN_FG_VAL",  f"**{cnn_fg}**")
    content = replace_tag(content, "CNN_FG_SENT", cnn_rating)
    content = replace_tag(content, "CNN_FG_DATE", cnn_date)

    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S CST')
    content = re.sub(r'產生時間: .*?\n', f'產生時間: {timestamp}\n', content)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"更新 README.md（複合分數={composite} {level}）")


if __name__ == "__main__":
    print("Fetching latest data...")
    latest_us_vix = get_latest_us_vix()
    latest_taiwan_vix, taiwan_vix_date = get_latest_taiwan_vix()
    latest_cnn_val, latest_cnn_rating, latest_cnn_date = get_latest_cnn_fear_greed()

    # 修正後的 README 更新（用 comment tag 替換，不用舊 regex）
    update_readme_placeholders(latest_us_vix, latest_taiwan_vix, taiwan_vix_date,
                               latest_cnn_val, latest_cnn_rating, latest_cnn_date)

    # 新增：輸出 current_vix.csv 供 Google Sheets 使用
    write_current_vix_csv(latest_us_vix, latest_taiwan_vix, taiwan_vix_date,
                          latest_cnn_val, latest_cnn_rating, latest_cnn_date)
