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
output_image = "vix_chart.png"
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

    # Filter for last 2 years
    end_date = df.index.max()
    start_date = end_date - timedelta(days=years_back * 365)
    df_filtered = df.loc[start_date:end_date]

    if df_filtered.empty:
        print("No data in the last 2 years.")
        return

    # Plotting - increased figure size for better clarity
    plt.figure(figsize=(16, 8), dpi=150)  # Higher DPI for sharper image
    
    # Define styles for each known column
    styles = {
        'US_VIX': {'color': 'blue', 'label': 'US VIX (^VIX)', 'linewidth': 1.5},
        'Japan_VIX': {'color': 'red', 'label': 'Japan VIX (Nikkei VI)', 'linewidth': 1.5, 'linestyle': '--'},
        'Taiwan_VIX': {'color': 'green', 'label': 'Taiwan VIX (VIXTWN)', 'linewidth': 1.5}
    }

    # Add Risk Zones (Background Color Bands)
    # Note: alpha controls transparency
    plt.axhspan(0, 15, facecolor='green', alpha=0.1, label='Safe (<15)')
    plt.axhspan(15, 20, facecolor='yellow', alpha=0.15, label='Warning (15-20)')
    plt.axhspan(20, 30, facecolor='orange', alpha=0.15, label='Dangerous (20-30)')
    plt.axhspan(30, 100, facecolor='red', alpha=0.1, label='Very Dangerous (>30)')

    # Add Bold Threshold Line for Very Dangerous
    plt.axhline(y=30, color='darkred', linewidth=3, linestyle='--', alpha=0.8)
    plt.text(df_filtered.index.min(), 30.5, ' VERY DANGEROUS THRESHOLD', color='darkred', fontsize=10, fontweight='bold', va='bottom')

    # Add 'Today' indicator
    latest_date = df_filtered.index.max()
    plt.axvline(x=latest_date, color='gray', linestyle=':', linewidth=2, label='Today')

    for col in df_filtered.columns:
        if col in styles:
            # Increase linewidth to 2.0 for better visibility
            styles[col]['linewidth'] = 2.0
            plt.plot(df_filtered.index, df_filtered[col], **styles[col])
        else:
            plt.plot(df_filtered.index, df_filtered[col], label=col, linewidth=2.0)

    plt.title(f'VIX Indices (Last {years_back} Years)', fontsize=16, pad=20)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('VIX Value', fontsize=12)
    
    # Set Y-axis limits to make charts look good but capture spikes
    max_val = df_filtered.max().max()
    plt.ylim(0, max(40, max_val * 1.1)) # At least go up to 40 to show the red zone start

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Place legend outside or in a good spot
    plt.legend(loc='upper left', fontsize=10, framealpha=0.8)
    
    plt.tight_layout()

    # Save with high resolution
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"Chart saved to {output_image} (high resolution)")

if __name__ == "__main__":
    df = get_data()
    plot_vix(df)
