import pandas as pd
import yfinance as yf
import os

def collect_us_vix(start_date, end_date):
    print("Collecting US VIX (^VIX)...")
    try:
        vix = yf.Ticker("^VIX")
        df = vix.history(start=start_date, end=end_date)
        if df.empty:
            print("  No data found for US VIX.")
            return pd.DataFrame()
            
        df = df[['Close']].rename(columns={'Close': 'US_VIX'})
        df.index = df.index.tz_localize(None) 
        print(f"  Got {len(df)} rows.")
        return df
    except Exception as e:
        print(f"  Error collecting US VIX: {e}")
        return pd.DataFrame()

def load_japan_vix_local(file_path, start_date, end_date):
    print(f"Checking for local Japan VIX file: {file_path}...")
    if not os.path.exists(file_path):
        print(f"  File not found. Please download it from Nikkei website.")
        print(f"  URL: https://indexes.nikkei.co.jp/nkave/archives/data/nk225vi_daily_jp.csv (or similar)")
        return pd.DataFrame()
    
    try:
        # Nikkei CSV is usually Shift-JIS
        df = pd.read_csv(file_path, encoding='shift-jis')
        
        # Clean columns
        # Expected: 日付, 始値, 高値, 安値, 終値 (Date, Open, High, Low, Close)
        # Sometimes there's a header line to skip or footer
        
        # Rename columns based on position to be safe if headers vary
        # Assuming format: Date, Open, High, Low, Close
        df = df.iloc[:, :5] # Keep first 5 cols
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close']
        
        # Drop rows that are not data (e.g. empty or headers repeated)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        df = df.set_index('Date')
        df = df[['Close']].rename(columns={'Close': 'Japan_VIX'})
        
        # Filter
        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        df = df.loc[mask]
        print(f"  Loaded {len(df)} rows from local file.")
        return df
    except Exception as e:
        print(f"  Error reading local Japan VIX: {e}")
        return pd.DataFrame()

def load_taiwan_vix_local(file_path, start_date, end_date):
    print(f"Checking for local Taiwan VIX file: {file_path}...")
    if not os.path.exists(file_path):
        print(f"  File not found. Please download from TAIFEX.")
        print(f"  URL: https://www.taifex.com.tw/cht/3/vixDataDown (Manual download required)")
        return pd.DataFrame()

    try:
        # TAIFEX CSV usually has headers like "Date", "VIX Index"
        # Encoding often Big5 or UTF-8
        try:
            df = pd.read_csv(file_path, encoding='big5')
        except:
            df = pd.read_csv(file_path, encoding='utf-8')
            
        # Inspect columns to find Date and Close
        # TAIFEX VIX columns: "日期", "收盤價" (Date, Close)
        # Map columns
        col_map = {}
        for c in df.columns:
            if '日期' in c or 'Date' in c:
                col_map[c] = 'Date'
            elif '收盤' in c or 'Close' in c:
                col_map[c] = 'Taiwan_VIX'
                
        df = df.rename(columns=col_map)
        
        if 'Date' not in df.columns or 'Taiwan_VIX' not in df.columns:
            print("  Could not identify Date or VIX columns in Taiwan CSV.")
            print(f"  Columns found: {df.columns.tolist()}")
            return pd.DataFrame()
            
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.set_index('Date')
        df = df[['Taiwan_VIX']]
        
        mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
        df = df.loc[mask]
        print(f"  Loaded {len(df)} rows from local file.")
        return df
    except Exception as e:
        print(f"  Error reading local Taiwan VIX: {e}")
        return pd.DataFrame()

def main():
    start_date = "2010-01-01"
    end_date = pd.Timestamp.now().strftime("%Y-%m-%d")
    
    # 1. US VIX (Auto)
    us_df = collect_us_vix(start_date, end_date)
    
    # 2. Japan VIX (Local File)
    # User should download: https://indexes.nikkei.co.jp/nkave/archives/data/nk225vi_daily_jp.csv
    jp_file = "nk225vi_daily_jp.csv"
    jp_df = load_japan_vix_local(jp_file, start_date, end_date)
    
    # 3. Taiwan VIX (Local File)
    # User should download from TAIFEX and save as taifex_vix.csv
    tw_file = "taifex_vix.csv"
    tw_df = load_taiwan_vix_local(tw_file, start_date, end_date)
    
    # Merge
    print("\nMerging all available data...")
    merged_df = pd.DataFrame()
    
    if not us_df.empty:
        merged_df = us_df.copy()
        
    for df in [jp_df, tw_df]:
        if not df.empty:
            if merged_df.empty:
                merged_df = df
            else:
                merged_df = merged_df.join(df, how='outer')
    
    if not merged_df.empty:
        merged_df = merged_df.sort_index()
        output_file = "global_vix_merged.csv"
        merged_df.to_csv(output_file)
        print(f"\nSUCCESS! Data saved to {output_file}")
        print("Data Summary:")
        print(merged_df.describe())
        print("\nHead:")
        print(merged_df.head())
    else:
        print("\nNo data collected.")

if __name__ == "__main__":
    main()