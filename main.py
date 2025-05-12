from fasthtml.common import *
from monsterui.all import *
import db
from pathlib import Path

hdrs = (Theme.blue.headers(), Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"))

# Create your app with the theme
app, rt = fast_app(hdrs=hdrs)

# Initialize database
db.init_db()

def NewHabitForm():
    return Form(
        Input(name="name", placeholder="Habit name"),
        Input(name="unit", placeholder="Unit (optional)"),
        Input(name="value", type="number", value="1.0"),
        Button("Add"),
        hx_post=add_habit, hx_swap="outerHTML",
        id='new-habit-form',
        hx_swap_oob="true"
    )

# Main page with habit list
@app.get
def index():
    habits = db.get_habits()
    
    # Habit cards - single tap to record
    cards = [
        Card(
            Form(
                LabelRange(
                    f"{h['name']} {h['unit'] or ''}",
                    id=f"track-input-{h['id']}", 
                    name="value", 
                    value=str(h["default_value"]), 
                    min=0, 
                    max=60, 
                    step=1, 
                    label_range=True,
                    hx_trigger="change"
                ),
                Button("Track"),
                Input(type="hidden", name="habit_id", value=h["id"]),
                hx_post=track_habit
            )
        ) for h in habits
    ]
    
    # Add new habit form
    
    # Visualization placeholders
    viz_divs = [Div(id=f"viz-{h['id']}") for h in habits]
    
    return Titled("Habit Tracker", 
        Container(
            Card(NewHabitForm(), header=H2("New Habit")),
            Grid(*cards, cls="habit-grid"),
            *viz_divs
        ),
        Style("""
            .habit-grid { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
        """)
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

# Get visualization
@app.get("/viz/{habit_id}")
def get_viz(habit_id: str):
    img_bytes = db.generate_heatmap(int(habit_id))
    return FileResponse(img_bytes, media_type="image/png")

# Start server
if __name__ == "__main__":
    serve()