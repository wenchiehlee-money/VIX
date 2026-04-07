import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# Configuration
csv_file = "global_vix_merged.csv"
event_file = "raw_event_historical_crashes.csv"
output_html = "index.html"
years_back = 5

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

def plot_vix_interactive(df_vix):
    """Create interactive chart: 580px height, 85:15 Main:Slider ratio, 100% height overlaid VIX/TAIEX."""
    if df_vix.empty:
        print("No VIX data to plot.")
        return

    # Filter for last 5 years
    end_date = df_vix.index.max()
    start_date = end_date - timedelta(days=years_back * 365)
    df_vix = df_vix.loc[start_date:end_date]

    # Fetch TAIEX data
    df_taiex = get_taiex_data(start_date - timedelta(days=5), end_date + timedelta(days=1))
    
    # Merge
    df = df_vix.join(df_taiex, how='left')
    df = df.ffill()

    # Create figure with secondary Y-axis (Overlaid mode)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Add TAIEX (Secondary Y-axis, 100% height)
    if 'TAIEX' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['TAIEX'], name="TAIEX (台股指數)",
                line=dict(color='rgba(31, 119, 180, 0.4)', width=1.5),
                fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.05)',
                hovertemplate='TAIEX: %{y:,.0f}<extra></extra>'
            ),
            secondary_y=True,
        )

    # 2. Add VIX lines (Primary Y-axis, 100% height)
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

    fig.write_html(output_html, include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    print(f"Interactive chart (580px, 85:15 ratio, 100% overlay) saved to {output_html}")

if __name__ == "__main__":
    df_vix = get_vix_data()
    plot_vix_interactive(df_vix)
