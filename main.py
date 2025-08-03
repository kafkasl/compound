from fasthtml.common import *
from fastcore.all import *
from monsterui.all import *
from fasthtml.oauth import GoogleAppClient, OAuth

from heatmap import HeatmapComponent
from plots import HabitLinePlot
import db

import datetime as dt

cli = GoogleAppClient.from_file('client_secret.json')

class Auth(OAuth):
    def get_auth(self, info, ident, session, state):
        print(f"{info=}")
        if info.email_verified and info.email:
            # Ensure user exists and set current user context
            db.ensure_user(info.sub, info.email, info.name, info.picture)
            return RedirectResponse('/', status_code=303)

hdrs = (
    Theme.blue.headers(),
    Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
    Link(rel='stylesheet', href='style.css', type='text/css'),
    # Script("htmx.logAll();") # debug HTMX events
)
skip = ('/login', '/logout', '/redirect', r'/.*\.(png|jpg|ico|css|js|md|svg)', '/static')

app, rt = fast_app(hdrs=hdrs)
oauth = Auth(app, cli, skip=skip)

def UserMenu(email: str): return DivHStacked(P(email), A("Logout", href="/logout"))

def PageLayout(*children, title="Compound Habits"):
    return (Title(title),
            Favicon("/static/img/favicon.svg", "/static/img/favicon-dark.svg"), 
            Container(*children))

def Header(user_email, title='Compound Habits'):
    today = dt.date.today().strftime("%A, %B %d, %Y")
    return Div(
        H1(title, cls="header-title"), 
        P(today, cls=TextPresets.muted_sm + " header-date"),
        UserMenu(user_email),
        cls="header-container"
    )

def NewHabitForm():
    return Card(
            Form(
            DivHStacked(
            Input(name="name", placeholder="Habit name"),
                Input(name="unit", placeholder="Unit (s/kg)"),
                Input(name="value", type="number", value="1.0"),
            Button("Add"),
            ),
            hx_post=add_habit),
        id='new-habit-form',
        hx_target="#habits-grid",
        hx_swap="beforeend"
    )

def HabitCard(h):
    # Display today's total along with the habit name
    today_total, today_count = h.get("today_total", 0), h.get("today_count", 0)
    unit_display = h["unit"] if h["unit"] else ""
    
    return Card(
            Form(
                Div(
                    Div(
                        H4(h["name"], title=h["name"], data_tooltip=h["name"]),
                        P(f"{today_count}× ({today_total} {unit_display})", cls=TextPresets.muted_sm),
                    ),
                    Div(
                        Button("+1"),
                        Button("-1", 
                            hx_delete=f"/delete_last/{h['id']}", 
                            hx_swap="outerHTML", 
                            hx_target="closest .habit-card"),
                        Input(type="hidden", name="habit_id", value=h["id"]),
                    ),
                    Range(
                        label=h["unit"],
                        id=f"track-input-{h['id']}", 
                        name="value", value=str(h["latest_value"]), 
                        min=1, max=100, step=1, hx_trigger="change",
                    ),
                    cls="habit-actions-container"
                ),
            hx_post=track_habit,
            hx_swap="outerHTML", hx_target="closest .habit-card"
        ),
        A("×", 
            cls="delete-habit", 
            hx_delete=f"/habit/{h['id']}", 
            hx_confirm=f"Delete habit '{h['name']}'?",
            hx_swap="outerHTML", hx_target="closest .habit-card"
        ),
        cls="habit-card"
    )

def generate_habit_card(auth, habit_id):
    habits = db.get_habits_with_counts(auth)
    habit = first((h for h in habits if h["id"] == habit_id))
    return HabitCard(habit)

def generate_habit_grid(auth):
    habits = db.get_habits_with_counts(auth)
    cards = [HabitCard(h) for h in habits]
    return Grid(*cards, id="habits-grid", cols_max=4, cls="gap-0", hx_swap_oob="true")

def generate_heatmap(auth): 
    return Div(
        HeatmapComponent(db.get_heatmap_data(auth)), 
        id="heatmap",
        hx_get="/heatmap",
        hx_trigger="htmx:afterSwap from:#habits-grid delay:500ms, htmx:beforeCleanupElement from:.habit-card"
    )

@app.get
def index(auth):
    user = db.get_user(auth)
    print(f"{user=}")
    
    return PageLayout(
        Header(user.email),
        NewHabitForm(),
        generate_habit_grid(auth),
        generate_heatmap(auth)
    )

def generate_plot(habit_id: int, plot_type: str, auth, days: int = 30):
    """Generate a plot for a specific habit"""
    habits = db.get_habits(auth)
    print(f"{habits=}")
    habit = next((h for h in habits if h["id"] == habit_id), None)
    if not habit: return P("Habit not found", cls=TextPresets.muted_sm)
    
    # Get specified days of data
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(days=days)
    date_range = [start_date + dt.timedelta(days=x) for x in range(days + 1)]
    
    sum_dict, count_dict = db.get_habit_stats(habit_id, auth, start_date, end_date)
    
    if plot_type == "count":
        values = [count_dict.get(d.isoformat(), 0) for d in date_range]
    elif plot_type == "sum":
        values = [sum_dict.get(d.isoformat(), 0) for d in date_range]
    else:  # average
        values = [sum_dict.get(d.isoformat(), 0) / count_dict.get(d.isoformat(), 1) 
                  if count_dict.get(d.isoformat(), 0) > 0 else 0 for d in date_range]
    
    return HabitLinePlot(habit["name"], date_range, values, habit.get("unit", ""), plot_type)

@app.get('/plots')
def plot(auth):
    habits = db.get_habits(auth)

    return PageLayout(
        Header(db.get_user(auth).email, title='Habit Plots'),
        Card(
            H3("Available Plot Endpoints"),
            P("/plots/{habit_id}/{type}?days={number}"),
            Ul(
                Li("type: count, sum, or average"),
                Li("days: number of days to show (default: 30)"),
                Li("Example: /plots/1/sum?days=150"),
                cls=TextPresets.muted_sm
            ),
            H4("Your Habits", cls="mt-4"),
            Ul(
                *[Li(A(f"{h['id']} - {h['name']}", href=f"/plots/{h['id']}/sum?days=150")) for h in habits],
                cls="habit-list"
            )
        ),
        title="Habit Plots - Compound Habits"
    )

@app.get('/plots/{habit_id}/{plot_type}')
def plot(habit_id: int, plot_type: str, auth, days: int = 30):
    return PageLayout(
        Header(db.get_user(auth).email, title='Habit Plot'),
        generate_plot(habit_id, plot_type, auth, days),
        title="Habit Plot - Compound Habits"
    )

@app.get('/login')
def login(req): 
    return (
        Title("Compound Habits - Login"),
        Favicon("/static/img/favicon.svg", "/static/img/favicon-dark.svg"),
        DivVStacked(
            Img(src="/static/img/favicon.svg", width=100),
            DivVStacked(
                H1('Compound Habits', cls="text-center"),
                P("Track your habits and build consistency", cls=TextPresets.muted_sm + " text-center"),
                A(Button("Log in with Google"), href=oauth.login_link(req))
            ),
            cls="pt-[20vh]",
        ),
    )

@app.get('/logout')
def logout(session):
    session.pop('auth', None)
    return RedirectResponse('/login', status_code=303)

@app.post
def add_habit(name: str, unit: str, value: str, auth):
    habit_id = db.add_habit(auth, name, unit, float(value))
    return NewHabitForm(), generate_habit_card(auth, habit_id)

@app.post
def track_habit(habit_id: int, value: float, auth):
    db.record_habit(auth, habit_id, float(value))
    
    # Get the updated habit with new count
    return generate_habit_card(auth, habit_id)

@app.get("/heatmap")
def heatmap(auth):
    return generate_heatmap(auth)


@app.delete("/delete_last/{habit_id}")
def delete_last(habit_id: int, auth):
    """Delete last entry of a given habit"""
    db.delete_last_entry(auth, habit_id)

    return generate_habit_card(auth, habit_id)

@app.delete("/habit/{habit_id}")
def delete_habit(habit_id: int, auth):
    db.delete_habit(auth, habit_id)



# Start server
if __name__ == "__main__":
    serve()