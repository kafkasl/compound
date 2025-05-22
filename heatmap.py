from fasthtml.common import *
from monsterui.all import *
import db
import datetime as dt
import plotly.graph_objects as go

def HeatmapComponent(heatmap_data):
    # Create GitHub heatmap
    habit_names = heatmap_data["habits"]
    dates = heatmap_data["dates"]
    z_values = heatmap_data["data"]
    counts = heatmap_data.get("counts", None)
    units = heatmap_data.get("units", [""] * len(habit_names))
    
    # Create empty placeholder if no data
    if not habit_names or not dates:
        return Card(P("No habit data recorded yet", cls=TextPresets.muted_sm))
    
    # Find the maximum count value across all habits
    max_count = 1
    for row in counts:
        row_max = max(row) if row else 0
        max_count = max(max_count, row_max)
    
    # Create hover text matrix with actual values
    hover_text = []
    for i, habit in enumerate(habit_names):
        hover_row = []
        unit = units[i]
        
        for j, date in enumerate(dates):
            volume = z_values[i][j]
            count = counts[i][j] if counts else None
            
            txt = f"{habit}<br>Date: {date.strftime('%Y-%m-%d')}"
            if count > 0:
                txt += f"<br>Count: {count}×"
                txt += f"<br>Total: {volume} {unit}"
                
            hover_row.append(txt)
        hover_text.append(hover_row)
    
    # GitHub-like colorscale
    custom_colorscale = [
        [0, "rgba(235, 237, 240, 1)"],    # Light gray for zero
        [0.0001, "rgba(155, 233, 168, 1)"], # Light green for very small values
        [0.5, "rgba(64, 196, 99, 1)"],    # Medium green
        [1, "rgba(33, 110, 57, 1)"]       # Dark green
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=counts,
        x=dates,
        y=habit_names,
        colorscale=custom_colorscale,
        hoverinfo='text',
        text=hover_text,
        # Make sure 0 is distinctly colored
        zmin=0,
        zmax=max_count
    ))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=max(250, len(habit_names) * 40 + 100),
        xaxis_nticks=15,
        xaxis=dict(
            tickformat="%b %d",
            tickangle=-45
        )
    )
    
    heatmap_html = fig.to_html(include_plotlyjs=False, full_html=False, config={'displayModeBar': False})
    
    return Card(
        Safe(heatmap_html),
        id="heatmap", hx_swap_oob="true",
    )