from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
import json
import random
import string
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "cactumatch_secure_key_2026"
app.config['UPLOAD_FOLDER'] = 'static/avatars'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = "db.json"
CODE_FILE = "codes.json"
EVAL_FILE = "evals.json"

SUPER_ADMINS = {
    "ian@cactumatch.com": "cactumatch2026",
}

ADMIN_USERS = {
    "roundmanager@cactumatch.com": "cactumatch2026",
}

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": [], "matches": [], "judges": []}, f)
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    for u in data["users"]:
        if "color" not in u:
            u["color"] = "#4285F4"
        if "premium" not in u:
            u["premium"] = False
        if "premium_expire" not in u:
            u["premium_expire"] = None
        if "is_judge" not in u:
            u["is_judge"] = False
        if "level" not in u:
            u["level"] = None
        if "cv" not in u:
            u["cv"] = ""
        if "cv_last_update" not in u:
            u["cv_last_update"] = None
        if "cv_status" not in u:
            u["cv_status"] = "pending"
    return data

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_codes():
    if not os.path.exists(CODE_FILE):
        with open(CODE_FILE, "w") as f:
            json.dump([], f)
    with open(CODE_FILE, "r") as f:
        return json.load(f)

def save_codes(codes):
    with open(CODE_FILE, "w") as f:
        json.dump(codes, f, indent=2)

def load_evals():
    if not os.path.exists(EVAL_FILE):
        with open(EVAL_FILE, "w") as f:
            json.dump([], f)
    with open(EVAL_FILE, "r") as f:
        return json.load(f)

def save_evals(evals):
    with open(EVAL_FILE, "w") as f:
        json.dump(evals, f, indent=2)

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

    now_dt = datetime.now()
    for u in db["users"]:
        if u["email"] == "ian@cactumatch.com":
            u["premium"] = True
            u["premium_expire"] = None
            continue

        if u.get("premium_expire"):
            try:
                exp = datetime.strptime(u["premium_expire"], "%Y-%m-%d %H:%M:%S")
                if now_dt > exp:
                    u["premium"] = False
                    u["premium_expire"] = None
            except:
                u["premium"] = False
                u["premium_expire"] = None
    save_db(db)

def get_color(email):
    colors = ["#4285F4", "#EA4335", "#34A853", "#FBBC05", "#8E24AA", "#F06292", "#5C6BC0", "#26A69A", "#8D6E63", "#78909C"]
    return colors[sum(ord(c) for c in email) % len(colors)]

def get_user_by_email(email):
    db = load_db()
    for u in db["users"]:
        if u["email"].lower() == email.lower():
            return u
    return None

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

    filtered = []
    if user:
        for m in db["matches"]:
            if "level_restrict" not in m:
                filtered.append(m)
            else:
                ul = user.get("level")
                ml = m.get("level")
                if ul is None or ml is None:
                    continue
                if ml in [1,2]:
                    if ul in [1,2]:
                        filtered.append(m)
                elif ml in [3,4]:
                    if ul in [3,4]:
                        filtered.append(m)
                elif ml in [5,6]:
                    if ul in [5,6]:
                        filtered.append(m)
    else:
        filtered = db["matches"]

    evals = []
    pending_count = 0
    if user and user["email"] == "ian@cactumatch.com":
        evals = load_evals()
        pending_count = len(evals)

    redeem_confirm_code = request.args.get("confirm_code")
    return render_template("index.html", matches=filtered, user=user, redeem_confirm_code=redeem_confirm_code, evals=evals, pending_count=pending_count)

@app.route('/timer')
def timer_page():
    if "user" not in session:
        return redirect("/")
    db = load_db()
    user = None
    for u in db["users"]:
        if u["email"] == session["user"]:
            user = u
            break
    if not user or not user.get("premium"):
        return redirect("/")

    evals = []
    pending_count = 0
    if user["email"] == "ian@cactumatch.com":
        evals = load_evals()
        pending_count = len(evals)

    return render_template("index.html", user=user, matches=[], evals=evals, pending_count=pending_count)

@app.route('/generate-code', methods=['GET', 'POST'])
def generate_code():
    if session.get("user") not in SUPER_ADMINS:
        return "Permission denied", 403
    if request.method == 'POST':
        duration = request.form.get("duration", "1M")
        code = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
        expire_at = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        codes = load_codes()
        codes.append({"code": code, "expire_at": expire_at, "used": False, "used_by": None, "duration": duration})
        save_codes(codes)
        flash(f"Generated: {code} | {duration} | valid 10min")
        return redirect("/")
    return redirect("/")

@app.route('/redeem-code', methods=['POST'])
def redeem_code():
    if "user" not in session:
        return redirect("/")
    code_str = request.form["code"].strip()
    force = request.form.get("force") == "1"
    now = datetime.now()
    codes = load_codes()
    db = load_db()
    email = session["user"]
    user = None
    for u in db["users"]:
        if u["email"] == email:
            user = u
            break
    if not user:
        flash("User not found")
        return redirect("/")
    target = None
    for c in codes:
        if c["code"] == code_str:
            target = c
            break
    if not target:
        flash("Invalid code")
        return redirect("/")
    if target["used"]:
        flash("Code already used")
        return redirect("/")
    try:
        exp = datetime.strptime(target["expire_at"], "%Y-%m-%d %H:%M:%S")
        if now > exp:
            flash("Code expired")
            return redirect("/")
    except:
        flash("Invalid code")
        return redirect("/")
    has_premium = user.get("premium") is True and user.get("premium_expire") is not None
    if has_premium and not force:
        flash("Your premium account has not expired yet. If you still want to redeem a new one, the new one will replace your old one and start counting days from 0.")
        return redirect(f"/?confirm_code={code_str}")
    target["used"] = True
    target["used_by"] = email
    save_codes(codes)
    dur = target.get("duration", "1M")
    if dur == "7D":
        new_exp = now + timedelta(days=7)
    elif dur == "1M":
        new_exp = now + timedelta(days=30)
    elif dur == "3M":
        new_exp = now + timedelta(days=90)
    elif dur == "1Y":
        new_exp = now + timedelta(days=365)
    elif dur == "2Y":
        new_exp = now + timedelta(days=365*2)
    else:
        new_exp = now + timedelta(days=30)
    user["premium"] = True
    user["premium_expire"] = new_exp.strftime("%Y-%m-%d %H:%M:%S")
    save_db(db)
    flash(f"Success! Premium activated: {dur}")
    return redirect("/")

@app.route('/api/users')
def api_users():
    q = request.args.get("q", "").lower()
    db = load_db()
    users = [u["email"] for u in db["users"] if q in u["email"].lower() or q in u["first_name"].lower() or q in u["last_name"].lower()]
    return jsonify(users[:5])

@app.route('/api/check-email')
def check_email():
    email = request.args.get("email", "").strip()
    user = get_user_by_email(email)
    if user:
        return jsonify({"exists": True, "name": f"{user['first_name']} {user['last_name']}"})
    return jsonify({"exists": False})

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
        new_user = {"email": email, "password": pwd, "first_name": "Ian", "last_name": "Admin", "avatar": "", "color": get_color(email), "premium": True, "premium_expire": None, "is_judge": False, "level": 6, "cv": "ROOT", "cv_last_update": None, "cv_status": "approved"}
        db["users"].append(new_user)
        save_db(db)
        session["user"] = email
        return redirect("/")
    if email in ADMIN_USERS and pwd == ADMIN_USERS[email]:
        for u in db["users"]:
            if u["email"] == email:
                session["user"] = email
                return redirect("/")
        new_user = {"email": email, "password": pwd, "first_name": "Round", "last_name": "Manager", "avatar": "", "color": get_color(email), "premium": False, "premium_expire": None, "is_judge": False, "level": None, "cv": "", "cv_last_update": None, "cv_status": "pending"}
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
    is_judge = request.form.get("is_judge") == "on"
    cv = request.form["cv"].strip()
    db = load_db()
    for u in db["users"]:
        if u["email"] == email:
            flash("Email already exists")
            return redirect("/")
    user = {"email": email, "password": pwd, "first_name": first, "last_name": last, "avatar": "", "color": get_color(email), "premium": False, "premium_expire": None, "is_judge": is_judge, "level": None, "cv": cv, "cv_last_update": None, "cv_status": "pending"}
    db["users"].append(user)
    save_db(db)
    ev = {"email": email, "name": f"{first} {last}", "cv": cv, "type": "pre", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
    evals = load_evals()
    evals.append(ev)
    save_evals(evals)

    flash("You successfully created an account, please log in")
    return redirect("/?registered=success")

@app.route('/update-cv', methods=['POST'])
def update_cv():
    if "user" not in session:
        return redirect("/")

    email = session["user"]
    if email == "ian@cactumatch.com":
        flash("Ian does not need to update CV")
        return redirect("/")

    cv = request.form["new_cv"].strip()
    db = load_db()
    user = None
    for u in db["users"]:
        if u["email"] == email:
            user = u
            break

    if not user:
        flash("User not found")
        return redirect("/")

    user["cv"] = cv
    user["cv_last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user["cv_status"] = "pending"
    save_db(db)

    ev = {"email": email, "name": f"{user['first_name']} {user['last_name']}", "cv": cv, "type": "re", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
    evals = load_evals()
    evals.append(ev)
    save_evals(evals)

    flash("CV updated, waiting for evaluation")
    return redirect("/")

@app.route('/set-level', methods=['POST'])
def set_level():
    if session.get("user") != "ian@cactumatch.com":
        return "Denied", 403

    email = request.form["email"].strip()
    level = request.form.get("level")
    if not level:
        flash("Please select level")
        return redirect("/")

    db = load_db()
    found = False
    for u in db["users"]:
        if u["email"] == email:
            u["level"] = int(level)
            u["cv_status"] = "approved"
            found = True
            break

    if not found:
        flash("User not found")
        return redirect("/")

    save_db(db)
    evals = load_evals()
    new_evals = [e for e in evals if e["email"] != email]
    save_evals(new_evals)

    flash(f"Success: Set {email} to LV{level}")
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
    if not user or user.get("is_judge"):
        return redirect("/")

    match_type = request.form["type"]
    teammate_email = request.form.get("teammate_email", "").strip()
    no_account = request.form.get("no_account") == "on"
    teammate_name = request.form.get("teammate_name", "").strip()

    if no_account and teammate_name:
        team = f"({user['first_name']} {user['last_name']}, {teammate_name})"
    elif not no_account and teammate_email:
        teammate_user = get_user_by_email(teammate_email)
        if teammate_user:
            team = f"({user['first_name']} {user['last_name']}, {teammate_user['first_name']} {teammate_user['last_name']})"
        else:
            team = f"({user['first_name']} {user['last_name']}, {teammate_email})"
    else:
        team = f"({user['first_name']} {user['last_name']})"

    restrict = request.form.get("level_restrict") == "on"
    match = {
        "author": user["email"],
        "type": match_type,
        "time": request.form["time"].replace("T", " "),
        "platform": request.form["platform"],
        "judge": request.form.get("judge", "").strip() or "Not specified",
        "meeting_id": request.form["meeting_id"],
        "meeting_pwd": request.form["meeting_pwd"],
        "teams": [team],
        "premium": user.get("premium", False)
    }
    if restrict and user.get("level"):
        match["level_restrict"] = True
        match["level"] = user["level"]
    db["matches"].append(match)
    save_db(db)
    return redirect("/")

@app.route('/join/<int:idx>', methods=['POST'])
def join(idx):
    if "user" not in session:
        flash("Please login first")
        return redirect("/")

    db = load_db()
    if idx < 0 or idx >= len(db["matches"]):
        return redirect("/")

    match = db["matches"][idx]
    email = session["user"]
    user = None
    for u in db["users"]:
        if u["email"] == email:
            user = u
            break

    if not user or user.get("is_judge"):
        return redirect("/")

    full_name = f"{user['first_name']} {user['last_name']}"
    for team in match["teams"]:
        if full_name in team:
            flash("You already joined this match")
            return redirect("/")

    teammate_email = request.form.get("teammate_email", "").strip()
    no_account = request.form.get("no_account") == "on"
    teammate_name = request.form.get("teammate_name", "").strip()

    if no_account and teammate_name:
        team = f"({full_name}, {teammate_name})"
    elif not no_account and teammate_email:
        teammate_user = get_user_by_email(teammate_email)
        if teammate_user:
            team = f"({full_name}, {teammate_user['first_name']} {teammate_user['last_name']})"
        else:
            team = f"({full_name}, {teammate_email})"
    else:
        team = f"({full_name})"

    match["teams"].append(team)
    save_db(db)
    flash("Successfully joined the match!")
    return redirect("/")

@app.route('/delete/<int:idx>')
def delete(idx):
    user = session.get("user")
    if user not in SUPER_ADMINS and user not in ADMIN_USERS:
        return redirect("/")
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
    app.run(host="0.0.0.0", port=10000, debug=True)
