# dashboard_app.py
import os, datetime
import streamlit as st

# Firestore (admin) – uses your local JSON path via env var
from firebase_admin import firestore, credentials, initialize_app
import firebase_admin

# ------------------ CONFIG ------------------ #
PROJECT_ROOT = "aslam_pregnancy_planner"  # must match desktop app
KEY_PATH = os.getenv("FIREBASE_KEY_PATH", r"C:\Aslam\Docs\pregnancy-planner-d9ef9-firebase-adminsdk-fbsvc-dc33fb0f0a.json")

# ------------------ INIT FIREBASE ------------------ #
if not firebase_admin._apps:
    if not os.path.exists(KEY_PATH):
        st.error("FIREBASE_KEY_PATH is not set or file not found.\n\nSet env var FIREBASE_KEY_PATH to your service account JSON path.")
        st.stop()
    cred = credentials.Certificate(KEY_PATH)
    initialize_app(cred)

db = firestore.client()

# ------------------ UI ------------------ #
st.set_page_config(page_title="Pregnancy Planner Dashboard", page_icon="👶", layout="wide")
st.title("👶 Pregnancy Planner — Family Dashboard")

# Helper to fetch docs
def fetch_tasks():
    docs = db.collection(PROJECT_ROOT).document("tasks").collection("items").stream()
    rows = []
    for d in docs:
        x = d.to_dict()
        x["id"] = d.id
        rows.append(x)
    return rows

def fetch_appts():
    docs = db.collection(PROJECT_ROOT).document("appointments").collection("items").stream()
    rows = []
    for d in docs:
        x = d.to_dict()
        x["id"] = d.id
        rows.append(x)
    return rows

def fetch_activity(limit=200):
    docs = db.collection(PROJECT_ROOT).document("activity").collection("entries")\
             .order_by("ts", direction=firestore.Query.DESCENDING).limit(limit).stream()
    rows = []
    for d in docs:
        x = d.to_dict()
        # Convert Firestore Timestamp → string
        ts = x.get("ts")
        if hasattr(ts, "to_datetime"):
            x["ts"] = ts.to_datetime().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        rows.append(x)
    return rows

with st.sidebar:
    st.header("Filters")
    today = datetime.date.today().isoformat()
    scope = st.selectbox("Range", ["Today", "This Week", "All"], index=0)
    who = st.selectbox("User", ["Everyone", "Aslam", "Wife"], index=0)
    st.info("Access is restricted by Streamlit’s share list (Google login).")

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("✅ Today’s Checklist")
    tasks = fetch_tasks()
    # Filter tasks for today
    tday = [t for t in tasks if t.get("date") == today]
    if who != "Everyone":
        # optional: if you later write 'owner' into tasks, filter here
        pass
    if not tday:
        st.write("No tasks found for today yet.")
    else:
        done = sum(1 for t in tday if t.get("completed"))
        st.progress(min(1.0, done / max(1, len(tday))))
        for t in sorted(tday, key=lambda x: (x.get("completed"), x.get("id"))):
            mark = "✅" if t.get("completed") else "⬜"
            st.write(f"{mark} {t.get('task')}  ·  *{t.get('category','General')}*")

with col2:
    st.subheader("🩺 Appointments (upcoming)")
    appts = fetch_appts()
    # Sort & show upcoming
    def to_dt(a):
        try:
            d, t = a.get("date",""), a.get("time","00:00")
            y,m,dd = map(int, d.split("-"))
            hh,mm = map(int, t.split(":"))
            return datetime.datetime(y,m,dd,hh,mm)
        except:
            return datetime.datetime.max
    appts = sorted(appts, key=to_dt)
    upcoming = [a for a in appts if to_dt(a) >= datetime.datetime.now() - datetime.timedelta(minutes=5)]
    if not upcoming:
        st.write("No upcoming appointments.")
    else:
        for a in upcoming[:10]:
            when = f"{a.get('date')} {a.get('time')}"
            st.write(f"**{when}** — {a.get('note','(no note)')}")

with col3:
    st.subheader("📊 Activity (latest)")
    # Range filter
    rows = fetch_activity(limit=300)
    now = datetime.datetime.now()
    def in_scope(ts_str):
        try:
            ts = datetime.datetime.fromisoformat(ts_str)
        except:
            return True
        if scope == "All": return True
        if scope == "This Week": return (now - ts).days <= 7
        return ts.date() == now.date()
    if who != "Everyone":
        rows = [r for r in rows if r.get("user") == who]
    rows = [r for r in rows if in_scope(r.get("ts", ""))]
    if not rows:
        st.write("No activity yet.")
    else:
        for r in rows[:30]:
            st.write(f"{r.get('ts','')} · **{r.get('user','?')}** · {r.get('action','')} · {r.get('meta','')}")
