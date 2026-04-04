from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, json, random, datetime, os

app = Flask(__name__)
app.secret_key = "secret123"

DB = "workout.db"

# ---------------- INIT DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        email TEXT PRIMARY KEY,
        password TEXT,
        streak INTEGER DEFAULT 0,
        last_date TEXT,
        pro INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS workouts(
        email TEXT,
        plan TEXT,
        progress TEXT,
        calories INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- STREAK ----------------
def update_streak(email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT streak,last_date FROM users WHERE email=?", (email,))
    row = c.fetchone()

    streak = row[0] if row else 0
    last = row[1] if row else None
    today = datetime.date.today()

    if last:
        last = datetime.datetime.strptime(last,"%Y-%m-%d").date()
        if last == today:
            return
        elif last == today - datetime.timedelta(days=1):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    c.execute("UPDATE users SET streak=?, last_date=? WHERE email=?",
              (streak, today.strftime("%Y-%m-%d"), email))

    conn.commit()
    conn.close()

# ---------------- PLAN ----------------
def generate_plan(days):
    base = [
        {"name":"Push Ups","benefit":"Chest","cal":50,"link":"https://www.youtube.com/embed/IODxDxX7oi4"},
        {"name":"Squats","benefit":"Legs","cal":60,"link":"https://www.youtube.com/embed/aclHkVaku9U"},
        {"name":"Plank","benefit":"Core","cal":30,"link":"https://www.youtube.com/embed/pSHjTRCQxIw"},
        {"name":"Burpees","benefit":"Fat Burn","cal":100,"link":"https://www.youtube.com/embed/TU8QYVW0gDU"},
        {"name":"Crunches","benefit":"Abs","cal":40,"link":"https://www.youtube.com/embed/Xyd_fa5zoEU"}
    ]

    plan = []
    for i in range(int(days)):
        exercises = []
        for e in random.sample(base,5):
            exercises.append(e)
        plan.append({"day":f"Day {i+1}","exercises":exercises})
    return plan

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                      (request.form["email"],request.form["password"],0,"",0))
            conn.commit()
            return redirect("/")
        except:
            return "User exists"
    return render_template("signup.html")

@app.route("/login", methods=["POST"])
def login():
    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT * FROM users WHERE email=? AND password=?",
              (request.form["email"],request.form["password"]))

    if c.fetchone():
        session["email"]=request.form["email"]
        return redirect("/input")

    return "Invalid login"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/input", methods=["GET","POST"])
def input_page():
    if "email" not in session:
        return redirect("/")

    if request.method=="POST":
        plan = generate_plan(request.form["days"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("DELETE FROM workouts WHERE email=?", (session["email"],))
        c.execute("INSERT INTO workouts VALUES (?,?,?,?)",
                  (session["email"], json.dumps(plan), json.dumps({}), 0))

        conn.commit()
        return redirect("/plan")

    return render_template("workout.html")

@app.route("/plan")
def plan():
    if "email" not in session:
        return redirect("/")

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT plan,progress,calories FROM workouts WHERE email=?",
              (session["email"],))
    row=c.fetchone()

    if not row:
        return redirect("/input")

    plan=json.loads(row[0])
    progress=json.loads(row[1]) if row[1] else {}
    calories=row[2] if row[2] else 0

    total=sum(len(d["exercises"]) for d in plan)
    percent=int((len(progress)/total)*100) if total else 0

    return render_template("plan.html",
                           plan=plan,
                           progress=progress,
                           percent=percent,
                           calories=calories)

@app.route("/complete/<int:d>/<int:e>")
def complete(d,e):
    if "email" not in session:
        return redirect("/")

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT progress,plan,calories FROM workouts WHERE email=?",
              (session["email"],))
    row=c.fetchone()

    progress=json.loads(row[0]) if row[0] else {}
    plan=json.loads(row[1])
    calories=row[2] if row[2] else 0

    key=f"{d}-{e}"

    if key not in progress:
        progress[key]=True
        calories += plan[d]["exercises"][e]["cal"]
        update_streak(session["email"])

    c.execute("UPDATE workouts SET progress=?, calories=? WHERE email=?",
              (json.dumps(progress),calories,session["email"]))

    conn.commit()
    return redirect("/plan")

# ✅ FIXED DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT streak FROM users WHERE email=?", (session["email"],))
    row1 = c.fetchone()
    streak = row1[0] if row1 and row1[0] else 0

    c.execute("SELECT calories FROM workouts WHERE email=?", (session["email"],))
    row2 = c.fetchone()
    calories = row2[0] if row2 and row2[0] else 0

    return render_template("dashboard.html", streak=streak, calories=calories)

# ✅ CAMERA PAGE
@app.route("/posture")
def posture():
    if "email" not in session:
        return redirect("/")

    return render_template("posture.html")

@app.route("/leaderboard")
def leaderboard():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT email,streak FROM users ORDER BY streak DESC LIMIT 10")
    users=c.fetchall()
    return render_template("leaderboard.html", users=users)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
