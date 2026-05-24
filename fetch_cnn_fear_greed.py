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

def fetch_cnn_fear_greed(start_date=None):
    """
    Fetch CNN Fear & Greed Index history from CNN API.
    """
    if not start_date:
        # Default to 1 year ago if no start date provided
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
            print(f"Error fetching data: HTTP {response.status_code}")
            return pd.DataFrame()
        
        data = response.json()
        historical_data = data.get('fear_and_greed_historical', {}).get('data', [])
        
        if not historical_data:
            print("No historical data found in response.")
            return pd.DataFrame()
        
        # Parse data
        parsed_data = []
        for point in historical_data:
            # x is timestamp in milliseconds
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
        
        print(f"Successfully fetched {len(df)} days of CNN Fear & Greed Index.")
        return df

    except Exception as e:
        print(f"Exception while fetching CNN data: {e}")
        return pd.DataFrame()

def main():
    file_path = "cnn_fear_greed.csv"
    
    # 1. Load existing data if available
    existing_df = pd.DataFrame()
    last_date = None
    
    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, index_col='Date')
            if not existing_df.empty:
                last_date = existing_df.index.max()
                print(f"Found existing data. Last date: {last_date}")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
    
    # 2. Determine start date for API (fetch since last date to be safe)
    # If we have data, we fetch since last date - 2 days to catch any updates
    if last_date:
        fetch_start = (pd.to_datetime(last_date) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        # Default to a few years back for initial population
        fetch_start = "2024-01-01"
    
    # 3. Fetch new data
    new_data_df = fetch_cnn_fear_greed(fetch_start)
    
    if new_data_df.empty and existing_df.empty:
        print("Failed to get any data.")
        return

    # 4. Merge data
    if not existing_df.empty and not new_data_df.empty:
        # Update existing with new data
        final_df = new_data_df.combine_first(existing_df)
    elif not new_data_df.empty:
        final_df = new_data_df
    else:
        final_df = existing_df
    
    # Sort and remove duplicates
    final_df = final_df.sort_index()
    final_df = final_df[~final_df.index.duplicated(keep='last')]
    
    # 5. Save to CSV
    final_df.to_csv(file_path)
    print(f"Saved {len(final_df)} rows to {file_path}")
    
    # Output current summary
    if not final_df.empty:
        current = final_df.iloc[-1]
        print("\n--- Current CNN Fear & Greed Index ---")
        print(f"Date: {final_df.index[-1]}")
        print(f"Value: {current['Fear_Greed_Value']}")
        print(f"Rating: {current['Rating']}")
        print("--------------------------------------")

if __name__ == "__main__":
    main()
