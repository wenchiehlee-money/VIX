"""
Fetch full historical Taiwan VIX (VIXTWN) data from TAIFEX.
Saves to taiwan_vix_historical.csv with columns: Date, IVIXTWN
"""
import pandas as pd
import requests
import time

def fetch_all_taifex_vix(start_year=2015, end_year=None):
    if end_year is None:
        end_year = pd.Timestamp.now().year

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    all_data = []

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == end_year and month > pd.Timestamp.now().month:
                break

            month_str = f"{year}{str(month).zfill(2)}"
            url = f"https://www.taifex.com.tw/file/taifex/Dailydownload/vix/log2data_eng/{month_str}new.txt"

            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    print(f"  {year}/{month:02d}: HTTP {resp.status_code} (skipped)")
                    continue

                lines = resp.text.strip().split('\n')
                count = 0
                for line in lines:
                    if not line.strip() or 'Date' in line or '---' in line:
                        continue
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    if len(parts) >= 3:
                        try:
                            date_obj = pd.to_datetime(parts[0], format='%Y%m%d')
                            vix_val = float(parts[2])
                            all_data.append({'Date': date_obj, 'IVIXTWN': vix_val})
                            count += 1
                        except:
                            continue

                print(f"  {year}/{month:02d}: {count} rows")
                time.sleep(0.3)  # be polite

            except Exception as e:
                print(f"  {year}/{month:02d}: error - {e}")

    if not all_data:
        print("No data collected.")
        return

    df = pd.DataFrame(all_data)
    df = df.set_index('Date')
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='first')]

    output_file = 'taiwan_vix_historical.csv'
    df.to_csv(output_file)
    print(f"\nSaved {len(df)} rows to {output_file}")
    print(f"Date range: {df.index.min().date()} to {df.index.max().date()}")
    print(df.tail())

if __name__ == '__main__':
    print("Fetching Taiwan VIX (VIXTWN) historical data from TAIFEX...")
    fetch_all_taifex_vix(start_year=2015)
