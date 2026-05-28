import pandas as pd
import yfinance as yf
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

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

def collect_taiwan_vix_auto(start_date, end_date):
    """
    Automatically download Taiwan VIX data from TAIFEX website.
    Downloads directly from TAIFEX TXT files.
    """
    print("Collecting Taiwan VIX (TAIFEX) automatically...")

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        all_data = []

        # Calculate months to fetch
        current_date = end_dt
        months_to_fetch = []

        # Go back to start date, collecting all months
        while current_date >= start_dt:
            months_to_fetch.append((current_date.year, current_date.month))
            # Move to previous month
            if current_date.month == 1:
                current_date = pd.Timestamp(current_date.year - 1, 12, 1)
            else:
                current_date = pd.Timestamp(current_date.year, current_date.month - 1, 1)

        months_to_fetch.reverse()  # Process chronologically

        print(f"  Downloading data for {len(months_to_fetch)} months...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        for year, month in months_to_fetch:
            try:
                # Direct download URL pattern found on TAIFEX website
                # Format: https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data_eng/YYYYMMnew.txt
                month_str = f"{year}{str(month).zfill(2)}"
                url = f"https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data_eng/{month_str}new.txt"

                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    # Parse the TXT file
                    # Format: Date\t\tClosing Time\t\tDaily Index\t\tLast 1 min AVG
                    # Date format: YYYYMMDD
                    lines = response.text.strip().split('\n')

                    data_rows = []
                    for line in lines:
                        # Skip empty lines, headers, and separator lines
                        if not line.strip() or 'Date' in line or '---' in line:
                            continue

                        # Split by tabs
                        parts = [p.strip() for p in line.split('\t') if p.strip()]

                        if len(parts) >= 3:
                            try:
                                date_str = parts[0]  # YYYYMMDD format
                                vix_val_str = parts[2]  # Daily Index (3rd column)

                                # Parse date (format: YYYYMMDD)
                                date_obj = pd.to_datetime(date_str, format='%Y%m%d')
                                vix_val = float(vix_val_str)

                                data_rows.append({
                                    'Date': date_obj,
                                    'Taiwan_VIX': vix_val
                                })
                            except:
                                continue

                    if data_rows:
                        all_data.extend(data_rows)
                        print(f"    Downloaded {year}/{str(month).zfill(2)}: {len(data_rows)} rows")

            except requests.exceptions.RequestException:
                # File might not exist for this month (too old or future month)
                pass
            except Exception as e:
                print(f"    Warning: Could not fetch {year}/{month}: {str(e)[:50]}")
                continue

        # Process collected data
        if all_data:
            df = pd.DataFrame(all_data)
            df = df.set_index('Date')
            df = df.sort_index()
            df = df[~df.index.duplicated(keep='first')]

            # Filter by date range
            mask = (df.index >= start_dt) & (df.index <= end_dt)
            df = df.loc[mask]

            if not df.empty:
                print(f"  Successfully downloaded {len(df)} rows from TAIFEX")
                return df

        print("  No data downloaded, trying local file...")
        return load_taiwan_vix_local('taifex_vix.csv', start_date, end_date)

    except Exception as e:
        print(f"  Error in automatic download: {e}")
        print("  Falling back to local file method...")
        return load_taiwan_vix_local('taifex_vix.csv', start_date, end_date)


def collect_taiwan_vix_alternative(start_date, end_date):
    """
    Alternative method to fetch Taiwan VIX data using monthly queries.
    """
    print("  Using alternative download method (monthly queries)...")

    try:
        all_data = []
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # Query by month to avoid TAIFEX limitations
        current_date = start_dt

        while current_date <= end_dt:
            year = current_date.year
            month = current_date.month

            # TAIFEX daily VIX URL pattern
            url = f"https://www.taifex.com.tw/cht/3/vixDaily3M"

            params = {
                'queryYear': str(year),
                'queryMonth': str(month).zfill(2),
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.post(url, data=params, headers=headers, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table', {'class': 'table_f'})

                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cols = row.find_all('td')
                        if len(cols) >= 5:  # Date, Open, High, Low, Close
                            try:
                                date_str = cols[0].text.strip()
                                close_value = cols[4].text.strip().replace(',', '')

                                date_obj = pd.to_datetime(date_str)
                                all_data.append({
                                    'Date': date_obj,
                                    'Taiwan_VIX': float(close_value)
                                })
                            except:
                                continue

            # Move to next month
            if month == 12:
                current_date = pd.Timestamp(year + 1, 1, 1)
            else:
                current_date = pd.Timestamp(year, month + 1, 1)

        if all_data:
            df = pd.DataFrame(all_data)
            df = df.set_index('Date')
            df = df.sort_index()
            df = df[~df.index.duplicated(keep='first')]

            # Filter by date range
            mask = (df.index >= start_dt) & (df.index <= end_dt)
            df = df.loc[mask]

            print(f"  Successfully downloaded {len(df)} rows via alternative method")
            return df

        print("  Alternative method failed, falling back to local file...")
        return load_taiwan_vix_local('taifex_vix.csv', start_date, end_date)

    except Exception as e:
        print(f"  Error in alternative download: {e}")
        return load_taiwan_vix_local('taifex_vix.csv', start_date, end_date)


def load_taiwan_vix_local(file_path, start_date, end_date):
    print(f"Checking for local Taiwan VIX file: {file_path}...")
    if not os.path.exists(file_path):
        print(f"  File not found.")
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

def load_taiwan_vix_historical(file_path):
    """Load the macromicro.me historical Taiwan VIX CSV (taiwan_vix_historical.csv)."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df = df.rename(columns={df.columns[0]: 'Taiwan_VIX'})
        df = df[['Taiwan_VIX']]
        df = df[~df.index.duplicated(keep='first')]
        print(f"  Loaded {len(df)} rows from {file_path} ({df.index.min().date()} ~ {df.index.max().date()})")
        return df
    except Exception as e:
        print(f"  Error loading {file_path}: {e}")
        return pd.DataFrame()


def main():
    output_file = "global_vix_merged.csv"

    # Date ranges
    start_date = "2010-01-01"
    end_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    # 1. US VIX (Auto - full history)
    us_df = collect_us_vix(start_date, end_date)

    # 2. Japan VIX (Local File)
    jp_file = "nk225vi_daily_jp.csv"
    jp_df = load_japan_vix_local(jp_file, start_date, end_date)

    # 3. Taiwan VIX - combine historical CSV + TAIFEX recent updates
    print("\nLoading Taiwan VIX historical base (taiwan_vix_historical.csv)...")
    tw_historical = load_taiwan_vix_historical("taiwan_vix_historical.csv")

    # TAIFEX only keeps ~2 months; fetch current + previous month to catch the latest days
    print("Fetching latest Taiwan VIX from TAIFEX (current + previous month)...")
    taiwan_start_date = (pd.Timestamp.now() - pd.Timedelta(days=65)).strftime("%Y-%m-%d")
    tw_recent = collect_taiwan_vix_auto(taiwan_start_date, end_date)

    # Merge: recent TAIFEX takes precedence over historical CSV for overlapping dates
    if not tw_historical.empty and not tw_recent.empty:
        tw_df = tw_recent.combine_first(tw_historical)
    elif not tw_recent.empty:
        tw_df = tw_recent
    else:
        tw_df = tw_historical

    if not tw_df.empty:
        tw_df = tw_df.sort_index()
        tw_df = tw_df[~tw_df.index.duplicated(keep='first')]
        print(f"  Taiwan VIX combined: {tw_df['Taiwan_VIX'].notna().sum()} rows "
              f"({tw_df[tw_df.Taiwan_VIX.notna()].index.min().date()} ~ "
              f"{tw_df[tw_df.Taiwan_VIX.notna()].index.max().date()})")

    # Build merged dataframe with outer join so all dates are included
    print("\nMerging all data...")
    frames = [df for df in [us_df, jp_df, tw_df] if not df.empty]
    if not frames:
        print("No data collected.")
        return

    merged_df = frames[0]
    for df in frames[1:]:
        merged_df = merged_df.combine_first(df)

    merged_df = merged_df.sort_index()
    merged_df = merged_df[~merged_df.index.duplicated(keep='first')]
    
    # Add timestamps for freshness tracking
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged_df["process_timestamp"] = now_str
    merged_df["download_timestamp"] = now_str
    
    merged_df.to_csv(output_file)

    print(f"\nSUCCESS! Data saved to {output_file}")
    print("\nData Summary:")
    print(merged_df.describe())
    print("\nRecent data (last 5 rows):")
    print(merged_df.tail())

if __name__ == "__main__":
    main()