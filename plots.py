from fasthtml.common import *
import plotly.graph_objects as go
import datetime as dt

def HabitLinePlot(habit_name, dates, values, unit="", plot_type="count"):
    """Create a bar plot for habit data"""
    
    # Format dates for display
    date_strings = [d.strftime('%b %d') for d in dates]
    
    # Create plotly figure
    fig = go.Figure()
    
    # Determine y-axis label
    if plot_type == "count":
        y_label = "Times per day"
        title = f"{habit_name} - Daily Count"
    elif plot_type == "sum":
        y_label = f"Total {unit}" if unit else "Total"
        title = f"{habit_name} - Daily Total"
    else:  # average
        y_label = f"Average {unit}" if unit else "Average"
        title = f"{habit_name} - Daily Average"
    
    # Add bar trace
    fig.add_trace(go.Bar(
        x=date_strings,
        y=values,
        name=habit_name,
        marker_color='#3b82f6'
    ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        height=400,
        margin=dict(l=50, r=30, t=60, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#6b7280'),
        showlegend=False,
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(156, 163, 175, 0.1)',
            tickangle=-45
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(156, 163, 175, 0.1)',
            rangemode='tozero'
        )
    )
    
    # Convert to HTML div
    return Div(
        NotStr(fig.to_html(include_plotlyjs=False, div_id="habit-plot")),
        id="plot-container"
    )