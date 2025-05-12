from fasthtml.common import *
from monsterui.all import *
import db
import datetime as dt
import plotly.graph_objects as go

# Headers with plotly included
hdrs = (
    Theme.blue.headers(),
    Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js")
)

# Create app
app, rt = fast_app(hdrs=hdrs)

# Initialize database
db.init_db()

def NewHabitForm():
    return Form(
        DivHStacked(
            Input(name="name", placeholder="Habit name"),
            Input(name="unit", placeholder="Unit (s/kg)", cls="mx-2 w-40"),
            Input(name="value", type="number", value="1.0", cls="mx-2 w-40"),
            Button("Add"),
        ),
        hx_post=add_habit, hx_swap="outerHTML",
        id='new-habit-form',
        hx_swap_oob="true"
    )

def HeatmapComponent():
    # Create GitHub heatmap
    heatmap_data = db.get_heatmap_data()
    habit_names = heatmap_data["habits"]
    dates = heatmap_data["dates"]
    z_values = heatmap_data["data"]
    
    # Create empty placeholder if no data
    if not habit_names or not dates:
        habit_names = ["No habits recorded yet"]
        dates = [dt.date.today() - dt.timedelta(days=x) for x in range(5)]
        z_values = [[0, 0, 0, 0, 0]]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=dates,
        y=habit_names,
        colorscale='Viridis'
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

@app.get
def index():
    habits = db.get_habits()
    today = dt.date.today().strftime("%A, %B %d, %Y")
    
    print(f"{habits=}")
    cards = [
        Card(Form(
                DivHStacked(
                    P(h["name"]),
                    Div(
                        Range(
                            label=h["unit"],
                            id=f"track-input-{h['id']}", name="value", value=str(h["default_value"]), 
                            min=0, max=60, step=1, hx_trigger="change"
                        ),
                        cls="flex-1 px-4"
                    ),
                    Button("Track"),
                    Input(type="hidden", name="habit_id", value=h["id"]),
                ),
                hx_post=track_habit
            ),
        ) for h in habits
    ]
    
    # GitHub-style heatmap
    github_heatmap = HeatmapComponent()
    
    return Titled("Habit Tracker", 
        Container(
            H3(today),
            Card(NewHabitForm()),
            Grid(*cards, gap=4, cls="mt-4"),
            github_heatmap
        )
    )

# Add habit
@app.post
def add_habit(name: str, unit: str, value: str):
    print(name, unit, value)
    db.add_habit(name, unit, float(value))
    return NewHabitForm()

# Track habit
@app.post
def track_habit(habit_id: str, value: float):
    print(f"habit_id: {habit_id=}, value: {value=}")
    db.record_habit(habit_id, float(value))
    return Response(None, status_code=204)

# Start server
if __name__ == "__main__":
    serve()