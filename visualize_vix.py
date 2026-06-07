import pandas as pd
import matplotlib.pyplot as plt
import os
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib
import platform

# Configure Chinese font support
def setup_font():
    matplotlib.rcParams['svg.fonttype'] = 'path'  # Render text as paths for consistent SVG display
    matplotlib.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
    
    # Try to manually add common Linux CJK fonts if on Linux
    if platform.system() == 'Linux':
        try:
            from matplotlib import font_manager
            possible_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK.ttc',
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttf'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        font_manager.fontManager.addfont(path)
                        print(f"Manually added font from path: {path}")
                    except Exception as ae:
                        print(f"Failed to add font {path}: {ae}")
        except Exception as fe:
            print(f"Error loading system fonts: {fe}")
            
    # Comprehensive list of Traditional Chinese fonts across platforms
    tc_fonts = [
        'Microsoft JhengHei', 'Microsoft YaHei', 
        'Noto Sans CJK TC', 'Noto Sans TC', 
        'PingFang TC', 'Heiti TC', 'STHeiti',
        'WenQuanYi Micro Hei', 'Arial Unicode MS', 'Droid Sans Fallback'
    ]
    
    # Try to identify available fonts from the list
    try:
        from matplotlib import font_manager
        available_fonts = {f.name for f in font_manager.fontManager.ttflist}
        
        # Filter the list to only include fonts that actually exist in the system
        valid_fonts = [f for f in tc_fonts if f in available_fonts]
        
        if valid_fonts:
            matplotlib.rcParams['font.sans-serif'] = valid_fonts + ['sans-serif']
            print(f"Selected fonts for CJK: {valid_fonts[0]} (Available: {len(valid_fonts)})")
        else:
            # Fallback if none of our preferred fonts are found
            if platform.system() == 'Linux':
                matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
            elif platform.system() == 'Windows':
                matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
            else:
                matplotlib.rcParams['font.sans-serif'] = ['Heiti TC', 'PingFang TC', 'Arial Unicode MS']
            print("Warning: No preferred Traditional Chinese fonts found in fontManager. Falling back to defaults.")
    except Exception as e:
        print(f"Error during font setup: {e}")
        # Default fallback
        matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'sans-serif']

setup_font()

# Configuration
csv_file = "raw_vix_merged.csv"
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

    # Define numeric VIX columns for plotting and max calculation
    vix_cols = [col for col in df_filtered.columns if col in styles]
    
    for col in df_filtered.columns:
        if col in styles:
            # Increase linewidth to 2.5 for better visibility
            styles[col]['linewidth'] = 2.5
            plt.plot(df_filtered.index, df_filtered[col], **styles[col])
        elif col == 'CNN_FG':
            # Base line: orange dotted
            plt.plot(df_filtered.index, df_filtered[col], label='CNN Fear & Greed', color='orange', linewidth=1, linestyle=':', alpha=0.7)
            # Highlight line: Red and Bold continuous line for 0-25 and 75-100
            cnn_fg = df_filtered[col]
            cnn_high = cnn_fg.copy()
            cnn_high[(cnn_high > 25) & (cnn_high < 75)] = float('nan')
            plt.plot(df_filtered.index, cnn_high, color='red', linewidth=3, linestyle='-', label='_nolegend_', marker='o', markersize=3, alpha=0.9)
        # Skip timestamp columns
        elif 'timestamp' in col.lower():
            continue
        else:
            plt.plot(df_filtered.index, df_filtered[col], label=col, linewidth=2.5)

    plt.title(f'全球 VIX 指數趨勢 (最近 {years_back} 年)', fontsize=20, pad=25)
    plt.xlabel('日期', fontsize=14)
    plt.ylabel('VIX 指數值', fontsize=14)
    
    # Set Y-axis limits to make charts look good but capture spikes
    # Only use numeric VIX columns for max calculation to avoid errors with strings
    numeric_df = df_filtered.select_dtypes(include=['number'])
    if not numeric_df.empty:
        max_val = numeric_df.max().max()
        plt.ylim(0, max(45, max_val * 1.1)) 
    else:
        plt.ylim(0, 45)

    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Place legend in a good spot
    plt.legend(loc='upper left', fontsize=11, framealpha=0.9, ncol=2)
    
    plt.tight_layout()

    # Save as SVG (vector format for perfect quality at any size)
    plt.savefig(output_image, format='svg', bbox_inches='tight')
    print(f"Chart saved to {output_image} (SVG vector format)")

    # Ensure SVG has XML declaration with UTF-8 encoding to prevent rendering/encoding issues
    try:
        with open(output_image, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        if not svg_content.strip().startswith('<?xml'):
            svg_content = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n' + svg_content
            with open(output_image, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print("Added XML UTF-8 declaration to SVG file.")
    except Exception as e:
        print(f"Warning: Could not add XML declaration to SVG: {e}")

if __name__ == "__main__":
    df = get_data()
    plot_vix(df)
