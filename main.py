from fasthtml.common import *
from fastcore.all import *
from monsterui.all import *
from fasthtml.oauth import GoogleAppClient, OAuth

from heatmap import HeatmapComponent
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
    Link(rel='stylesheet', href='style.css', type='text/css')
)
skip = ('/login', '/logout', '/redirect', r'/.*\.(png|jpg|ico|css|js|md|svg)', '/static')

app, rt = fast_app(hdrs=hdrs)
oauth = Auth(app, cli, skip=skip)


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
        hx_swap_oob="true"
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
                        name="value", value=str(h["default_value"]), 
                        min=0, max=60, step=1, hx_trigger="change",
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
        ),
        cls="habit-card"
    )

def generate_habit_grid(auth):
    habits = db.get_habits_with_counts(auth)
    cards = [HabitCard(h) for h in habits]
    return Grid(*cards, id="habits-grid", cols_max=4, cls="gap-0", hx_swap_oob="true")

def generate_heatmap(auth):
    return HeatmapComponent(db.get_heatmap_data(auth))


def UserMenu(email: str):
    return DivHStacked(P(email), A("Logout", href="/logout"))

@app.get
def index(auth):
    user = db.get_user(auth)
    print(f"{user=}")
    today = dt.date.today().strftime("%A, %B %d, %Y")
    
    return (Title("Compound Habits"),
            Favicon("/static/img/favicon.svg", "/static/img/favicon-dark.svg"), 
            Container(
                Div(
                    H1('Compound Habits', cls="header-title"), 
                    P(today, cls=TextPresets.muted_sm + " header-date"),
                    UserMenu(user.email),
                    cls="header-container"
                ),
                NewHabitForm(),
                generate_habit_grid(auth),
                generate_heatmap(auth)
            )
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
    db.add_habit(auth, name, unit, float(value))
    return NewHabitForm(), generate_habit_grid(auth), generate_heatmap(auth)

@app.post
def track_habit(habit_id: str, value: float, auth):
    db.record_habit(auth, habit_id, float(value))
    
    # Get the updated habit with new count
    habits = db.get_habits_with_counts(auth)
    updated_habit = first((h for h in habits if str(h["id"]) == habit_id))
    
    return (HabitCard(updated_habit),
            generate_habit_grid(auth),
            generate_heatmap(auth))


@app.delete("/delete_last/{habit_id}")
def delete_last(habit_id: str, auth):
    """Delete last entry of a given habit"""
    db.delete_last_entry(auth, habit_id)
    
    return generate_habit_grid(auth), generate_heatmap(auth)

@app.delete("/habit/{habit_id}")
def delete_habit(habit_id: str, auth):
    db.delete_habit(auth, habit_id)
    
    return generate_habit_grid(auth), generate_heatmap(auth)


# Start server
if __name__ == "__main__":
    serve()