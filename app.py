from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
import json
import random
import string
from datetime import datetime, timedelta


app = Flask(__name__, template_folder='Templates', static_folder='Static')
app.secret_key = "cactumatch_secure_key_2026"
app.config['UPLOAD_FOLDER'] = 'Static/avatars'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = "db.json"
CODE_FILE = "codes.json"
EVAL_FILE = "evals.json"
REPORT_FILE = "reports.json"
JOURNAL_FILE = "journal.json"

SUPER_ADMINS = {
    "ian@cactumatch.com": "cactumatch2026",
}

ADMIN_USERS = {
    "roundmanager@cactumatch.com": "cactumatch2026",
    "henry@cactumatch.com": "cactumatch2026",
}

ACCOUNT_TYPES = ["debater", "student_judge", "professional_judge"]

def get_account_type_label(account_type):
    labels = {
        "debater": "Debater",
        "student_judge": "Student Judge",
        "professional_judge": "Professional Judge"
    }
    return labels.get(account_type, "Debater")

def _generate_uid_simple(existing_uids):
    while True:
        uid = ''.join(random.choices(string.digits, k=5))
        if uid not in existing_uids:
            return uid

def _generate_rid_simple(existing_rids):
    while True:
        rid = ''.join(random.choices(string.digits, k=6))
        if rid not in existing_rids:
            return rid

def generate_uid():
    db = load_db()
    existing_uids = {u.get("uid", "") for u in db["users"]}
    return _generate_uid_simple(existing_uids)

def generate_rid():
    db = load_db()
    existing_rids = {m.get("rid", "") for m in db["matches"]}
    return _generate_rid_simple(existing_rids)

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": [], "matches": [], "judges": []}, f)
    with open(DB_FILE, "r") as f:
        data = json.load(f)

    existing_uids = {u.get("uid", "") for u in data["users"]}
    existing_rids = {m.get("rid", "") for m in data["matches"]}

    for u in data["users"]:
        if "color" not in u:
            u["color"] = "#4285F4"
        if "premium" not in u:
            u["premium"] = False
        if "premium_expire" not in u:
            u["premium_expire"] = None
        if "is_judge" not in u:
            u["is_judge"] = False
        if "account_type" not in u:
            if u.get("is_judge"):
                u["account_type"] = "professional_judge"
            else:
                u["account_type"] = "debater"
        if "level" not in u:
            u["level"] = None
        if "cv" not in u:
            u["cv"] = ""
        if "cv_last_update" not in u:
            u["cv_last_update"] = None
        if "cv_status" not in u:
            u["cv_status"] = "pending"
        if "report_count" not in u:
            u["report_count"] = 0
        if "suspended_until" not in u:
            u["suspended_until"] = None
        if "uid" not in u:
            u["uid"] = _generate_uid_simple(existing_uids)
            existing_uids.add(u["uid"])
        if "registered_date" not in u:
            u["registered_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for m in data["matches"]:
        if "rid" not in m:
            m["rid"] = _generate_rid_simple(existing_rids)
            existing_rids.add(m["rid"])
        if "judge_email" not in m:
            m["judge_email"] = ""
        if "judge_type_restriction" not in m or m.get("judge_type_restriction") not in ["any", "student_judge", "professional_judge"]:
            m["judge_type_restriction"] = "any"
        if "participants" not in m:
            m["participants"] = []
        if "teams_data" not in m:
            m["teams_data"] = []
    save_db(data)
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

def load_reports():
    if not os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "w") as f:
            json.dump([], f)
    with open(REPORT_FILE, "r") as f:
        return json.load(f)

def save_reports(reports):
    with open(REPORT_FILE, "w") as f:
        json.dump(reports, f, indent=2)

def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, "w") as f:
            json.dump([], f)
    with open(JOURNAL_FILE, "r") as f:
        return json.load(f)

def save_journal(journal):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(journal, f, indent=2)

def add_journal_entry(match):
    journal = load_journal()
    entry = {
        "rid": match.get("rid", ""),
        "time": match.get("time", ""),
        "type": match.get("type", ""),
        "platform": match.get("platform", ""),
        "meeting_id": match.get("meeting_id", ""),
        "meeting_pwd": match.get("meeting_pwd", ""),
        "teams": match.get("teams", []),
        "teams_data": match.get("teams_data", []),
        "participants": match.get("participants", []),
        "judge": match.get("judge", "Not specified"),
        "judge_email": match.get("judge_email", ""),
        "judge_type_restriction": match.get("judge_type_restriction", "any"),
        "author": match.get("author", ""),
        "author_name": match.get("author_name", ""),
        "completed": False,
        "completed_time": None
    }
    existing = None
    for j in journal:
        if j["rid"] == entry["rid"]:
            existing = j
            break
    if existing:
        existing.update(entry)
    else:
        journal.append(entry)
    save_journal(journal)

def complete_journal_entry(rid):
    journal = load_journal()
    for j in journal:
        if j["rid"] == rid:
            j["completed"] = True
            j["completed_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    save_journal(journal)

def auto_clean_expired():
    db = load_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_matches = []
    for m in db["matches"]:
        try:
            if m["time"] >= now:
                new_matches.append(m)
            else:
                complete_journal_entry(m.get("rid", ""))
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
        if u.get("suspended_until"):
            try:
                sus = datetime.strptime(u["suspended_until"], "%Y-%m-%d %H:%M:%S")
                if now_dt > sus:
                    u["suspended_until"] = None
            except:
                u["suspended_until"] = None
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

def get_user_by_uid(uid):
    db = load_db()
    for u in db["users"]:
        if u.get("uid") == uid:
            return u
    return None

def get_match_by_rid(rid):
    db = load_db()
    for m in db["matches"]:
        if m.get("rid") == rid:
            return m
    return None

def check_suspended(email):
    user = get_user_by_email(email)
    if user and user.get("suspended_until"):
        try:
            sus = datetime.strptime(user["suspended_until"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < sus:
                return True, user["suspended_until"]
        except:
            pass
    return False, None

def execute_punishment(email, punishment):
    db = load_db()
    for u in db["users"]:
        if u["email"] == email:
            u["report_count"] = u.get("report_count", 0) + 1
            now = datetime.now()
            if punishment == "suspend 7 days":
                u["suspended_until"] = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            elif punishment == "suspend 2 weeks":
                u["suspended_until"] = (now + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
            elif punishment == "suspend a month":
                u["suspended_until"] = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            elif punishment == "suspend a year":
                u["suspended_until"] = (now + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
            break
    save_db(db)

def get_user_match_count(email):
    db = load_db()
    journal = load_journal()
    count = 0
    user = get_user_by_email(email)
    if not user:
        return 0
    full_name = f"{user['first_name']} {user['last_name']}"
    for j in journal:
        found = False
        for p in j.get("participants", []):
            if p.get("email", "").lower() == email.lower():
                found = True
                break
        if not found:
            for team in j.get("teams_data", []):
                for member in team.get("members", []):
                    if member.get("email", "").lower() == email.lower():
                        found = True
                        break
                if found:
                    break
        if not found:
            for team in j.get("teams", []):
                if full_name in team:
                    found = True
                    break
        if found:
            count += 1
    return count

def get_user_match_history(email):
    db = load_db()
    journal = load_journal()
    history = []
    user = get_user_by_email(email)
    if not user:
        return history
    full_name = f"{user['first_name']} {user['last_name']}"
    for j in journal:
        found = False
        for p in j.get("participants", []):
            if p.get("email", "").lower() == email.lower():
                found = True
                break
        if not found:
            for team in j.get("teams_data", []):
                for member in team.get("members", []):
                    if member.get("email", "").lower() == email.lower():
                        found = True
                        break
                if found:
                    break
        if not found:
            for team in j.get("teams", []):
                if full_name in team:
                    found = True
                    break
        if found:
            history.append(j)
    try:
        history.sort(key=lambda x: x.get("time", ""), reverse=True)
    except:
        pass
    return history

def get_judge_match_count(email):
    try:
        journal = load_journal()
        count = 0
        for j in journal:
            if j.get("judge_email", "").lower() == email.lower():
                count += 1
        return count
    except:
        return 0

def get_judge_history(email):
    journal = load_journal()
    history = []
    for j in journal:
        if j.get("judge_email", "").lower() == email.lower():
            history.append(j)
    try:
        history.sort(key=lambda x: x.get("time", ""), reverse=True)
    except:
        pass
    return history

def get_judge_pool():
    try:
        db = load_db()
    except:
        return []
    judges = []
    for u in db.get("users", []):
        if u.get("account_type") in ["student_judge", "professional_judge"]:
            try:
                judge_count = get_judge_match_count(u.get("email", ""))
            except:
                judge_count = 0
            judges.append({
                "name": f"{u.get('first_name', '')} {u.get('last_name', '')}",
                "email": u.get("email", ""),
                "uid": u.get("uid", ""),
                "account_type": u.get("account_type", "debater"),
                "level": u.get("level"),
                "avatar": u.get("avatar", ""),
                "color": u.get("color", "#4285F4"),
                "judge_count": judge_count
            })
    return judges

def extract_participants_from_team(team_str):
    participants = []
    db = load_db()
    team_clean = team_str.strip("()")
    names = [n.strip() for n in team_clean.split(",")]
    for name in names:
        if not name or name == "Waiting...":
            continue
        for u in db["users"]:
            full_name = f"{u['first_name']} {u['last_name']}"
            if full_name == name:
                participants.append({
                    "name": full_name,
                    "email": u["email"],
                    "uid": u.get("uid", "")
                })
                break
        else:
            participants.append({
                "name": name,
                "email": "",
                "uid": ""
            })
    return participants

def extract_participants_from_teams(match):
    participants = []
    db = load_db()
    for team in match.get("teams", []):
        team_clean = team.strip("()")
        names = [n.strip() for n in team_clean.split(",")]
        for name in names:
            if not name or name == "Waiting...":
                continue
            for u in db["users"]:
                full_name = f"{u['first_name']} {u['last_name']}"
                if full_name == name:
                    participants.append({
                        "name": full_name,
                        "email": u["email"],
                        "uid": u.get("uid", "")
                    })
                    break
            else:
                participants.append({
                    "name": name,
                    "email": "",
                    "uid": ""
                })
    return participants

# ========== ROUTES ==========

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
        if user:
            is_sus, sus_until = check_suspended(email)
            if is_sus:
                session.clear()
                flash(f"Account locked until {sus_until}")
                return redirect("/")

    filtered = []
    my_matches = []
    if user:
        full_name = f"{user['first_name']} {user['last_name']}"
        for m in db["matches"]:
            show = True
            if "level_restrict" in m:
                ul = user.get("level")
                ml = m.get("level")
                if ul is None or ml is None:
                    show = False
                else:
                    if ml in [1,2] and ul not in [1,2]: show = False
                    elif ml in [3,4] and ul not in [3,4]: show = False
                    elif ml in [5,6] and ul not in [5,6]: show = False
            if show:
                filtered.append(m)
            for team in m.get("teams", []):
                if full_name in team:
                    my_matches.append({"match": m, "rid": m.get("rid", "N/A")})
                    break
    else:
        filtered = db["matches"]

    utc8_offset = timedelta(hours=8)
    now_utc8 = datetime.now() + utc8_offset
    def sort_key(match):
        try:
            match_time = datetime.strptime(match["time"], "%Y-%m-%d %H:%M")
        except:
            try:
                match_time = datetime.strptime(match["time"], "%Y-%m-%dT%H:%M")
            except:
                return (float('inf'), 0)
        diff = abs((match_time - now_utc8).total_seconds())
        is_premium = 1 if match.get("premium") or match.get("official") else 0
        return (diff, -is_premium)
    filtered.sort(key=sort_key)
    my_matches.sort(key=lambda x: sort_key(x["match"]))

    evals = []
    pending_cv = 0
    pending_reports = 0
    reports = []
    journal = []
    judge_pool = []
    if user:
        if user["email"] == "ian@cactumatch.com":
            evals = load_evals()
            pending_cv = len(evals)
            all_reports = load_reports()
            pending_reports = len([r for r in all_reports if r["status"] in ["pending", "henry_reviewed"]])
            reports = all_reports
            journal = load_journal()
            judge_pool = get_judge_pool()
        elif user["email"] == "henry@cactumatch.com":
            all_reports = load_reports()
            pending_reports = len([r for r in all_reports if r["status"] == "pending"])
            reports = all_reports

    redeem_confirm_code = request.args.get("confirm_code")
    return render_template("index.html",
                          matches=filtered, my_matches=my_matches, user=user,
                          redeem_confirm_code=redeem_confirm_code,
                          evals=evals, pending_cv=pending_cv,
                          pending_reports=pending_reports, reports=reports,
                          db=db, journal=journal, judge_pool=judge_pool)

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
    evals, pending_cv, pending_reports, reports, journal, judge_pool = [], 0, 0, [], [], []
    if user["email"] == "ian@cactumatch.com":
        evals = load_evals()
        pending_cv = len(evals)
        reports = load_reports()
        pending_reports = len([r for r in reports if r["status"] in ["pending", "henry_reviewed"]])
        journal = load_journal()
        judge_pool = get_judge_pool()
    elif user["email"] == "henry@cactumatch.com":
        reports = load_reports()
        pending_reports = len([r for r in reports if r["status"] == "pending"])
    return render_template("index.html", user=user, matches=[], my_matches=[],
                          evals=evals, pending_cv=pending_cv,
                          pending_reports=pending_reports, reports=reports,
                          db=db, journal=journal, judge_pool=judge_pool)

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
        flash("Your premium account has not expired yet.")
        return redirect(f"/?confirm_code={code_str}")
    target["used"] = True
    target["used_by"] = email
    save_codes(codes)
    dur = target.get("duration", "1M")
    if dur == "7D": new_exp = now + timedelta(days=7)
    elif dur == "1M": new_exp = now + timedelta(days=30)
    elif dur == "3M": new_exp = now + timedelta(days=90)
    elif dur == "1Y": new_exp = now + timedelta(days=365)
    elif dur == "2Y": new_exp = now + timedelta(days=365*2)
    else: new_exp = now + timedelta(days=30)
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

@app.route('/api/user-info')
def api_user_info():
    email = request.args.get("email", "").strip()
    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    registered_date = user.get("registered_date", "")
    days_since = 0
    if registered_date:
        try:
            reg = datetime.strptime(registered_date, "%Y-%m-%d %H:%M:%S")
            days_since = (datetime.now() - reg).days
        except:
            pass
    try:
        match_count = get_user_match_count(email)
    except:
        match_count = 0
    try:
        judge_count = get_judge_match_count(email)
    except:
        judge_count = 0
    return jsonify({
        "name": f"{user['first_name']} {user['last_name']}",
        "level": user.get("level"),
        "days_since_joined": days_since,
        "match_count": match_count,
        "judge_count": judge_count,
        "uid": user.get("uid", ""),
        "avatar": user.get("avatar", ""),
        "color": user.get("color", "#4285F4"),
        "premium": user.get("premium", False),
        "account_type": user.get("account_type", "debater"),
        "is_judge": user.get("is_judge", False)
    })

@app.route('/api/user/<uid>/history')
def api_user_history(uid):
    if session.get("user") != "ian@cactumatch.com":
        return jsonify({"error": "Denied"}), 403
    user = get_user_by_uid(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    account_type = user.get("account_type", "debater")
    match_history = get_user_match_history(user["email"])
    judge_history = get_judge_history(user["email"]) if account_type in ["student_judge", "professional_judge"] else []
    judge_count = get_judge_match_count(user["email"])
    match_count = get_user_match_count(user["email"])
    return jsonify({
        "user": {
            "name": f"{user['first_name']} {user['last_name']}",
            "email": user["email"],
            "uid": uid,
            "level": user.get("level"),
            "avatar": user.get("avatar", ""),
            "color": user.get("color", "#4285F4"),
            "account_type": account_type
        },
        "match_history": match_history,
        "judge_history": judge_history,
        "match_count": match_count,
        "judge_count": judge_count
    })

@app.route('/api/judge-pool')
def api_judge_pool():
    if session.get("user") != "ian@cactumatch.com":
        return jsonify({"error": "Denied"}), 403
    return jsonify(get_judge_pool())

@app.route('/change-account-type', methods=['POST'])
def change_account_type():
    if session.get("user") != "ian@cactumatch.com":
        return "Denied", 403
    email = request.form["email"].strip()
    new_type = request.form["account_type"].strip()
    if new_type not in ACCOUNT_TYPES:
        flash("Invalid account type")
        return redirect("/")
    db = load_db()
    found = False
    for u in db["users"]:
        if u["email"] == email:
            u["account_type"] = new_type
            u["is_judge"] = (new_type in ["student_judge", "professional_judge"])
            found = True
            break
    if not found:
        flash("User not found")
        return redirect("/")
    save_db(db)
    flash(f"Changed {email} to {get_account_type_label(new_type)}")
    return redirect("/")

@app.route('/login', methods=['POST'])
def login():
    email = request.form["email"].strip().lower()
    pwd = request.form["password"].strip()
    is_sus, sus_until = check_suspended(email)
    if is_sus:
        flash(f"Account locked until {sus_until}")
        return redirect("/")
    db = load_db()
    if email == "henry@cactumatch.com" and pwd == "cactumatch2026":
        found = False
        for u in db["users"]:
            if u["email"] == email:
                found = True
                break
        if not found:
            new_user = {"email": email, "password": pwd, "first_name": "Henry", "last_name": "Reviewer", "avatar": "", "color": get_color(email), "premium": True, "premium_expire": None, "is_judge": False, "account_type": "debater", "level": None, "cv": "", "cv_last_update": None, "cv_status": "approved", "report_count": 0, "suspended_until": None, "uid": generate_uid(), "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            db["users"].append(new_user)
            save_db(db)
        session["user"] = email
        return redirect("/")
    if email in SUPER_ADMINS and pwd == SUPER_ADMINS[email]:
        for u in db["users"]:
            if u["email"] == email:
                session["user"] = email
                return redirect("/")
        new_user = {"email": email, "password": pwd, "first_name": "Ian", "last_name": "Admin", "avatar": "", "color": get_color(email), "premium": True, "premium_expire": None, "is_judge": False, "account_type": "debater", "level": 6, "cv": "ROOT", "cv_last_update": None, "cv_status": "approved", "report_count": 0, "suspended_until": None, "uid": generate_uid(), "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        db["users"].append(new_user)
        save_db(db)
        session["user"] = email
        return redirect("/")
    if email in ADMIN_USERS and pwd == ADMIN_USERS[email]:
        for u in db["users"]:
            if u["email"] == email:
                session["user"] = email
                return redirect("/")
        new_user = {"email": email, "password": pwd, "first_name": "Round", "last_name": "Manager", "avatar": "", "color": get_color(email), "premium": False, "premium_expire": None, "is_judge": False, "account_type": "debater", "level": None, "cv": "", "cv_last_update": None, "cv_status": "pending", "report_count": 0, "suspended_until": None, "uid": generate_uid(), "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
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

@app.route('/update-cv', methods=['POST'])
def update_cv():
    if "user" not in session:
        return redirect("/")
    email = session["user"]
    if email in ["ian@cactumatch.com", "henry@cactumatch.com", "roundmanager@cactumatch.com"]:
        flash("Admin does not need to update CV")
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
    if not user or (user.get("account_type") not in ["debater"] and user["email"] not in SUPER_ADMINS and user["email"] not in ADMIN_USERS):
        flash("Only debaters can post matches")
        return redirect("/")
    match_type = request.form["type"]
    teammate_email = request.form.get("teammate_email", "").strip()
    no_account = request.form.get("no_account") == "on"
    teammate_name = request.form.get("teammate_name", "").strip()
    restrict = request.form.get("level_restrict") == "on"
    note = request.form.get("note", "").strip()
    if user["email"] != "ian@cactumatch.com":
        note = note[:120]
    judge_type_restriction = request.form.get("judge_type_restriction", "any")
    if judge_type_restriction not in ["any", "student_judge", "professional_judge"]:
        judge_type_restriction = "any"
    official = request.form.get("official") == "on" and user["email"] == "ian@cactumatch.com"

    if user["email"] == "ian@cactumatch.com":
        team = "(Waiting...)"
    elif no_account and teammate_name:
        team = f"({user['first_name']} {user['last_name']}, {teammate_name})"
    elif not no_account and teammate_email:
        teammate_user = get_user_by_email(teammate_email)
        if teammate_user:
            team = f"({user['first_name']} {user['last_name']}, {teammate_user['first_name']} {teammate_user['last_name']})"
        else:
            team = f"({user['first_name']} {user['last_name']}, {teammate_email})"
    else:
        team = f"({user['first_name']} {user['last_name']})"

    rid = generate_rid()
    match_time = request.form["time"].replace("T", " ")

    match = {
        "rid": rid,
        "author": user["email"],
        "author_name": f"{user['first_name']} {user['last_name']}",
        "type": match_type,
        "time": match_time,
        "platform": request.form["platform"],
        "judge": request.form.get("judge", "").strip() or "Not specified",
        "judge_email": "",
        "meeting_id": request.form["meeting_id"],
        "meeting_pwd": request.form["meeting_pwd"],
        "teams": [team],
        "premium": user.get("premium", False),
        "note": note,
        "official": official,
        "judge_type_restriction": judge_type_restriction,
        "participants": [],
        "teams_data": []
    }
    if restrict and user.get("level"):
        match["level_restrict"] = True
        match["level"] = user["level"]

    match["participants"] = extract_participants_from_teams(match)
    match["teams_data"] = [{"team_index": i, "members": extract_participants_from_team(t)} for i, t in enumerate(match["teams"])]

    db["matches"].append(match)
    save_db(db)
    add_journal_entry(match)
    flash(f"Match posted! RID: {rid}")
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
    if not user:
        return redirect("/")

    if user.get("account_type") in ["student_judge", "professional_judge"]:
        restriction = match.get("judge_type_restriction", "any")
        if restriction not in ["any", "student_judge", "professional_judge"]:
            restriction = "any"
        if restriction != "any" and restriction != user.get("account_type"):
            required = "Student Judge" if restriction == "student_judge" else "Professional Judge"
            flash(f"This match requires a {required}")
            return redirect("/")
        judge_name = f"{user['first_name']} {user['last_name']}"
        match["judge"] = judge_name
        match["judge_email"] = email
        save_db(db)
        match["participants"] = extract_participants_from_teams(match)
        add_journal_entry(match)
        flash(f"Judge {judge_name} has joined the match!")
        return redirect("/")

    full_name = f"{user['first_name']} {user['last_name']}"
    for team in match["teams"]:
        if full_name in team:
            flash("You already joined this match")
            return redirect("/")

    match_type = match.get("type", "")

    if match_type == "LD":
        if len(match["teams"]) >= 2:
            flash("LD match is full")
            return redirect("/")
        team = f"({full_name})"
        if match["teams"][0] == "(Waiting...)":
            match["teams"][0] = team
        else:
            match["teams"].append(team)
    else:
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

    match["participants"] = extract_participants_from_teams(match)
    match["teams_data"] = [{"team_index": i, "members": extract_participants_from_team(t)} for i, t in enumerate(match["teams"])]
    save_db(db)
    add_journal_entry(match)
    flash("Successfully joined the match!")
    return redirect("/")

@app.route('/report/<rid>', methods=['POST'])
def report(rid):
    if "user" not in session:
        return redirect("/")
    reason = request.form["reason"]
    details = request.form.get("details", "").strip()
    reports = load_reports()
    report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
    reports.append({
        "id": report_id, "rid": rid, "reporter": session["user"],
        "reason": reason, "details": details,
        "status": "pending", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_reports(reports)
    flash("Report submitted")
    return redirect("/")

@app.route('/henry-review/<report_id>', methods=['POST'])
def henry_review(report_id):
    if session.get("user") != "henry@cactumatch.com":
        return "Denied", 403
    action = request.form.get("action")
    punish_who = request.form.get("punish_who")
    punishment = request.form.get("punishment")
    reports = load_reports()
    db = load_db()
    target = None
    for r in reports:
        if r["id"] == report_id:
            target = r
            break
    if not target:
        return redirect("/")
    match = get_match_by_rid(target["rid"])
    if not match:
        flash("Match not found")
        return redirect("/")
    if action == "pass":
        target["status"] = "dismissed"
        target["henry_decision"] = "dismissed"
        save_reports(reports)
        flash("Report dismissed")
        return redirect("/")
    punished_email = ""
    if punish_who == "reporter":
        punished_email = target["reporter"]
    elif punish_who == "creator":
        punished_email = match.get("author", "")
    elif punish_who == "judge":
        if match.get("judge_email"):
            punished_email = match["judge_email"]
        else:
            judge_name = match.get("judge", "")
            for u in db["users"]:
                if f"{u['first_name']} {u['last_name']}" == judge_name:
                    punished_email = u["email"]
                    break
    if not punished_email:
        flash("Could not determine who to punish")
        return redirect("/")
    punished_user = get_user_by_email(punished_email)
    is_first_report = (punished_user and punished_user.get("report_count", 0) == 0)
    if is_first_report:
        target["status"] = "henry_reviewed"
        target["henry_decision"] = {"type": "first_offense", "punished_email": punished_email, "reporter": target["reporter"]}
        save_reports(reports)
        flash("First offense - escalated to Ian for review")
        return redirect("/")
    if punishment in ["suspend a month", "suspend a year"]:
        target["status"] = "henry_reviewed"
        target["henry_decision"] = {"punish_who": punish_who, "punished_email": punished_email, "punishment": punishment}
        save_reports(reports)
        flash("Severe punishment - escalated to Ian for final review")
        return redirect("/")
    execute_punishment(punished_email, punishment)
    target["status"] = "resolved"
    target["henry_decision"] = {"punish_who": punish_who, "punished_email": punished_email, "punishment": punishment}
    save_reports(reports)
    flash(f"Punishment executed: {punished_email} - {punishment}")
    return redirect("/")

@app.route('/ian-review/<report_id>', methods=['POST'])
def ian_review(report_id):
    if session.get("user") != "ian@cactumatch.com":
        return "Denied", 403
    action = request.form.get("action")
    punishment = request.form.get("punishment", "")
    punished_email = request.form.get("punished_email", "")
    reports = load_reports()
    target = None
    for r in reports:
        if r["id"] == report_id:
            target = r
            break
    if not target:
        return redirect("/")
    if action == "dismiss":
        target["status"] = "dismissed"
        target["ian_decision"] = "dismissed"
    else:
        if punishment and punished_email:
            execute_punishment(punished_email, punishment)
            target["status"] = "resolved"
            target["ian_decision"] = {"punishment": punishment, "punished_email": punished_email}
    save_reports(reports)
    flash("Ian review completed")
    return redirect("/")

@app.route('/delete/<int:idx>')
def delete(idx):
    user = session.get("user")
    if user not in SUPER_ADMINS and user not in ADMIN_USERS:
        return redirect("/")
    db = load_db()
    if 0 <= idx < len(db["matches"]):
        rid = db["matches"][idx].get("rid", "")
        del db["matches"][idx]
        save_db(db)
        if rid:
            complete_journal_entry(rid)
    return redirect("/")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

@app.route('/register', methods=['POST'])
def register():
    email = request.form["email"].strip().lower()
    pwd = request.form["password"].strip()
    first = request.form["first_name"].strip()
    last = request.form["last_name"].strip()
    account_type = request.form.get("account_type", "debater").strip()
    if account_type not in ACCOUNT_TYPES:
        account_type = "debater"
    cv = request.form["cv"].strip()
    db = load_db()
    for u in db["users"]:
        if u["email"] == email:
            flash("Email already exists")
            return redirect("/")
    new_user = {
        "email": email, "password": pwd, "first_name": first, "last_name": last,
        "avatar": "", "color": get_color(email), "premium": False, "premium_expire": None,
        "is_judge": (account_type in ["student_judge", "professional_judge"]),
        "account_type": account_type, "level": None, "cv": cv,
        "cv_last_update": None, "cv_status": "pending", "report_count": 0,
        "suspended_until": None, "uid": generate_uid(),
        "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db["users"].append(new_user)
    save_db(db)
    ev = {"email": email, "name": f"{first} {last}", "cv": cv, "type": "pre", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
    evals = load_evals()
    evals.append(ev)
    save_evals(evals)
    flash("You successfully created an account, please log in")
    return redirect("/?registered=success")

@app.route('/debug/rebuild-journal')
def rebuild_journal():
    if session.get("user") != "ian@cactumatch.com":
        return "Denied", 403
    db = load_db()
    journal = load_journal()
    existing_rids = {j["rid"] for j in journal}
    count = 0
    for m in db["matches"]:
        if m.get("rid") not in existing_rids:
            if not m.get("participants"):
                m["participants"] = extract_participants_from_teams(m)
            if not m.get("teams_data"):
                m["teams_data"] = [{"team_index": i, "members": extract_participants_from_team(t)} for i, t in enumerate(m.get("teams", []))]
            add_journal_entry(m)
            count += 1
    flash(f"Rebuilt {count} journal entries")
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
