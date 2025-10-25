import os, json, datetime
import streamlit as st
from firebase_admin import firestore, credentials, initialize_app
import firebase_admin

# ---------------- APP CONFIG ----------------
st.set_page_config(page_title="Pregnancy Dashboard", page_icon="👶", layout="wide")
PROJECT_ROOT = "aslam_pregnancy_planner"  # must match desktop app Firestore path

# ---------------- FIREBASE INIT ----------------
if "FIREBASE_KEY" not in st.secrets:
    st.error("❌ FIREBASE_KEY missing in Streamlit Secrets.\nAdd your service key JSON under 'Secrets'.")
    st.stop()

# Convert FIREBASE_KEY TOML section into Python dict
firebase_key = dict(st.secrets["FIREBASE_KEY"])

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key)
    initialize_app(cred)

db = firestore.client()

# ---------------- ACCESS CONTROL ----------------
# Only allow these emails
ALLOWED_USERS = {"wasimk14@gmail.com", "h33na.ansari@gmail.com"}

if "email" not in st.session_state:
    # Streamlit Cloud provides this
    email = st.experimental_user.email if hasattr(st.experimental_user, 'email') else None
    st.session_state.email = email

email = st.session_state.email
if not email or email not in ALLOWED_USERS:
    st.error("🚫 Access Denied — Please sign in with your approved Google account.")
    st.stop()

st.write(f"✅ Logged in as: **{email}**")

# ---------------- DATA FETCHERS ----------------
def get_tasks():
    docs = db.collection(PROJECT_ROOT).document("tasks").collection("items").stream()
    tasks = []
    for d in docs:
        x = d.to_dict()
        x["id"] = d.id
        tasks.append(x)
    return tasks

def get_appts():
    docs = db.collection(PROJECT_ROOT).document("appointments").collection("items").stream()
    appts = []
    for d in docs:
        x = d.to_dict()
        x["id"] = d.id
        appts.append(x)
    return appts

def get_activity():
    docs = (
        db.collection(PROJECT_ROOT)
        .document("activity")
        .collection("entries")
        .order_by("ts", direction=firestore.Query.DESCENDING)
        .limit(200)
        .stream()
    )
    rows = []
    for d in docs:
        x = d.to_dict()
        ts = x.get("ts")
        if hasattr(ts, "to_datetime"):
            x["ts"] = ts.to_datetime().strftime("%Y-%m-%d %H:%M:%S")
        rows.append(x)
    return rows

# ---------------- UI LAYOUT ----------------
st.title("👶 Pregnancy Planner Dashboard")

today = datetime.date.today().isoformat()
tasks = get_tasks()
appts = get_appts()
activity = get_activity()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("✅ Today's Checklist")
    todays_tasks = [t for t in tasks if t.get("date") == today]
    if not todays_tasks:
        st.info("No tasks for today.")
    else:
        done = sum(1 for t in todays_tasks if t.get("completed"))
        st.progress(done / len(todays_tasks))
        for t in todays_tasks:
            mark = "✅" if t.get("completed") else "⬜"
            st.write(f"{mark} {t.get('task')}")

with col2:
    st.subheader("🩺 Appointments")
    upcoming = []
    now = datetime.datetime.now()
    for a in appts:
        try:
            d, t = a["date"], a["time"]
            y, m, dd = map(int, d.split("-"))
            hh, mm = map(int, t.split(":"))
            dt = datetime.datetime(y, m, dd, hh, mm)
            if dt >= now - datetime.timedelta(hours=1):
                upcoming.append((dt, a))
        except:
            continue
    if not upcoming:
        st.write("No upcoming appointments.")
    else:
        for dt, a in sorted(upcoming):
            st.write(f"**{a['date']} {a['time']}** — {a.get('note','')}")

# ---------------- Activity Feed ----------------
st.subheader("📊 Recent Activity")
for r in activity[:20]:
    ts = r.get("ts","")
    user = r.get("user","?")
    act = r.get("action","")
    meta = r.get("meta","")
    st.write(f"{ts} · **{user}** · {act} · {meta}")


