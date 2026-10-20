import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# Configuration
csv_file = "raw_vix_merged.csv"
event_file = "raw_event_historical_crashes.csv"
output_html = "index.html"
years_back = 40  # Increased to show full historical range from 1990 onwards

def get_vix_data():
    """Load VIX data from CSV file."""
    if os.path.exists(csv_file):
        print(f"Loading data from {csv_file}...")
        try:
            df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
            return df
        except Exception as e:
            print(f"Error reading CSV: {e}")
    return pd.DataFrame()

def get_event_data():
    """Load historical crash events from CSV."""
    if os.path.exists(event_file):
        print(f"Loading events from {event_file}...")
        try:
            try:
                df = pd.read_csv(event_file, encoding='utf-8-sig')
            except:
                df = pd.read_csv(event_file, encoding='utf-8')
            
            # Clean up the date columns - remove extra quotes and spaces
            for col in ['開始日期', '結束日期']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('"', '').str.strip()
            
            df['開始日期'] = pd.to_datetime(df['開始日期'], errors='coerce')
            df['結束日期'] = pd.to_datetime(df['結束日期'], errors='coerce')
            df = df.dropna(subset=['開始日期'])
            df['結束日期'] = df['結束日期'].fillna(df['開始日期'] + pd.Timedelta(days=3))
            return df
        except Exception as e:
            print(f"Error reading events CSV: {e}")
    return pd.DataFrame()

def get_taiex_data(start_date, end_date):
    """Fetch TAIEX (^TWII) data from yfinance."""
    print(f"Fetching TAIEX (^TWII) data from {start_date.date()} to {end_date.date()}...")
    try:
        taiex = yf.download("^TWII", start=start_date, end=end_date)
        if not taiex.empty:
            if isinstance(taiex.columns, pd.MultiIndex):
                taiex.columns = taiex.columns.get_level_values(0)
            return taiex[['Close']].rename(columns={'Close': 'TAIEX'})
    except Exception as e:
        print(f"Error fetching TAIEX: {e}")
    return pd.DataFrame()

def get_cnn_fg_data():
    """Load CNN Fear & Greed data from CSV."""
    if os.path.exists("cnn_fear_greed.csv"):
        print("Loading CNN Fear & Greed data...")
        try:
            df = pd.read_csv("cnn_fear_greed.csv", index_col='Date', parse_dates=True)
            return df[['Fear_Greed_Value']].rename(columns={'Fear_Greed_Value': 'CNN_FG'})
        except Exception as e:
            print(f"Error reading CNN CSV: {e}")
    return pd.DataFrame()

def plot_vix_interactive(df_vix):
    """Create interactive chart: 580px height, 85:15 Main:Slider ratio, 100% height overlaid VIX/TAIEX/CNN."""
    if df_vix.empty:
        print("No VIX data to plot.")
        return

    # Filter for requested range (Start from 2010 as per user request)
    end_date = df_vix.index.max()
    start_date = datetime(2010, 1, 1)
    
    # Create a full date range for the requested period
    full_range = pd.date_range(start=start_date, end=end_date, freq='D')
    df_base = pd.DataFrame(index=full_range)
    df_base.index.name = 'Date'

    # Filter VIX data
    df_vix = df_vix.loc[df_vix.index >= start_date]

    # Fetch TAIEX data
    df_taiex = get_taiex_data(start_date - timedelta(days=5), end_date + timedelta(days=1))
    
    # Fetch CNN data
    df_cnn = get_cnn_fg_data()

    # Merge: base range + VIX + TAIEX
    df = df_base.join(df_vix, how='left').join(df_taiex, how='left')
    
    # Join CNN data only if it's not already in df_vix (to avoid overlap error)
    if not df_cnn.empty:
        if 'CNN_FG' not in df.columns:
            df = df.join(df_cnn, how='left')
        else:
            # Update missing CNN_FG values if any, or just skip if already present
            df['CNN_FG'] = df['CNN_FG'].fillna(df_cnn['CNN_FG'])

    df = df.ffill() # Forward fill to handle weekends/holidays

    # Drop rows where we have NO data to keep chart clean
    available_cols = [c for c in ['US_VIX', 'Taiwan_VIX', 'Japan_VIX', 'TAIEX', 'CNN_FG'] if c in df.columns]
    df = df.dropna(subset=available_cols, how='all')

    # Create figure with secondary Y-axis (Overlaid mode)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Add TAIEX (Secondary Y-axis, 100% height)
    if 'TAIEX' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['TAIEX'], name="TAIEX (台股指數)",
                line=dict(color='rgba(31, 119, 180, 0.3)', width=1),
                fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.05)',
                hovertemplate='TAIEX: %{y:,.0f}<extra></extra>'
            ),
            secondary_y=True,
        )

    # 2. Add CNN Fear & Greed (Secondary Y-axis, but scaled to index 0-100)
    # We use secondary Y-axis for CNN as well, but TAIEX is also there.
    # To avoid visual clutter, CNN will have its own Y-axis range if possible, 
    # but Plotly standard secondary_y only allows one.
    # We will share secondary_y with TAIEX but CNN is 0-100.
    if 'CNN_FG' in df.columns:
        # Base line: orange dotted
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['CNN_FG'], name="CNN Fear & Greed (美股情緒)",
                line=dict(color='orange', width=1.5, dash='dot'),
                hovertemplate='CNN FG: %{y:.1f}<extra></extra>',
                visible='legendonly', # Start hidden to avoid clutter, user can enable
                legendgroup='CNN_FG'
            ),
            secondary_y=False, # Put on primary Y-axis (0-100) same as VIX
        )
        
        # Highlight line: Red and Bold continuous line for 0-25 and 75-100
        cnn_fg = df['CNN_FG']
        cnn_high = cnn_fg.copy()
        cnn_high[(cnn_high > 25) & (cnn_high < 75)] = float('nan')
        
        fig.add_trace(
            go.Scatter(
                x=df.index, y=cnn_high, name="CNN FG 極端值",
                line=dict(color='red', width=3, dash='solid'),
                mode='lines+markers',
                marker=dict(size=4, color='red'),
                hovertemplate='CNN FG: %{y:.1f}<extra></extra>',
                visible='legendonly',
                legendgroup='CNN_FG',
                showlegend=False  # Hide this second trace from the legend panel
            ),
            secondary_y=False,
        )

    # 3. Add VIX lines (Primary Y-axis, 100% height)
    line_configs = {
        'Taiwan_VIX': {'color': '#00A86B', 'name': 'Taiwan VIX (台指 VIX)', 'width': 1.5, 'dash': 'solid'},
        'US_VIX': {'color': 'red', 'name': 'US VIX (標普 VIX)', 'width': 1.5, 'dash': 'solid'},
        'Japan_VIX': {'color': '#7f7f7f', 'name': 'Japan VIX (日經 VI)', 'width': 1.5, 'dash': 'dash'}
    }

    for col, config in line_configs.items():
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=df[col], name=config['name'],
                    line=dict(color=config['color'], width=config['width'], dash=config.get('dash', 'solid')),
                    hovertemplate='%{y:.2f}<extra></extra>'
                ),
                secondary_y=False,
            )

    # 3. Risk Zones (Matching the 5 categories from reference image)
    # 0-15: 平穩 (#66A36E)
    fig.add_hrect(y0=0, y1=15, fillcolor="#66A36E", opacity=0.1, layer="below", line_width=0, secondary_y=False)
    # 15-20: 溫和波動 (#ABD398)
    fig.add_hrect(y0=15, y1=20, fillcolor="#ABD398", opacity=0.12, layer="below", line_width=0, secondary_y=False)
    # 20-25: 市場關注 (#F9E79F)
    fig.add_hrect(y0=20, y1=25, fillcolor="#F9E79F", opacity=0.15, layer="below", line_width=0, secondary_y=False)
    # 25-30: 市場動盪 (#F5B074)
    fig.add_hrect(y0=25, y1=30, fillcolor="#F5B074", opacity=0.15, layer="below", line_width=0, secondary_y=False)
    # >30: 加重動盪 (#EC7063)
    fig.add_hrect(y0=30, y1=100, fillcolor="#EC7063", opacity=0.12, layer="below", line_width=0, secondary_y=False)
    
    # Panic Level Line
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(200, 0, 0, 0.6)", line_width=2, 
                  annotation_text="恐慌臨界點 (30)", annotation_position="top left", secondary_y=False)

    # 4. Historical Events
    df_events = get_event_data()
    event_annotations = []
    if not df_events.empty:
        mask = (df_events['開始日期'] >= start_date) & (df_events['開始日期'] <= end_date)
        df_plot_events = df_events.loc[mask].sort_values('開始日期')
        
        cat_colors = {
            '金融危機': '#9467bd', '地緣政治': '#d62728', '政策衝擊': '#ff7f0e',
            '公共衛生': '#2ca02c', '自然災害': '#17becf'
        }

        for i, (_, event) in enumerate(df_plot_events.iterrows()):
            s_date = event['開始日期']
            e_date = event['結束日期']
            event_name = event['事件名稱']
            event_note = event.get('備註', '')
            event_cat = event.get('類別', '其他')
            color = cat_colors.get(event_cat, 'gray')
            
            fig.add_vrect(
                x0=s_date, x1=e_date, fillcolor=color, opacity=0.15,
                layer="below", line_width=0
            )
            
            h_text = f"<b>{event_name}</b> ({event_cat})<br>期間: {s_date.date()} ~ {e_date.date()}<br>{event_note}"

            event_annotations.append(dict(
                x=s_date, y=1.0, yref='paper',
                text="🚩", showarrow=False, xanchor='left',
                font=dict(size=16, color=color),
                bgcolor="rgba(255, 255, 255, 0.5)",
                hovertext=h_text
            ))

    # Calculate max VIX
    existing_vix_cols = [col for col in line_configs.keys() if col in df.columns]
    max_vix = 45
    if existing_vix_cols:
        current_max = df[existing_vix_cols].max().max()
        if not pd.isna(current_max):
            max_vix = max(45, current_max * 1.1)

    # Get current time
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S')

    # Footer
    footer_ann = dict(
        text=f"更新時間: {timestamp} (CST) | 來源: TAIFEX, Yahoo Finance",
        showarrow=False, xref="paper", yref="paper", x=1, y=-0.15, font=dict(size=10, color="gray")
    )

    # 5. Layout
    fig.update_layout(
        title=dict(text='<b>Taiwan VIX vs TAIEX 走勢對照圖</b>', x=0.5, y=0.96, font=dict(size=20, color='#333')),
        template='plotly_white', hovermode='x unified', 
        height=580, # FIXED HEIGHT 580px
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=60),
        annotations=event_annotations + [footer_ann]
    )

    fig.update_xaxes(
        title='日期', showgrid=True, gridcolor='#f0f0f0',
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(step="all", label="全部")
            ]),
            font=dict(size=11), bgcolor="white", activecolor="#e6f2ff"
        ),
        # Range Slider Ratio (85:15 means thickness should be ~0.15)
        rangeslider=dict(visible=True, thickness=0.15)
    )

    # 100% Height Overlay configuration
    fig.update_yaxes(title_text="VIX 指數", range=[0, max_vix], gridcolor='#f0f0f0', secondary_y=False)
    fig.update_yaxes(title_text="TAIEX 指數", showgrid=False, secondary_y=True)

        # Extract latest metrics for KPI strip
    latest_us_vix = 18.11
    latest_tw_vix = 26.37
    latest_cnn_fg = 24.94
    cnn_rating = "Extreme Fear"

    try:
        if 'US_VIX' in df.columns:
            valid_us = df['US_VIX'].dropna()
            if not valid_us.empty:
                latest_us_vix = float(valid_us.iloc[-1])
        if 'Taiwan_VIX' in df.columns:
            valid_tw = df['Taiwan_VIX'].dropna()
            if not valid_tw.empty:
                latest_tw_vix = float(valid_tw.iloc[-1])
        if os.path.exists('cnn_fear_greed.csv'):
            df_cnn_tmp = pd.read_csv('cnn_fear_greed.csv')
            if 'Fear_Greed_Value' in df_cnn_tmp.columns and not df_cnn_tmp.empty:
                latest_cnn_fg = float(df_cnn_tmp['Fear_Greed_Value'].dropna().iloc[-1])
            if 'Rating' in df_cnn_tmp.columns and not df_cnn_tmp.empty:
                cnn_rating = str(df_cnn_tmp['Rating'].dropna().iloc[-1])
    except Exception as e:
        print(f"Warning calculating KPI values: {e}")

    # Pointer position bounded between 0 and 100
    gauge_pointer_pct = max(2.0, min(98.0, latest_cnn_fg))

    chart_div = fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False, 'responsive': True})

    vix_full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Taiwan VIX vs TAIEX · 全球波動率雷達 (VIX Radar)</title>
  
  <!-- 幾何黑天鵝 SVG Favicon (Vecteezy 70781740) -->
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ef4444'%3E%3Cpath d='M 19.87 10.29 C 18.53 10.90, 16.41 10.68, 15.61 11.02 C 14.82 11.36, 13.62 12.66, 13.20 13.04 C 12.59 17.63, 11.47 15.05, 11.36 15.50 C 10.52 14.66, 9.22 11.32, 8.44 11.02 C 5.87 11.92, 9.96 13.48, 9.62 14.49 C 10.63 18.13, 12.14 18.86, 13.99 17.85 C 15.89 11.92, 18.86 11.64, 19.87 10.29 Z'/%3E%3C/svg%3E">
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700;800&family=Noto+Sans+TC:wght@400;600;700&display=swap" rel="stylesheet">
  
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      background: #f8fafc;
      color: #0f172a;
      font-family: 'Inter', 'Noto Sans TC', sans-serif;
      margin: 0;
      padding: 24px 20px;
      -webkit-font-smoothing: antialiased;
    }}
    .vix-page-wrapper {{
      max-width: 1440px;
      margin: 0 auto;
    }}
    .vix-header-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 14px;
      background: #0f172a;
      padding: 16px 24px;
      border-radius: 14px;
      margin-bottom: 20px;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.12);
      border: 1px solid #1e293b;
    }}
    .vix-brand-box {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .vix-brand-logo {{
      width: 32px;
      height: 32px;
      fill: #ef4444;
      filter: drop-shadow(0 0 10px rgba(239, 68, 68, 0.65));
      flex-shrink: 0;
    }}
    .vix-site-title {{
      font-size: 1.2rem;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.01em;
      margin: 0;
    }}
    .vix-site-desc {{
      font-size: 0.78rem;
      color: #94a3b8;
      margin-top: 3px;
    }}
    .vix-sync-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.74rem;
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 4px 10px;
      border-radius: 9999px;
    }}
    .vix-deck-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #ffffff;
      color: #0284c7;
      text-decoration: none;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 6px 16px;
      border-radius: 9999px;
      transition: all 0.2s ease;
      box-shadow: 0 2px 6px rgba(0,0,0,0.08);
      border: 1px solid #bae6fd;
    }}
    .vix-deck-btn:hover {{
      background: #f0f9ff;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.15);
    }}
    .vix-kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }}
    .vix-kpi-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 14px 18px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .vix-kpi-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .vix-kpi-title {{
      font-size: 0.76rem;
      color: #64748b;
      font-weight: 700;
      letter-spacing: 0.03em;
    }}
    .vix-kpi-val {{
      font-size: 1.85rem;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      line-height: 1.15;
    }}
    .vix-kpi-desc {{
      font-size: 0.74rem;
      font-weight: 600;
    }}
    .vix-chart-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 18px 16px;
      box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
      overflow: hidden;
    }}

    /* VIX Gauge / Scale Bar */
    .vix-gauge-box {{
      background: #0f172a;
      border-radius: 14px;
      padding: 1.25rem 1.35rem;
      color: #ffffff;
      margin-top: 20px;
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
      border: 1px solid #1e293b;
    }}
    .vix-gauge-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .vix-gauge-bar {{
      height: 10px;
      border-radius: 9999px;
      background: linear-gradient(90deg, #ef4444 0%, #f97316 25%, #38bdf8 50%, #eab308 75%, #10b981 100%);
      position: relative;
      margin-bottom: 8px;
    }}
    .vix-gauge-pointer {{
      position: absolute;
      top: -3px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #ffffff;
      border: 3px solid #ef4444;
      box-shadow: 0 0 10px #ef4444;
      transform: translateX(-50%);
    }}
    .vix-scale-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      font-family: "JetBrains Mono", monospace;
      color: #94a3b8;
    }}

    /* Historical Crash Events Timeline */
    .vix-events-section {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 18px 20px;
      box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
      margin-top: 20px;
    }}
    .vix-events-header {{
      font-size: 0.95rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .vix-events-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }}
    .vix-event-card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-left: 4px solid #ef4444;
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 0.8rem;
      transition: all 0.2s ease;
    }}
    .vix-event-card:hover {{
      border-color: #cbd5e1;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
    }}
    .vix-event-date {{
      color: #ef4444;
      font-weight: 800;
      font-family: "JetBrains Mono", monospace;
      font-size: 0.75rem;
    }}
    .vix-event-title {{
      font-weight: 800;
      color: #0f172a;
      margin: 3px 0 2px;
      font-size: 0.88rem;
    }}
    .vix-event-stat {{
      color: #64748b;
      font-size: 0.76rem;
      line-height: 1.4;
    }}

    .vix-footer {{
      margin-top: 24px;
      text-align: center;
      font-size: 0.78rem;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <div class="vix-page-wrapper">
    <!-- Obsidian Dark 品牌導航列 -->
    <header class="vix-header-bar">
      <div class="vix-brand-box">
        <svg class="vix-brand-logo" viewBox="0 0 24 24">
          <path d="M 19.87 10.29 C 18.53 10.90, 16.41 10.68, 15.61 11.02 C 14.82 11.36, 13.62 12.66, 13.20 13.04 C 12.59 17.63, 11.47 15.05, 11.36 15.50 C 10.52 14.66, 9.22 11.32, 8.44 11.02 C 5.87 11.92, 9.96 13.48, 9.62 14.49 C 10.63 18.13, 12.14 18.86, 13.99 17.85 C 15.89 11.92, 18.86 11.64, 19.87 10.29 Z"/>
        </svg>
        <div>
          <h1 class="vix-site-title">Taiwan VIX vs TAIEX · 全球波動率雷達</h1>
          <div class="vix-site-desc">台美日波動率指標、CNN 恐懼與貪婪指數及黑天鵝崩盤回測</div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <span class="vix-sync-badge">● 每日收盤定時結算 (CST)</span>
        <a href="https://wenchiehlee-ux.github.io/UX-Deck/" target="_blank" rel="noopener noreferrer" class="vix-deck-btn" title="瀏覽全端點吉祥物與九大生態系統設計規範">
          🎨 返回 UX-Deck 總看板 ↗
        </a>
      </div>
    </header>

    <!-- 3 KPI Cards Strip -->
    <div class="vix-kpi-grid">
      <div class="vix-kpi-card" style="border-top: 3px solid #ef4444;">
        <div class="vix-kpi-header">
          <span class="vix-kpi-title">美股波動率 (US VIX)</span>
          <span style="font-size: 0.7rem; background: #fef2f2; color: #dc2626; padding: 2px 8px; border-radius: 9999px; font-weight: 700;">CBOE</span>
        </div>
        <div class="vix-kpi-val" style="color: #ef4444;">{latest_us_vix:.2f}</div>
        <div class="vix-kpi-desc" style="color: #059669;">🟢 溫和常態 · Normal Complacency</div>
      </div>

      <div class="vix-kpi-card" style="border-top: 3px solid #10b981;">
        <div class="vix-kpi-header">
          <span class="vix-kpi-title">台指波動率 (TAIWAN VIX)</span>
          <span style="font-size: 0.7rem; background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 9999px; font-weight: 700;">TAIFEX</span>
        </div>
        <div class="vix-kpi-val" style="color: #10b981;">{latest_tw_vix:.2f}</div>
        <div class="vix-kpi-desc" style="color: #ea580c;">🟠 市場關注 · Elevated Alert</div>
      </div>

      <div class="vix-kpi-card" style="border-top: 3px solid #0284c7;">
        <div class="vix-kpi-header">
          <span class="vix-kpi-title">CNN 恐懼與貪婪指數</span>
          <span style="font-size: 0.7rem; background: #f0f9ff; color: #0284c7; padding: 2px 8px; border-radius: 9999px; font-weight: 700;">CNN F&G</span>
        </div>
        <div class="vix-kpi-val" style="color: #0284c7;">{latest_cnn_fg:.2f}</div>
        <div class="vix-kpi-desc" style="color: #0369a1;">🔵 {cnn_rating}</div>
      </div>
    </div>

    <!-- Plotly Interactive Chart Container -->
    <main class="vix-chart-card">
      {chart_div}
    </main>

    <!-- 市場情緒光譜量尺 (Sentiment Spectrum Gauge) -->
    <div class="vix-gauge-box">
      <div class="vix-gauge-top">
        <span style="font-size: 0.86rem; font-weight: 700; color: #f1f5f9;">市場情緒光譜量尺 (Sentiment Spectrum Gauge)</span>
        <span style="font-size: 0.76rem; font-family: 'JetBrains Mono', monospace; color: #f97316;">當前指標位階：{latest_cnn_fg:.2f}% ({cnn_rating})</span>
      </div>
      <div class="vix-gauge-bar">
        <div class="vix-gauge-pointer" style="left: {gauge_pointer_pct:.2f}%;"></div>
      </div>
      <div class="vix-scale-labels">
        <span style="color: #ef4444;">0 極度恐慌 (&lt; 25)</span>
        <span style="color: #f97316;">25 恐慌 (25~45)</span>
        <span style="color: #38bdf8;">50 中立 (45~55)</span>
        <span style="color: #eab308;">75 貪婪 (55~75)</span>
        <span style="color: #10b981;">100 極度貪婪 (&gt; 75)</span>
      </div>
    </div>

    <!-- 歷史重大黑天鵝與崩盤回測事件 (Historical Crash Stress Tests) -->
    <section class="vix-events-section">
      <div class="vix-events-header">
        <span>🚨 歷史重大黑天鵝與崩盤回測事件 (Historical Crash Stress Tests)</span>
      </div>
      <div class="vix-events-row">
        <div class="vix-event-card">
          <div class="vix-event-date">2024-08-05</div>
          <div class="vix-event-title">805 日圓套利平倉股災</div>
          <div class="vix-event-stat">Taiwan VIX 飆升至 <strong>48.20</strong> · TAIEX 單日重挫 -1,807 點</div>
        </div>
        <div class="vix-event-card">
          <div class="vix-event-date">2020-03-19</div>
          <div class="vix-event-title">COVID-19 全球疫情熔斷</div>
          <div class="vix-event-stat">US VIX 飆破 <strong>82.69</strong> (歷史天量) · 全球流動性恐慌</div>
        </div>
        <div class="vix-event-card">
          <div class="vix-event-date">2018-02-06</div>
          <div class="vix-event-title">206 期貨選擇權雙向歸零</div>
          <div class="vix-event-stat">Taiwan VIX 單日跳漲 <strong>+14.5</strong> · 波動率產品清算</div>
        </div>
        <div class="vix-event-card">
          <div class="vix-event-date">2011-08-08</div>
          <div class="vix-event-title">美國主權債務降評事件</div>
          <div class="vix-event-stat">S&P 降評引發全球拋售 · US VIX 突破 <strong>48.00</strong></div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="vix-footer">
      UX-Deck 生態系家族端點 · 資料來源：TAIFEX (台灣期貨交易所) · Yahoo Finance · CNN Business
    </footer>
  </div>
</body>
</html>"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(vix_full_html)
    print(f"[UX-Deck] Standalone branded VIX dashboard successfully saved to {output_html}!")

if __name__ == "__main__":
    df_vix = get_vix_data()
    plot_vix_interactive(df_vix)
