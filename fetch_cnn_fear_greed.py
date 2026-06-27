import requests
import pandas as pd
from datetime import datetime
import os
import time

def get_rating(value):
    if value <= 25:
        return "Extreme Fear"
    elif value <= 44:
        return "Fear"
    elif value <= 55:
        return "Neutral"
    elif value <= 74:
        return "Greed"
    else:
        return "Extreme Greed"

def fetch_alternative_me(limit=3000):
    """
    Fetch CNN Fear & Greed Index from alternative.me (mirrors CNN data, goes back to 2018-04-07).
    """
    url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
    print(f"Fetching CNN Fear & Greed from alternative.me (limit={limit})...")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"alternative.me HTTP {resp.status_code}")
            return pd.DataFrame()
        data = resp.json().get("data", [])
        if not data:
            return pd.DataFrame()
        parsed = []
        for d in data:
            dt = pd.to_datetime(int(d["timestamp"]), unit="s").strftime("%Y-%m-%d")
            val = round(float(d["value"]), 2)
            parsed.append({"Date": dt, "Fear_Greed_Value": val, "Rating": get_rating(val)})
        df = pd.DataFrame(parsed)
        df = df.drop_duplicates(subset=["Date"], keep="last")
        df = df.set_index("Date")
        df = df.sort_index()
        print(f"alternative.me: {len(df)} rows, {df.index.min()} ~ {df.index.max()}")
        return df
    except Exception as e:
        print(f"Exception from alternative.me: {e}")
        return pd.DataFrame()

def fetch_cnn_fear_greed(start_date=None):
    """
    Fetch CNN Fear & Greed Index history from CNN's own API (max ~1400 days, back to ~2020-12).
    """
    if not start_date:
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=365)).strftime("%Y-%m-%d")

    print(f"Fetching CNN Fear & Greed Index since {start_date}...")

    url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.cnn.com/markets/fear-and-greed',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"CNN API HTTP {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        historical_data = data.get('fear_and_greed_historical', {}).get('data', [])

        if not historical_data:
            print("No historical data found in CNN response.")
            return pd.DataFrame()

        parsed_data = []
        for point in historical_data:
            timestamp = pd.to_datetime(point['x'], unit='ms')
            value = float(point['y'])
            parsed_data.append({
                'Date': timestamp.strftime('%Y-%m-%d'),
                'Fear_Greed_Value': round(value, 2),
                'Rating': get_rating(value)
            })

        df = pd.DataFrame(parsed_data)
        df = df.drop_duplicates(subset=['Date'], keep='last')
        df = df.set_index('Date')
        print(f"CNN API: {len(df)} rows fetched.")
        return df

    except Exception as e:
        print(f"Exception from CNN API: {e}")
        return pd.DataFrame()

ALTERNATIVE_ME_START = "2018-04-07"  # alternative.me 可回溯至 2018-04-07
HISTORICAL_START     = "2020-12-01"  # CNN 官方 API 最遠 ~2020-12

def main():
    file_path = "cnn_fear_greed.csv"

    # 1. Load existing data
    existing_df = pd.DataFrame()
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, index_col='Date')
            if not existing_df.empty:
                print(f"Found existing data. Range: {existing_df.index.min()} ~ {existing_df.index.max()}")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")

    # 2. Backfill from alternative.me if data doesn't reach 2018
    earliest = existing_df.index.min() if not existing_df.empty else "9999"
    if earliest > ALTERNATIVE_ME_START:
        print(f"Backfilling from alternative.me (existing earliest: {earliest})...")
        altme_df = fetch_alternative_me(limit=3000)
        if not altme_df.empty:
            if not existing_df.empty:
                # CNN data wins for overlapping dates (more accurate)
                existing_df = existing_df.combine_first(altme_df)
            else:
                existing_df = altme_df
            print(f"After alternative.me backfill: {existing_df.index.min()} ~ {existing_df.index.max()}, {len(existing_df)} rows")

    # 3. Incremental update via CNN API (last 2 days overlap)
    last_date = existing_df.index.max() if not existing_df.empty else HISTORICAL_START
    fetch_start = (pd.to_datetime(last_date) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    new_data_df = fetch_cnn_fear_greed(fetch_start)

    if new_data_df.empty and existing_df.empty:
        print("Failed to get any data.")
        return

    # 4. Merge (CNN recent data wins over alternative.me for same dates)
    if not existing_df.empty and not new_data_df.empty:
        final_df = new_data_df.combine_first(existing_df)
    elif not new_data_df.empty:
        final_df = new_data_df
    else:
        final_df = existing_df

    final_df = final_df.sort_index()
    final_df = final_df[~final_df.index.duplicated(keep='last')]

    # 5. Save
    final_df.to_csv(file_path, encoding='utf-8')
    print(f"Saved {len(final_df)} rows to {file_path} ({final_df.index.min()} ~ {final_df.index.max()})")

    if not final_df.empty:
        current = final_df.iloc[-1]
        print("\n--- Current CNN Fear & Greed Index ---")
        print(f"Date:   {final_df.index[-1]}")
        print(f"Value:  {current['Fear_Greed_Value']}")
        print(f"Rating: {current['Rating']}")
        print("--------------------------------------")

if __name__ == "__main__":
    main()
