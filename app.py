from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "test123"
app.config['UPLOAD_FOLDER'] = 'static/avatars'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = "db.json"

SUPER_ADMINS = {
    "ian@cactumatch.com": "cactumatch2026",
    "roundmanager@cactumatch.com": "cactumatch2026"
}

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": [], "matches": []}, f)
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    for u in data["users"]:
        if "color" not in u:
            u["color"] = "#4285F4"
    return data

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def auto_clean_expired():
    db = load_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_matches = []
    for m in db["matches"]:
        try:
            if m["time"] >= now:
                new_matches.append(m)
        except:
            pass
    db["matches"] = new_matches
    save_db(db)

def get_color(email):
    colors = ["#4285F4", "#EA4335", "#34A853", "#FBBC05", "#8E24AA", "#F06292", "#5C6BC0", "#26A69A", "#8D6E63", "#78909C"]
    return colors[sum(ord(c) for c in email) % len(colors)]

@app.route('/')
def home():
    auto_clean_expired()
    db = load_db()
    user = None
    if "user" in session:
        email = session["user"]
        for u in db["users"]:
            if u["email"] == email:
                user = u
                break
    return render_template("index.html", matches=db["matches"], user=user)

@app.route('/api/users')
def api_users():
    q = request.args.get("q", "").lower()
    db = load_db()
    users = [u["email"] for u in db["users"] if q in u["email"].lower() or q in u["first_name"].lower() or q in u["last_name"].lower()]
    return jsonify(users[:5])

@app.route('/login', methods=['POST'])
def login():
    email = request.form["email"].strip().lower()
    pwd = request.form["password"].strip()
    db = load_db()

    if email in SUPER_ADMINS and pwd == SUPER_ADMINS[email]:
        for u in db["users"]:
            if u["email"] == email:
                session["user"] = email
                return redirect("/")
        new_user = {
            "email": email,
            "password": pwd,
            "first_name": "Ian" if email == "ian@cactumatch.com" else "Round",
            "last_name": "Admin" if email == "ian@cactumatch.com" else "Manager",
            "avatar": "",
            "color": get_color(email)
        }
        db["users"].append(new_user)
        save_db(db)
        session["user"] = email
        return redirect("/")

    for u in db["users"]:
        if u["email"] == email and u["password"] == pwd:
            session["user"] = email
            return redirect("/")
    flash("Invalid email or password")
    return redirect("/")

@app.route('/register', methods=['POST'])
def register():
    email = request.form["email"].strip().lower()
    pwd = request.form["password"].strip()
    first = request.form["first_name"].strip()
    last = request.form["last_name"].strip()
    db = load_db()
    for u in db["users"]:
        if u["email"] == email:
            flash("Email exists")
            return redirect("/")
    db["users"].append({
        "email": email,
        "password": pwd,
        "first_name": first,
        "last_name": last,
        "avatar": "",
        "color": get_color(email)
    })
    save_db(db)
    session["user"] = email
    return redirect("/")

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if "user" not in session:
        return redirect("/")
    email = session["user"]
    file = request.files["avatar"]
    if file:
        ext = file.filename.rsplit(".",1)[-1].lower()
        filename = f"{email.replace('@','_').replace('.','_')}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = load_db()
        for u in db["users"]:
            if u["email"] == email:
                u["avatar"] = filename
                break
        save_db(db)
    return redirect("/")

@app.route('/change-color', methods=['POST'])
def change_color():
    if "user" not in session:
        return redirect("/")
    email = session["user"]
    color = request.form.get("color")
    db = load_db()
    for u in db["users"]:
        if u["email"] == email:
            u["color"] = color
            break
    save_db(db)
    return redirect("/")

@app.route('/post', methods=['POST'])
def post():
    if "user" not in session:
        return redirect("/")
    db = load_db()
    user = None
    for u in db["users"]:
        if u["email"] == session["user"]:
            user = u
            break
    if not user:
        return redirect("/")

    team = f"({user['first_name']} {user['last_name']}, ...)"
    db["matches"].append({
        "author": user["email"],
        "type": request.form["type"],
        "time": request.form["time"].replace("T", " "),
        "platform": request.form["platform"],
        "judge": request.form["judge"],
        "meeting_id": request.form["meeting_id"],
        "meeting_pwd": request.form["meeting_pwd"],
        "teams": [team]
    })
    save_db(db)
    return redirect("/")

@app.route('/join/<int:idx>')
def join(idx):
    return redirect("/")

@app.route('/delete/<int:idx>')
def delete(idx):
    if session.get("user") in SUPER_ADMINS:
        db = load_db()
        if 0 <= idx < len(db["matches"]):
            del db["matches"][idx]
            save_db(db)
    return redirect("/")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
