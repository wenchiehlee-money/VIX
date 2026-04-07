import pandas as pd
import matplotlib.pyplot as plt
import os
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib
import platform

# Configure Chinese font support
if platform.system() == 'Windows':
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
elif platform.system() == 'Linux':
    matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'Arial Unicode MS']
else:  # macOS
    matplotlib.rcParams['font.sans-serif'] = ['Heiti TC', 'PingFang TC', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False  # Fix minus sign display

# Configuration
csv_file = "global_vix_merged.csv"
output_image = "vix_chart.svg"
years_back = 2

def get_data():
    # 1. Try to load merged CSV
    if os.path.exists(csv_file):
        print(f"Loading data from {csv_file}...")
        try:
            df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
            return df
        except Exception as e:
            print(f"Error reading CSV: {e}")
    
    # 2. Fallback: Fetch US VIX directly if CSV is missing or broken
    print("CSV not found or unreadable. Fetching fresh US VIX data...")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365 + 30) # Buffer
        vix = yf.Ticker("^VIX")
        df = vix.history(start=start_date, end=end_date)
        df = df[['Close']].rename(columns={'Close': 'US_VIX'})
        return df
    except Exception as e:
        print(f"Error fetching US VIX: {e}")
        return pd.DataFrame()

def plot_vix(df):
    if df.empty:
        print("No data to plot.")
        return

    # Filter for last 5 years
    end_date = df.index.max()
    start_date = end_date - timedelta(days=years_back * 365)
    df_filtered = df.loc[start_date:end_date]

    if df_filtered.empty:
        print("No data in the last 5 years.")
        return

    # Plotting - increased figure size for better clarity
    plt.figure(figsize=(16, 8), dpi=150)  # Higher DPI for sharper image
    
    # Define styles for each known column
    styles = {
        'US_VIX': {'color': 'blue', 'label': 'US VIX (^VIX)', 'linewidth': 1.5},
        'Japan_VIX': {'color': 'red', 'label': 'Japan VIX (Nikkei VI)', 'linewidth': 1.5, 'linestyle': '--'},
        'Taiwan_VIX': {'color': 'green', 'label': 'Taiwan VIX (VIXTWN)', 'linewidth': 1.5}
    }

    # Add Risk Zones (Background Color Bands) matching the JPG reference image
    # 0-15: 平穩 (Greenish)
    plt.axhspan(0, 15, facecolor='#66A36E', alpha=0.15, label='0-15 平穩')
    # 15-20: 溫和波動 (Light Green)
    plt.axhspan(15, 20, facecolor='#ABD398', alpha=0.2, label='15-20 溫和波動')
    # 20-25: 市場關注 (Yellow)
    plt.axhspan(20, 25, facecolor='#F9E79F', alpha=0.25, label='20-25 市場關注')
    # 25-30: 市場動盪 (Orange)
    plt.axhspan(25, 30, facecolor='#F5B074', alpha=0.25, label='25-30 市場動盪')
    # >30: 加重動盪 (Reddish)
    plt.axhspan(30, 100, facecolor='#EC7063', alpha=0.2, label='>30 加重動盪')

    # Add Bold Threshold Line for Panic Level
    plt.axhline(y=30, color='darkred', linewidth=3, linestyle='--', alpha=0.8)
    plt.text(df_filtered.index.min(), 30.5, ' 恐慌臨界點 (30)', color='darkred', fontsize=12, fontweight='bold', va='bottom')

    # Add 'Today' indicator
    latest_date = df_filtered.index.max()
    plt.axvline(x=latest_date, color='gray', linestyle=':', linewidth=2, label='最新數據')

    for col in df_filtered.columns:
        if col in styles:
            # Increase linewidth to 2.5 for better visibility
            styles[col]['linewidth'] = 2.5
            plt.plot(df_filtered.index, df_filtered[col], **styles[col])
        else:
            plt.plot(df_filtered.index, df_filtered[col], label=col, linewidth=2.5)

    plt.title(f'全球 VIX 指數趨勢 (最近 {years_back} 年)', fontsize=20, pad=25)
    plt.xlabel('日期', fontsize=14)
    plt.ylabel('VIX 指數值', fontsize=14)
    
    # Set Y-axis limits to make charts look good but capture spikes
    max_val = df_filtered.max().max()
    plt.ylim(0, max(45, max_val * 1.1)) 

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Place legend in a good spot
    plt.legend(loc='upper left', fontsize=11, framealpha=0.9, ncol=2)
    
    plt.tight_layout()

    # Save as SVG (vector format for perfect quality at any size)
    plt.savefig(output_image, format='svg', bbox_inches='tight')
    print(f"Chart saved to {output_image} (SVG vector format)")

if __name__ == "__main__":
    df = get_data()
    plot_vix(df)
