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
            df = df.dropna(subset=['開始日期'])
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
    """Create professional interactive chart similar to MacroMicro."""
    if df_vix.empty:
        print("No VIX data to plot.")
        return

    # Filter for last 5 years
    end_date = df_vix.index.max()
    start_date = end_date - timedelta(days=years_back * 365)
    df_vix = df_vix.loc[start_date:end_date]

    # Fetch TAIEX data for the same period
    df_taiex = get_taiex_data(start_date - timedelta(days=5), end_date + timedelta(days=1))
    
    # Merge data
    df = df_vix.join(df_taiex, how='left')
    df = df.ffill()

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Add TAIEX as background (Secondary Y-axis)
    if 'TAIEX' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, 
                y=df['TAIEX'],
                name="TAIEX (台股加權指數)",
                line=dict(color='rgba(150, 150, 150, 0.4)', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(200, 200, 200, 0.1)',
                hovertemplate='TAIEX: %{y:,.0f}<extra></extra>'
            ),
            secondary_y=True,
        )

    # 2. Add Risk Zones (Primary Y-axis)
    fig.add_hrect(y0=0, y1=15, fillcolor="green", opacity=0.05, layer="below", line_width=0, secondary_y=False)
    fig.add_hrect(y0=20, y1=30, fillcolor="orange", opacity=0.08, layer="below", line_width=0, secondary_y=False)
    fig.add_hrect(y0=30, y1=100, fillcolor="red", opacity=0.08, layer="below", line_width=0, secondary_y=False)

    # 3. Add VIX lines (Primary Y-axis)
    line_configs = {
        'Taiwan_VIX': {'color': '#00A86B', 'name': 'Taiwan VIX (台指 VIX)', 'width': 2.5},
        'US_VIX': {'color': '#1f77b4', 'name': 'US VIX (標普 VIX)', 'width': 1.5, 'dash': 'dot'},
        'Japan_VIX': {'color': '#d62728', 'name': 'Japan VIX (日經 VI)', 'width': 1.5, 'dash': 'dash'}
    }

    for col, config in line_configs.items():
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    name=config['name'],
                    line=dict(
                        color=config['color'],
                        width=config['width'],
                        dash=config.get('dash', 'solid')
                    ),
                    hovertemplate='%{y:.2f}<extra></extra>'
                ),
                secondary_y=False,
            )

    # 4. Add threshold line at 30
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(200, 0, 0, 0.5)", line_width=1, secondary_y=False)

    # Calculate max VIX for scaling
    existing_vix_cols = [col for col in line_configs.keys() if col in df.columns]
    max_vix = 45
    if existing_vix_cols:
        current_max = df[existing_vix_cols].max().max()
        if not pd.isna(current_max):
            max_vix = max(45, current_max * 1.1)

    # 5. Add Historical Crash Events (Bold Vertical Labels)
    df_events = get_event_data()
    if not df_events.empty:
        mask = (df_events['開始日期'] >= start_date) & (df_events['開始日期'] <= end_date)
        df_plot_events = df_events.loc[mask].sort_values('開始日期')
        print(f"Plotting {len(df_plot_events)} events out of {len(df_events)} total events.")
        
        cat_colors = {
            '金融危機': '#9467bd', '地緣政治': '#d62728', '政策衝擊': '#ff7f0e',
            '公共衛生': '#2ca02c', '自然災害': '#17becf'
        }

        for i, (_, event) in enumerate(df_plot_events.iterrows()):
            event_date = event['開始日期']
            event_name = event['事件名稱']
            event_note = event.get('備註', '')
            event_cat = event.get('類別', '其他')
            color = cat_colors.get(event_cat, 'gray')
            
            # Thick colorful vertical line
            fig.add_vline(
                x=event_date, 
                line_width=3, 
                line_dash="dot", 
                line_color=color,
                opacity=0.4,
                layer="above"
            )
            
            link1 = event.get('Link1', '')
            h_text = f"<b>{event_name}</b> ({event_cat})<br>日期: {event_date.date()}<br>{event_note}"
            if pd.notna(link1) and link1:
                h_text += f"<br><a href='{link1}'>查看來源</a>"

            # Label positioned significantly above the data area
            fig.add_annotation(
                x=event_date,
                y=1.12, # Outside the plot area
                yref='paper',
                text=f"🚩 {event_name}",
                showarrow=False,
                textangle=-90,
                xanchor='center',
                yanchor='bottom',
                font=dict(size=14, color=color, family="Arial Black"),
                bgcolor="white",
                bordercolor=color,
                borderwidth=2,
                hovertext=h_text
            )

    # Get current time for footer
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S')

    # 6. Styling & Layout
    fig.update_layout(
        title=dict(text='<b>Taiwan VIX vs TAIEX 走勢對照圖 (附重大市場事件)</b>', x=0.5, y=0.98, font=dict(size=24, color='#333')),
        template='plotly_white', hovermode='x unified', height=1000,
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=250, b=50), # Large top margin for flags
        annotations=[dict(
            text=f"資料更新時間: {timestamp} (CST) | 數據來源: TAIFEX, Yahoo Finance",
            showarrow=False, xref="paper", yref="paper", x=1, y=-0.08, font=dict(size=10, color="gray")
        )]
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
        rangeslider=dict(visible=True, thickness=0.04)
    )

    fig.update_yaxes(title_text="<b>VIX 指數值</b>", secondary_y=False, range=[0, max_vix], gridcolor='#f0f0f0')
    fig.update_yaxes(title_text="TAIEX 指數", secondary_y=True, showgrid=False)

    fig.write_html(output_html, include_plotlyjs='cdn', config={'displayModeBar': True, 'displaylogo': False})
    print(f"Professional interactive chart saved to {output_html}")

if __name__ == "__main__":
    df_vix = get_vix_data()
    plot_vix_interactive(df_vix)
