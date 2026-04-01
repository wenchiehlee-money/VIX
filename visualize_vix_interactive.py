import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# Configuration
csv_file = "global_vix_merged.csv"
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

def get_taiex_data(start_date, end_date):
    """Fetch TAIEX (^TWII) data from yfinance."""
    print(f"Fetching TAIEX (^TWII) data from {start_date.date()} to {end_date.date()}...")
    try:
        taiex = yf.download("^TWII", start=start_date, end=end_date)
        if not taiex.empty:
            # Handle multi-index columns if necessary (yfinance v0.2.40+)
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
    df = df.ffill() # Fill missing TAIEX values (weekends/holidays)

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Add TAIEX as background (Secondary Y-axis)
    # Using a light gray area to represent the market trend without distracting from VIX
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

    # Get current time for footer
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S')

    # 5. Styling & Layout
    fig.update_layout(
        title=dict(
            text='<b>Taiwan VIX vs TAIEX 走勢對照圖</b>',
            x=0.5,
            font=dict(size=22, color='#333')
        ),
        template='plotly_white',
        hovermode='x unified',
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=100, b=50),
        annotations=[
            dict(
                text=f"資料更新時間: {timestamp} (CST) | 數據來源: TAIFEX, Yahoo Finance",
                showarrow=False,
                xref="paper", yref="paper",
                x=1, y=-0.12,
                font=dict(size=10, color="gray")
            )
        ]
    )

    # Configure X-axis with range selector (MacroMicro style)
    fig.update_xaxes(
        title='日期',
        showgrid=True,
        gridcolor='#f0f0f0',
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(step="all", label="全部")
            ]),
            font=dict(size=11),
            bgcolor="white",
            activecolor="#e6f2ff"
        ),
        rangeslider=dict(visible=True, thickness=0.04)
    )

    # Configure Y-axes
    # Get max value of existing VIX columns for range calculation
    existing_vix_cols = [col for col in line_configs.keys() if col in df.columns]
    max_vix = 45 # default min-max
    if existing_vix_cols:
        current_max = df[existing_vix_cols].max().max()
        if not pd.isna(current_max):
            max_vix = max(45, current_max * 1.1)

    fig.update_yaxes(
        title_text="<b>VIX 指數值</b>", 
        secondary_y=False, 
        range=[0, max_vix],
        gridcolor='#f0f0f0'
    )
    fig.update_yaxes(
        title_text="TAIEX 指數", 
        secondary_y=True, 
        showgrid=False
    )

    # Save as interactive HTML
    fig.write_html(
        output_html,
        include_plotlyjs='cdn',
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        }
    )
    print(f"Professional interactive chart saved to {output_html}")

if __name__ == "__main__":
    df_vix = get_vix_data()
    plot_vix_interactive(df_vix)
