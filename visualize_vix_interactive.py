import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import pytz

# Configuration
csv_file = "global_vix_merged.csv"
output_html = "vix_chart_interactive.html"
years_back = 2

def get_data():
    """Load VIX data from CSV file."""
    if os.path.exists(csv_file):
        print(f"Loading data from {csv_file}...")
        try:
            df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
            return df
        except Exception as e:
            print(f"Error reading CSV: {e}")
    return pd.DataFrame()

def plot_vix_interactive(df):
    """Create interactive Plotly chart with zoom, pan, and hover capabilities."""
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

    # Create figure
    fig = go.Figure()

    # Add risk zone backgrounds
    fig.add_hrect(y0=0, y1=15, fillcolor="green", opacity=0.1,
                  layer="below", line_width=0,
                  annotation_text="Safe Zone (<15)", annotation_position="top left")
    fig.add_hrect(y0=15, y1=20, fillcolor="yellow", opacity=0.15,
                  layer="below", line_width=0,
                  annotation_text="Warning (15-20)", annotation_position="top left")
    fig.add_hrect(y0=20, y1=30, fillcolor="orange", opacity=0.15,
                  layer="below", line_width=0,
                  annotation_text="Dangerous (20-30)", annotation_position="top left")
    fig.add_hrect(y0=30, y1=100, fillcolor="red", opacity=0.1,
                  layer="below", line_width=0,
                  annotation_text="Very Dangerous (>30)", annotation_position="top left")

    # Add threshold line at 30
    fig.add_hline(y=30, line_dash="dash", line_color="darkred", line_width=3,
                  annotation_text="VERY DANGEROUS THRESHOLD",
                  annotation_position="left",
                  annotation_font_color="darkred",
                  annotation_font_size=12)

    # Define line styles
    line_configs = {
        'US_VIX': {'color': 'blue', 'name': 'US VIX (^VIX)', 'width': 2},
        'Japan_VIX': {'color': 'red', 'name': 'Japan VIX (Nikkei VI)', 'width': 2, 'dash': 'dash'},
        'Taiwan_VIX': {'color': 'green', 'name': 'Taiwan VIX (VIXTWN)', 'width': 2}
    }

    # Add VIX lines
    for col in df_filtered.columns:
        if col in line_configs:
            config = line_configs[col]
            fig.add_trace(go.Scatter(
                x=df_filtered.index,
                y=df_filtered[col],
                mode='lines',
                name=config['name'],
                line=dict(
                    color=config['color'],
                    width=config['width'],
                    dash=config.get('dash', 'solid')
                ),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Date: %{x|%Y-%m-%d}<br>' +
                              'VIX: %{y:.2f}<br>' +
                              '<extra></extra>'
            ))

    # Add vertical line for today
    latest_date = df_filtered.index.max()
    fig.add_vline(x=latest_date, line_dash="dot", line_color="gray", line_width=2)

    # Get timestamp
    cst = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(cst).strftime('%Y-%m-%d %H:%M:%S CST')

    # Update layout
    fig.update_layout(
        title=dict(
            text=f'VIX Indices (Last {years_back} Years)<br><sub>Generated: {timestamp}</sub>',
            font=dict(size=20)
        ),
        xaxis_title='Date',
        yaxis_title='VIX Value',
        yaxis=dict(range=[0, max(40, df_filtered.max().max() * 1.1)]),
        hovermode='x unified',
        template='plotly_white',
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1
        ),
        # Enable range slider and buttons for easy navigation
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=2, label="2y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                bgcolor="rgba(255, 255, 255, 0.8)",
                activecolor="lightblue"
            ),
            rangeslider=dict(visible=True, thickness=0.05),
            type="date"
        )
    )

    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')

    # Save as interactive HTML
    fig.write_html(
        output_html,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'vix_chart',
                'height': 800,
                'width': 1600,
                'scale': 2
            }
        }
    )
    print(f"Interactive chart saved to {output_html}")
    print(f"Open this file in a browser for interactive features:")
    print(f"  - Zoom: Click and drag on chart")
    print(f"  - Pan: Hold shift and drag")
    print(f"  - Reset: Double-click on chart")
    print(f"  - Toggle lines: Click legend items")
    print(f"  - Hover: See exact values")

if __name__ == "__main__":
    df = get_data()
    plot_vix_interactive(df)
