from fasthtml.common import *
from monsterui.all import *
import db
import datetime as dt
from heatmap import HeatmapComponent


hdrs = (
    Theme.blue.headers(),
    Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js")
)

app, rt = fast_app(hdrs=hdrs)
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

def HabitCard(h):
    # Display today's total along with the habit name
    today_total = h.get("today_total", 0)
    today_count = h.get("today_count", 0)
    unit_display = h["unit"] if h["unit"] else ""
    
    return Card(
            Form(
            DivHStacked(
                Div(
                    H4(h["name"]),
                    P(f"Today: {today_count}× ({today_total} {unit_display})", cls=TextPresets.muted_sm),
                    cls="min-w-40"
                ),
                Div(
                    Range(
                        label=h["unit"],
                        id=f"track-input-{h['id']}", name="value", value=str(h["default_value"]), 
                        min=0, max=60, step=1, hx_trigger="change"
                    ),
                    cls="flex-1 px-4"
                ),
                Button("+1"),
                Button("-1", 
                      hx_delete=f"/delete_last/{h['id']}", 
                      hx_swap="outerHTML", 
                      hx_target="closest .habit-card"),
                Input(type="hidden", name="habit_id", value=h["id"]),
            ),
            hx_post=track_habit,
            hx_swap="outerHTML", hx_target="closest .habit-card"
        ),
        cls="habit-card"
    )


@app.get
def index():
    habits = db.get_habits_with_counts()
    today = dt.date.today().strftime("%A, %B %d, %Y")
    
    print(f"{habits=}")
    cards = [HabitCard(h) for h in habits ]
    
    # GitHub-style heatmap
    github_heatmap = HeatmapComponent(db.get_heatmap_data())
    
    return Container(
            DivHStacked(H1('Compound Habits'), P(today, cls=TextPresets.muted_sm)),
            Card(NewHabitForm()),
            Grid(*cards, gap=4, cls="mt-4"),
            github_heatmap
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
    
    # Get the updated habit with new count
    habits = db.get_habits_with_counts()
    updated_habit = next((h for h in habits if str(h["id"]) == habit_id), None)
    
    return HabitCard(updated_habit)

# Delete last entry endpoint
@app.delete("/delete_last/{habit_id}")
def delete_last(habit_id: str):
    db.delete_last_entry(habit_id)
    
    # Get the updated habit with new count
    habits = db.get_habits_with_counts()
    updated_habit = next((h for h in habits if str(h["id"]) == habit_id), None)
    
    return HabitCard(updated_habit)

# Start server
if __name__ == "__main__":
    serve()