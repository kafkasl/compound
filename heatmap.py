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
    units = heatmap_data.get("units", [""] * len(habit_names))  # Get units or empty strings
    
    # Create empty placeholder if no data
    if not habit_names or not dates:
        return Card(P("No habit data recorded yet", cls=TextPresets.muted_sm))
    
    # Normalize each row (each habit's values) to 0-1 scale
    normalized_z = []
    for row in z_values:
        max_val = max(row) if max(row) > 0 else 1  # Avoid division by zero
        normalized_row = [val/max_val for val in row]
        normalized_z.append(normalized_row)
    
    # Create hover text matrix with actual values
    hover_text = []
    for i, habit in enumerate(habit_names):
        hover_row = []
        unit = units[i]  # Get unit for this habit
        
        for j, date in enumerate(dates):
            volume = z_values[i][j]
            count = counts[i][j] if counts else None
            
            txt = f"{habit}<br>Date: {date.strftime('%Y-%m-%d')}"
            if volume > 0:
                txt += f"<br>Count: {count}×"
                txt += f"<br>Total: {volume} {unit}"

            hover_row.append(txt)
        hover_text.append(hover_row)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=normalized_z,
        x=dates,
        y=habit_names,
        colorscale='Viridis',
        hoverinfo='text',
        text=hover_text
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
    )