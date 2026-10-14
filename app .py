import sqlite3
import secrets
from datetime import datetime, date, time
from io import BytesIO
from pathlib import Path

import pandas as pd
import qrcode
import streamlit as st

import style

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "campuspulse.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="CampusPulse", page_icon="🎓", layout="wide")
style.inject_css()

# ---------------------------- Database ----------------------------
def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            venue TEXT NOT NULL,
            organizer TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 100,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            student_email TEXT NOT NULL,
            ticket_code TEXT NOT NULL UNIQUE,
            checked_in INTEGER NOT NULL DEFAULT 0,
            registered_at TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(id)
        );
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            note TEXT,
            decided_by TEXT NOT NULL,
            decided_at TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(id)
        );
        """)

def seed_demo():
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            today = date.today()
            demo_events = [
                ("CodeSprint 2026", "Technology", "A fast-paced 4-hour coding challenge for campus teams.", (today.replace(day=min(today.day + 3, 28))).isoformat(), "09:30", "14:00", "Innovation Lab", "Coding Club", 120, "Approved"),
                ("CircuitVerse: Embedded Systems", "Workshop", "Hands-on Arduino, sensors, and embedded prototyping session.", (today.replace(day=min(today.day + 5, 28))).isoformat(), "10:00", "13:00", "ECE Lab 2", "ECE Association", 60, "Approved"),
                ("Open Mic Evening", "Cultural", "Music, poetry, and stand-up performances by students.", (today.replace(day=min(today.day + 7, 28))).isoformat(), "16:00", "18:30", "Main Auditorium", "Arts Circle", 180, "Pending"),
            ]
            for row in demo_events:
                conn.execute("""INSERT INTO events
                    (title, category, description, event_date, start_time, end_time, venue,
                     organizer, capacity, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*row, datetime.now().isoformat(timespec="seconds")))

init_db()
seed_demo()

# ---------------------------- Helpers ----------------------------
def get_events(status=None):
    with connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM events WHERE status=? ORDER BY event_date, start_time", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY event_date, start_time").fetchall()
    return [dict(r) for r in rows]

def get_event(event_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return dict(row) if row else None

def registration_count(event_id):
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM registrations WHERE event_id=?", (event_id,)).fetchone()[0]

def make_qr(code):
    img = qrcode.make(code)
    output = BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()

def venue_conflicts(venue, event_date, start_time, end_time, exclude_id=None):
    # Overlap rule: existing_start < new_end AND existing_end > new_start
    sql = """SELECT * FROM events
             WHERE lower(venue)=lower(?) AND event_date=?
             AND status IN ('Pending', 'Approved')
             AND start_time < ? AND end_time > ?"""
    params = [venue.strip(), event_date, end_time, start_time]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def add_approval(event_id, decision, note, decided_by):
    with connect() as conn:
        conn.execute("UPDATE events SET status=? WHERE id=?", (decision, event_id))
        conn.execute("""INSERT INTO approvals(event_id, decision, note, decided_by, decided_at)
                         VALUES (?, ?, ?, ?, ?)""",
                     (event_id, decision, note, decided_by, datetime.now().isoformat(timespec="seconds")))

def page_header():
    style.hero()

page_header()

NAV_ICONS = {
    "Discover events": "🔎", "Host an event": "📣", "Approvals": "✅",
    "Check-in desk": "📲", "Analytics": "📈",
}

with st.sidebar:
    style.render("""
    <div class="side-brand">
      <div class="logo">🎓</div>
      <div><b>CampusPulse</b><small>Events, end to end</small></div>
    </div>
    """)
    page = st.radio("Open workspace", list(NAV_ICONS),
                    format_func=lambda p: f"{NAV_ICONS[p]}  {p}")
    st.divider()
    st.caption("SYNESIS 26 • Demo build")
    st.caption("Demo data is stored locally in SQLite.")

# ---------------------------- Student discovery ----------------------------
if page == "Discover events":
    style.section("Find your next campus experience", "Browse approved events, grab a seat, and get a QR ticket in seconds.")
    events = get_events("Approved")
    if not events:
        st.info("No approved events yet. Check back later.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            search = st.text_input("Search events", placeholder="Try coding, music, workshop…")
        with c2:
            categories = ["All"] + sorted(set(e["category"] for e in events))
            category = st.selectbox("Category", categories)
        filtered = [e for e in events
                    if search.lower() in (e["title"] + " " + e["description"] + " " + e["venue"]).lower()
                    and (category == "All" or e["category"] == category)]
        if not filtered:
            st.warning("No events match those filters.")
        for event in filtered:
            registered = registration_count(event["id"])
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    style.render(style.event_head(event))
                with right:
                    style.render(style.seats_html(event["capacity"], registered))
                    with st.expander("🎟️ Register"):
                        with st.form(f"register_{event['id']}"):
                            student_name = st.text_input("Your name", key=f"name_{event['id']}")
                            student_email = st.text_input("College email", key=f"email_{event['id']}")
                            submitted = st.form_submit_button("Get my QR ticket", type="primary")
                            if submitted:
                                if not student_name.strip() or "@" not in student_email:
                                    st.error("Enter your name and a valid email address.")
                                elif registered >= event["capacity"]:
                                    st.error("This event is full.")
                                else:
                                    with connect() as conn:
                                        existing = conn.execute(
                                            "SELECT id FROM registrations WHERE event_id=? AND lower(student_email)=lower(?)",
                                            (event["id"], student_email.strip())).fetchone()
                                        if existing:
                                            st.warning("This email is already registered for this event.")
                                        else:
                                            code = "CP-" + secrets.token_hex(5).upper()
                                            conn.execute("""INSERT INTO registrations
                                                (event_id, student_name, student_email, ticket_code, registered_at)
                                                VALUES (?, ?, ?, ?, ?)""",
                                                (event["id"], student_name.strip(), student_email.strip(), code,
                                                 datetime.now().isoformat(timespec="seconds")))
                                            st.session_state["latest_ticket"] = {
                                                "event": event["title"], "name": student_name.strip(), "code": code,
                                                "category": event["category"],
                                                "meta": f"{event['event_date']}, {event['start_time']} at {event['venue']}",
                                            }
                                            st.success("Registration successful. Your ticket is ready below.")
                                            st.balloons()
    ticket = st.session_state.get("latest_ticket")
    if ticket:
        st.divider()
        st.subheader("Your latest ticket")
        style.render(style.ticket_html(ticket, make_qr(ticket["code"])))
        st.download_button("Download QR ticket", make_qr(ticket["code"]),
                           file_name=f"{ticket['code']}.png", mime="image/png")

# ---------------------------- Organizer event creation ----------------------------
elif page == "Host an event":
    style.section("Create an event", "Add the details, or upload a poster as a reference. We check the venue for clashes before it goes for approval.")
    uploaded = st.file_uploader("Optional event poster (PNG/JPG/PDF)", type=["png", "jpg", "jpeg", "pdf"])
    if uploaded:
        safe_name = Path(uploaded.name).name.replace(" ", "_")
        (UPLOAD_DIR / safe_name).write_bytes(uploaded.getvalue())
        st.success(f"Poster saved locally as uploads/{safe_name}. Fill the form below using its details.")
        if uploaded.type.startswith("image/"):
            st.image(uploaded, caption="Uploaded poster")
    with st.form("create_event"):
        title = st.text_input("Event title *")
        category = st.selectbox("Category", ["Technology", "Workshop", "Cultural", "Sports", "Career", "Other"])
        description = st.text_area("Description")
        col1, col2, col3 = st.columns(3)
        with col1:
            event_date = st.date_input("Event date", min_value=date.today())
        with col2:
            start = st.time_input("Start time", value=time(10, 0))
        with col3:
            end = st.time_input("End time", value=time(12, 0))
        col4, col5 = st.columns(2)
        with col4:
            venue = st.text_input("Venue *", placeholder="e.g. Main Auditorium")
        with col5:
            organizer = st.text_input("Organizer / club *", placeholder="e.g. ECE Association")
        capacity = st.number_input("Maximum attendees", min_value=1, max_value=5000, value=100, step=10)
        submit = st.form_submit_button("Submit for approval", type="primary")
        if submit:
            if not title.strip() or not venue.strip() or not organizer.strip():
                st.error("Please complete the title, venue, and organizer fields.")
            elif end <= start:
                st.error("End time must be later than start time.")
            else:
                conflicts = venue_conflicts(venue, event_date.isoformat(), start.strftime("%H:%M"), end.strftime("%H:%M"))
                if conflicts:
                    st.error("Potential venue conflict detected. Review the events below before submitting.")
                    for c in conflicts:
                        st.write(f"• {c['title']} — {c['start_time']}–{c['end_time']} ({c['status']})")
                    st.info("Try another venue or time slot. This demo blocks submission when a conflict is detected.")
                else:
                    with connect() as conn:
                        conn.execute("""INSERT INTO events
                            (title, category, description, event_date, start_time, end_time, venue,
                             organizer, capacity, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)""",
                            (title.strip(), category, description.strip(), event_date.isoformat(),
                             start.strftime("%H:%M"), end.strftime("%H:%M"), venue.strip(),
                             organizer.strip(), int(capacity), datetime.now().isoformat(timespec="seconds")))
                    st.success("Event submitted for approval.")

# ---------------------------- Approval workflow ----------------------------
elif page == "Approvals":
    style.section("Event approval queue", "Review each request, leave a note, and approve or reject. Every decision is kept in the history below.")
    pending = get_events("Pending")
    if not pending:
        st.success("No pending events.")
    for event in pending:
        with st.container(border=True):
            style.render(style.event_head(event, show_status=True))
            with st.form(f"approval_{event['id']}"):
                note = st.text_input("Approval note (optional)", key=f"note_{event['id']}")
                reviewer = st.text_input("Reviewer name", value="Campus Admin", key=f"reviewer_{event['id']}")
                approve_col, reject_col = st.columns(2)
                approve = approve_col.form_submit_button("Approve event", type="primary")
                reject = reject_col.form_submit_button("Reject event")
                if approve or reject:
                    decision = "Approved" if approve else "Rejected"
                    add_approval(event["id"], decision, note.strip(), reviewer.strip() or "Campus Admin")
                    st.success(f"{event['title']} marked {decision.lower()}.")
                    st.rerun()
    with connect() as conn:
        history = pd.read_sql_query("""SELECT a.event_id, e.title, a.decision, a.note, a.decided_by, a.decided_at
                                       FROM approvals a JOIN events e ON e.id=a.event_id
                                       ORDER BY a.decided_at DESC""", conn)
    if not history.empty:
        st.subheader("Approval history")
        st.dataframe(history, use_container_width=True, hide_index=True)

# ---------------------------- Check-in ----------------------------
elif page == "Check-in desk":
    style.section("QR ticket check-in", "Type or paste the ticket code shown under the QR to let someone in.")
    code = st.text_input("Ticket code", placeholder="e.g. CP-A1B2C3D4E5")
    if st.button("Validate and check in", type="primary"):
        with connect() as conn:
            row = conn.execute("""SELECT r.*, e.title, e.status FROM registrations r
                                  JOIN events e ON e.id=r.event_id WHERE upper(r.ticket_code)=upper(?)""",
                               (code.strip(),)).fetchone()
            if not row:
                st.error("Ticket not found. Check the code and try again.")
            elif row["status"] != "Approved":
                st.error("This event is not approved; check-in is disabled.")
            elif row["checked_in"]:
                st.warning(f"Already checked in: {row['student_name']} — {row['title']}.")
            else:
                conn.execute("UPDATE registrations SET checked_in=1 WHERE id=?", (row["id"],))
                st.success(f"Check-in successful: {row['student_name']} for {row['title']}.")
                st.balloons()
    with connect() as conn:
        recent = pd.read_sql_query("""SELECT e.title AS Event, r.student_name AS Attendee,
                                      r.ticket_code AS Ticket, r.checked_in AS CheckedIn
                                      FROM registrations r JOIN events e ON e.id=r.event_id
                                      ORDER BY r.registered_at DESC LIMIT 20""", conn)
    if not recent.empty:
        st.subheader("Recent registrations")
        st.dataframe(recent, use_container_width=True, hide_index=True)

# ---------------------------- Analytics ----------------------------
elif page == "Analytics":
    style.section("Organizer analytics", "Registrations, check-ins and the approval pipeline at a glance.")
    with connect() as conn:
        events_df = pd.read_sql_query("SELECT * FROM events ORDER BY event_date", conn)
        regs_df = pd.read_sql_query("""SELECT r.*, e.title AS event_title, e.status AS event_status
                                      FROM registrations r JOIN events e ON e.id=r.event_id""", conn)
    total_events = len(events_df)
    total_regs = len(regs_df)
    checked = int(regs_df["checked_in"].sum()) if not regs_df.empty else 0
    approved = int((events_df["status"] == "Approved").sum()) if not events_df.empty else 0
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        style.render(style.tile("Total events", total_events, "🗓️", "#8b5cf6"))
    with m2:
        style.render(style.tile("Approved events", approved, "✅", "#4ade80"))
    with m3:
        style.render(style.tile("Registrations", total_regs, "🎟️", "#f472b6"))
    with m4:
        style.render(style.tile("Check-ins", checked, "📲", "#22d3ee"))
    if not regs_df.empty:
        summary = regs_df.groupby("event_title").agg(
            Registrations=("id", "count"),
            CheckIns=("checked_in", "sum")
        ).reset_index().rename(columns={"event_title": "Event"})
        summary["Check-in rate (%)"] = (summary["CheckIns"] / summary["Registrations"] * 100).round(1)
        st.subheader("Attendance by event")
        st.bar_chart(summary.set_index("Event")[["Registrations", "CheckIns"]], color=["#f472b6", "#22d3ee"])
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.info("Register for an event to populate attendance analytics.")
    if not events_df.empty:
        st.subheader("Event pipeline")
        st.bar_chart(events_df["status"].value_counts(), color="#8b5cf6")
        st.dataframe(events_df[["id", "title", "category", "event_date", "venue", "status"]], use_container_width=True, hide_index=True)

st.divider()
st.caption("CampusPulse prototype • Educational hackathon demo • Do not use real student data in this demo.")
