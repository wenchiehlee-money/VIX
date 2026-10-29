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
  
  <!-- 幾何黑天鵝 SVG & PNG Favicon (Vecteezy 70781740) -->
  <link rel="icon" type="image/svg+xml" href="./favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="./favicon.png">
  
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
  <!-- Global site tag (gtag.js) - Google Analytics 4 -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-913Z6DSVD2"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-913Z6DSVD2');
  </script>
  </style>
</head>
<body>
  <div class="vix-page-wrapper">
    <!-- Obsidian Dark 品牌導航列 -->
    <header class="vix-header-bar">
      <div class="vix-brand-box">
        <svg class="vix-brand-logo" viewBox="0 0 24 24" fill="#ef4444" fill-rule="evenodd">
          <path d="M 16.80 15.66 C 16.88 15.57, 16.46 15.17, 16.19 14.95 C 15.91 14.73, 15.39 14.47, 15.13 14.33 C 14.86 14.20, 14.75 14.19, 14.60 14.16 C 14.45 14.13, 14.32 14.17, 14.25 14.16 C 14.17 14.14, 14.31 14.09, 14.16 14.07 C 14.01 14.06, 13.51 14.09, 13.37 14.07 C 13.22 14.06, 13.54 13.98, 13.28 13.98 C 13.01 13.98, 12.04 14.04, 11.78 14.07 C 11.52 14.10, 11.91 14.10, 11.69 14.16 C 11.47 14.22, 10.71 14.35, 10.46 14.42 C 10.21 14.50, 10.36 14.54, 10.19 14.60 C 10.03 14.66, 9.74 14.69, 9.49 14.78 C 9.24 14.86, 8.95 15.05, 8.70 15.13 C 8.45 15.20, 8.12 15.19, 7.99 15.22 C 7.86 15.25, 8.24 15.29, 7.90 15.30 C 7.57 15.32, 6.30 15.32, 5.96 15.30 C 5.63 15.29, 6.01 15.23, 5.88 15.22 C 5.74 15.20, 5.30 15.23, 5.17 15.22 C 5.04 15.20, 5.26 15.16, 5.08 15.13 C 4.91 15.10, 4.47 15.11, 4.11 15.04 C 3.76 14.97, 3.29 14.82, 2.97 14.69 C 2.65 14.56, 2.34 14.32, 2.18 14.25 C 2.01 14.17, 2.03 14.20, 2.00 14.25 C 1.97 14.29, 1.91 14.32, 2.00 14.51 C 2.09 14.70, 2.34 15.14, 2.53 15.39 C 2.72 15.64, 2.95 15.85, 3.15 16.01 C 3.34 16.17, 3.45 16.24, 3.67 16.36 C 3.89 16.48, 4.22 16.64, 4.47 16.71 C 4.72 16.79, 5.04 16.77, 5.17 16.80 C 5.30 16.83, 5.14 16.88, 5.26 16.89 C 5.38 16.90, 5.76 16.88, 5.88 16.89 C 5.99 16.90, 5.67 16.96, 5.96 16.98 C 6.26 16.99, 7.35 16.99, 7.64 16.98 C 7.93 16.96, 7.55 16.92, 7.73 16.89 C 7.90 16.86, 8.26 16.92, 8.70 16.80 C 9.14 16.68, 10.05 16.32, 10.37 16.19 C 10.69 16.05, 10.22 16.14, 10.63 16.01 C 11.05 15.88, 12.23 15.49, 12.84 15.39 C 13.44 15.29, 14.00 15.41, 14.25 15.39 C 14.50 15.38, 14.28 15.32, 14.33 15.30 C 14.39 15.29, 14.54 15.29, 14.60 15.30 C 14.66 15.32, 14.51 15.38, 14.69 15.39 C 14.86 15.41, 15.48 15.38, 15.66 15.39 C 15.83 15.41, 15.55 15.44, 15.74 15.48 C 15.94 15.52, 16.73 15.74, 16.80 15.66 Z M 3.06 8.61 C 3.01 8.86, 2.97 9.62, 2.97 9.84 C 2.97 10.06, 3.03 9.78, 3.06 9.93 C 3.09 10.08, 3.07 10.44, 3.15 10.72 C 3.22 11.00, 3.35 11.32, 3.50 11.60 C 3.64 11.88, 3.85 12.18, 4.03 12.40 C 4.20 12.62, 4.25 12.70, 4.56 12.93 C 4.86 13.15, 5.55 13.56, 5.88 13.72 C 6.20 13.88, 6.33 13.86, 6.49 13.89 C 6.65 13.92, 6.77 13.88, 6.85 13.89 C 6.92 13.91, 6.79 13.97, 6.93 13.98 C 7.08 14.00, 7.58 14.00, 7.73 13.98 C 7.87 13.97, 7.71 13.91, 7.81 13.89 C 7.92 13.88, 7.76 14.07, 8.34 13.89 C 8.93 13.72, 10.66 13.03, 11.34 12.84 C 12.01 12.65, 12.21 12.78, 12.40 12.75 C 12.59 12.72, 12.25 12.68, 12.48 12.66 C 12.72 12.65, 13.79 12.78, 13.81 12.66 C 13.82 12.54, 13.03 12.16, 12.57 11.96 C 12.12 11.75, 11.38 11.52, 11.07 11.43 C 10.77 11.34, 10.87 11.46, 10.72 11.43 C 10.58 11.40, 10.37 11.28, 10.19 11.25 C 10.02 11.22, 9.77 11.27, 9.67 11.25 C 9.56 11.24, 9.91 11.19, 9.58 11.16 C 9.24 11.13, 8.17 11.15, 7.64 11.07 C 7.11 11.00, 6.74 10.84, 6.41 10.72 C 6.07 10.60, 5.92 10.55, 5.61 10.37 C 5.30 10.19, 4.94 10.00, 4.56 9.67 C 4.17 9.33, 3.54 8.56, 3.32 8.34 C 3.10 8.12, 3.28 8.30, 3.23 8.34 C 3.19 8.39, 3.10 8.36, 3.06 8.61 Z M 18.92 2.44 C 18.67 2.26, 18.52 2.23, 18.30 2.18 C 18.08 2.12, 17.73 2.12, 17.59 2.09 C 17.46 2.06, 17.70 2.01, 17.51 2.00 C 17.32 1.99, 16.88 1.93, 16.45 2.00 C 16.02 2.07, 15.33 2.28, 14.95 2.44 C 14.57 2.60, 14.45 2.70, 14.16 2.97 C 13.86 3.23, 13.42 3.72, 13.19 4.03 C 12.95 4.33, 12.88 4.50, 12.75 4.82 C 12.62 5.14, 12.46 5.52, 12.40 5.96 C 12.34 6.41, 12.38 7.20, 12.40 7.46 C 12.41 7.73, 12.47 7.46, 12.48 7.55 C 12.50 7.64, 12.38 7.68, 12.48 7.99 C 12.59 8.30, 12.93 9.06, 13.10 9.40 C 13.28 9.74, 12.90 9.37, 13.54 10.02 C 14.19 10.66, 16.30 12.59, 16.98 13.28 C 17.65 13.97, 17.42 13.86, 17.59 14.16 C 17.77 14.45, 17.93 14.79, 18.04 15.04 C 18.14 15.29, 18.18 15.36, 18.21 15.66 C 18.24 15.95, 18.23 16.57, 18.21 16.80 C 18.20 17.04, 18.17 16.99, 18.12 17.07 C 18.08 17.14, 18.04 17.20, 17.95 17.24 C 17.86 17.29, 17.84 17.39, 17.59 17.33 C 17.35 17.27, 16.77 16.98, 16.45 16.89 C 16.13 16.80, 15.80 16.83, 15.66 16.80 C 15.51 16.77, 16.04 16.73, 15.57 16.71 C 15.10 16.70, 13.31 16.70, 12.84 16.71 C 12.37 16.73, 12.84 16.79, 12.75 16.80 C 12.66 16.82, 12.44 16.77, 12.31 16.80 C 12.18 16.83, 12.06 16.95, 11.96 16.98 C 11.85 17.01, 12.01 16.88, 11.69 16.98 C 11.37 17.08, 10.34 17.46, 10.02 17.59 C 9.69 17.73, 10.05 17.67, 9.75 17.77 C 9.46 17.87, 8.68 18.14, 8.26 18.21 C 7.83 18.28, 7.39 18.20, 7.20 18.21 C 7.01 18.23, 7.14 18.30, 7.11 18.30 C 7.08 18.30, 7.30 18.23, 7.02 18.21 C 6.74 18.20, 5.72 18.23, 5.44 18.21 C 5.16 18.20, 5.45 18.14, 5.35 18.12 C 5.25 18.11, 4.98 18.15, 4.82 18.12 C 4.66 18.09, 4.51 17.98, 4.38 17.95 C 4.25 17.92, 4.09 17.92, 4.03 17.95 C 3.97 17.98, 3.92 17.98, 4.03 18.12 C 4.13 18.27, 4.36 18.61, 4.64 18.83 C 4.92 19.05, 5.48 19.34, 5.70 19.44 C 5.92 19.55, 5.85 19.42, 5.96 19.44 C 6.08 19.47, 6.02 19.58, 6.41 19.62 C 6.79 19.67, 7.93 19.71, 8.26 19.71 C 8.58 19.71, 8.23 19.64, 8.34 19.62 C 8.46 19.61, 8.84 19.64, 8.96 19.62 C 9.08 19.61, 8.93 19.56, 9.05 19.53 C 9.17 19.50, 9.21 19.61, 9.67 19.44 C 10.12 19.28, 11.22 18.77, 11.78 18.56 C 12.34 18.36, 12.73 18.27, 13.01 18.21 C 13.29 18.15, 13.37 18.23, 13.45 18.21 C 13.54 18.20, 13.23 18.14, 13.54 18.12 C 13.85 18.11, 15.00 18.11, 15.30 18.12 C 15.61 18.14, 15.29 18.20, 15.39 18.21 C 15.49 18.23, 15.76 18.18, 15.92 18.21 C 16.08 18.24, 16.23 18.30, 16.36 18.39 C 16.49 18.48, 16.65 18.59, 16.71 18.74 C 16.77 18.89, 16.79 19.12, 16.71 19.27 C 16.64 19.42, 16.48 19.58, 16.27 19.62 C 16.07 19.67, 15.63 19.56, 15.48 19.53 C 15.33 19.50, 15.51 19.46, 15.39 19.44 C 15.27 19.43, 14.89 19.46, 14.78 19.44 C 14.66 19.43, 14.98 19.34, 14.69 19.36 C 14.39 19.37, 13.53 19.43, 13.01 19.53 C 12.50 19.64, 12.12 19.78, 11.60 19.97 C 11.09 20.16, 10.25 20.56, 9.93 20.68 C 9.61 20.80, 9.84 20.63, 9.67 20.68 C 9.49 20.72, 9.15 20.88, 8.87 20.94 C 8.59 21.00, 7.83 20.91, 7.99 21.03 C 8.15 21.15, 9.39 21.53, 9.84 21.65 C 10.30 21.77, 10.56 21.71, 10.72 21.74 C 10.88 21.77, 10.71 21.81, 10.81 21.82 C 10.91 21.84, 11.24 21.81, 11.34 21.82 C 11.44 21.84, 11.27 21.90, 11.43 21.91 C 11.59 21.93, 12.15 21.90, 12.31 21.91 C 12.47 21.93, 11.84 21.99, 12.40 22.00 C 12.95 22.01, 15.10 22.01, 15.66 22.00 C 16.21 21.99, 15.57 21.93, 15.74 21.91 C 15.92 21.90, 16.54 21.93, 16.71 21.91 C 16.89 21.90, 16.71 21.84, 16.80 21.82 C 16.89 21.81, 17.15 21.84, 17.24 21.82 C 17.33 21.81, 17.21 21.77, 17.33 21.74 C 17.45 21.71, 17.64 21.75, 17.95 21.65 C 18.26 21.54, 18.83 21.31, 19.18 21.12 C 19.53 20.93, 19.81 20.71, 20.06 20.50 C 20.31 20.30, 20.44 20.21, 20.68 19.89 C 20.91 19.56, 21.30 18.93, 21.47 18.56 C 21.65 18.20, 21.69 17.89, 21.74 17.68 C 21.78 17.48, 21.72 17.40, 21.74 17.33 C 21.75 17.26, 21.81 17.54, 21.82 17.24 C 21.84 16.95, 21.84 15.86, 21.82 15.57 C 21.81 15.27, 21.75 15.55, 21.74 15.48 C 21.72 15.41, 21.78 15.33, 21.74 15.13 C 21.69 14.92, 21.60 14.57, 21.47 14.25 C 21.34 13.92, 21.16 13.54, 20.94 13.19 C 20.72 12.84, 20.52 12.53, 20.15 12.13 C 19.78 11.74, 19.36 11.32, 18.74 10.81 C 18.12 10.30, 16.99 9.52, 16.45 9.05 C 15.91 8.58, 15.70 8.31, 15.48 7.99 C 15.26 7.67, 15.17 7.43, 15.13 7.11 C 15.08 6.79, 15.17 6.29, 15.22 6.05 C 15.26 5.82, 15.27 5.85, 15.39 5.70 C 15.51 5.55, 15.76 5.29, 15.92 5.17 C 16.08 5.05, 16.17 5.02, 16.36 5.00 C 16.55 4.97, 16.90 4.98, 17.07 5.00 C 17.23 5.01, 17.17 4.97, 17.33 5.08 C 17.49 5.20, 17.87 5.52, 18.04 5.70 C 18.20 5.88, 18.12 5.67, 18.30 6.14 C 18.48 6.61, 18.92 8.09, 19.09 8.52 C 19.27 8.95, 19.28 8.68, 19.36 8.70 C 19.43 8.71, 19.44 8.93, 19.53 8.61 C 19.62 8.28, 19.75 7.27, 19.89 6.76 C 20.02 6.24, 20.25 5.92, 20.33 5.52 C 20.40 5.13, 20.41 4.76, 20.33 4.38 C 20.24 4.00, 20.03 3.56, 19.80 3.23 C 19.56 2.91, 19.17 2.62, 18.92 2.44 Z M 18.74 3.85 C 18.83 3.85, 18.90 3.85, 19.00 3.94 C 19.11 4.03, 19.31 4.25, 19.36 4.38 C 19.40 4.51, 19.36 4.61, 19.27 4.73 C 19.18 4.85, 18.96 5.04, 18.83 5.08 C 18.70 5.13, 18.59 5.08, 18.48 5.00 C 18.36 4.91, 18.17 4.69, 18.12 4.56 C 18.08 4.42, 18.15 4.31, 18.21 4.20 C 18.27 4.10, 18.39 4.00, 18.48 3.94 C 18.56 3.88, 18.65 3.85, 18.74 3.85 Z"/>
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
