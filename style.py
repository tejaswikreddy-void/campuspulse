"""CampusPulse visual layer.

Only looks live here: CSS and small HTML helpers. No database or app logic.
Everything user-typed goes through esc() so a stray < or $ can never break a card.
"""
import base64
from datetime import datetime
from html import escape

import streamlit as st

# One colour per category, so the feed reads at a glance.
CATEGORY_COLORS = {
    "Technology": "#22d3ee",
    "Workshop": "#fbbf24",
    "Cultural": "#f472b6",
    "Sports": "#4ade80",
    "Career": "#60a5fa",
    "Other": "#a78bfa",
}
STATUS_COLORS = {"Approved": "#4ade80", "Pending": "#fbbf24", "Rejected": "#fb7185"}
DEFAULT_COLOR = "#a78bfa"


# ---------------------------- small helpers ----------------------------
def esc(value):
    """Make any value safe to put inside our HTML (one line, no markdown surprises)."""
    text = " ".join(str(value if value is not None else "").split())
    return escape(text).replace("$", "&#36;")


def _clean(html):
    # Streamlit treats blank lines / 4-space indents as markdown code blocks.
    # Strip both so our HTML always renders as HTML.
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def render(html):
    st.markdown(_clean(html), unsafe_allow_html=True)


def category_color(category):
    return CATEGORY_COLORS.get(category, DEFAULT_COLOR)


def chip(text, color):
    return f'<span class="chip" style="--c:{color}">{esc(text)}</span>'


def _date_parts(iso_date):
    try:
        d = datetime.strptime(str(iso_date), "%Y-%m-%d")
        return str(d.day), d.strftime("%b")
    except ValueError:
        return "•", ""


# ---------------------------- page pieces ----------------------------
def hero():
    render("""
    <div class="hero">
      <div>
        <div class="brand">CampusPulse</div>
        <div class="sub">Discover better. Organize smarter. Connect campus.</div>
      </div>
      <svg class="ecg" viewBox="0 0 400 64" aria-hidden="true">
        <path class="base" pathLength="1" d="M0 36 H120 L136 36 L146 10 L160 58 L172 30 L180 36 H400"/>
        <path class="beat" pathLength="1" d="M0 36 H120 L136 36 L146 10 L160 58 L172 30 L180 36 H400"/>
      </svg>
    </div>
    """)


def section(title, subtitle=""):
    sub = f'<div class="sec-s">{esc(subtitle)}</div>' if subtitle else ""
    render(f'<div class="sec"><div class="sec-t">{esc(title)}</div>{sub}</div>')


def event_head(event, show_status=False):
    color = category_color(event["category"])
    day, mon = _date_parts(event["event_date"])
    status = chip(event["status"], STATUS_COLORS.get(event["status"], DEFAULT_COLOR)) if show_status else ""
    desc = esc(event.get("description") or "No description provided.")
    return f"""
    <div class="ev" style="--c:{color}">
      <div class="stamp"><b>{day}</b><span>{mon}</span></div>
      <div class="ev-body">
        <div class="chips">{chip(event["category"], color)}{status}</div>
        <div class="ev-title">{esc(event["title"])}</div>
        <div class="ev-desc">{desc}</div>
        <div class="meta">
          <span>🕒 {esc(event["start_time"])}–{esc(event["end_time"])}</span>
          <span>📍 {esc(event["venue"])}</span>
          <span>🎤 {esc(event["organizer"])}</span>
        </div>
      </div>
    </div>
    """


def seats_html(capacity, registered):
    left = max(0, capacity - registered)
    ratio_left = (left / capacity) if capacity else 0
    color = "#4ade80" if ratio_left > 0.4 else "#fbbf24" if ratio_left > 0.15 else "#fb7185"
    filled = min(100, round(100 * registered / capacity)) if capacity else 100
    label = "seats left" if left else "event full"
    return f"""
    <div class="seats" style="--c:{color}">
      <div class="seats-n">{left}</div>
      <div class="seats-l">{label}</div>
      <div class="bar"><i style="width:{filled}%"></i></div>
    </div>
    """


def tile(label, value, icon, color):
    return f"""
    <div class="tile" style="--c:{color}">
      <div class="tile-i">{icon}</div>
      <div class="tile-n">{esc(value)}</div>
      <div class="tile-l">{esc(label)}</div>
    </div>
    """


def ticket_html(ticket, qr_png):
    color = category_color(ticket.get("category", ""))
    qr64 = base64.b64encode(qr_png).decode()
    meta = esc(ticket.get("meta", ""))
    meta_html = f'<div class="t-meta">{meta}</div>' if meta else ""
    return f"""
    <div class="ticket" style="--c:{color}">
      <div class="t-main">
        <div class="chips">{chip(ticket.get("category") or "Your ticket", color)}</div>
        <div class="t-title">{esc(ticket["event"])}</div>
        {meta_html}
        <div class="t-who"><span>Attendee</span><b>{esc(ticket["name"])}</b></div>
        <div class="t-code">{esc(ticket["code"])}</div>
      </div>
      <div class="t-stub">
        <img src="data:image/png;base64,{qr64}" alt="QR ticket"/>
        <span>Show this at the door</span>
      </div>
    </div>
    """


# ---------------------------- the stylesheet ----------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=DM+Sans:wght@400;500;700&display=swap');

:root{
  --bg:#0c0a1f; --surface:#17142e; --line:rgba(255,255,255,.10);
  --text:#f4f2ff; --muted:#a29ec7;
  --violet:#8b5cf6; --pink:#f472b6; --cyan:#22d3ee; --amber:#fbbf24; --green:#4ade80;
  --display:'Bricolage Grotesque','DM Sans',system-ui,sans-serif;
}

/* fonts: set on text elements only, so icon fonts keep working */
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li {
  font-family:'DM Sans',system-ui,sans-serif;
}
.stApp h1, .stApp h2, .stApp h3 { font-family:var(--display); letter-spacing:-.01em; }

/* page */
.stApp{
  background:
    radial-gradient(900px 500px at 6% -10%, rgba(139,92,246,.30), transparent 60%),
    radial-gradient(700px 420px at 100% 0%, rgba(244,114,182,.20), transparent 60%),
    var(--bg);
}
.block-container{ padding-top:2rem; max-width:1180px; }
#MainMenu, footer, [data-testid="stDecoration"]{ display:none; }

/* hero: the one loud moment */
.hero{
  position:relative; overflow:hidden; border-radius:24px; padding:28px 34px; margin-bottom:26px;
  display:flex; align-items:center; justify-content:space-between; gap:24px; flex-wrap:wrap;
  background:linear-gradient(115deg,#5b21b6 0%,#be185d 55%,#ea580c 100%);
  box-shadow:0 18px 50px rgba(190,24,93,.25);
}
.hero .brand{ font-family:var(--display); font-weight:800; font-size:2.7rem; line-height:1; letter-spacing:-.03em; color:#fff; }
.hero .sub{ color:rgba(255,255,255,.88); margin-top:10px; font-size:1.02rem; }
.ecg{ width:min(380px,100%); height:64px; }
.ecg path{ fill:none; stroke-width:3; stroke-linecap:round; stroke-linejoin:round; }
.ecg .base{ stroke:rgba(255,255,255,.30); }
.ecg .beat{
  stroke:#fff; stroke-dasharray:.3 1.1; animation:sweep 2.4s linear infinite;
  filter:drop-shadow(0 0 6px rgba(255,255,255,.9));
}
@keyframes sweep{ from{ stroke-dashoffset:.3; } to{ stroke-dashoffset:-1.1; } }

/* section titles */
.sec{ margin:6px 0 16px; }
.sec-t{ font-family:var(--display); font-weight:700; font-size:1.7rem; letter-spacing:-.02em; color:var(--text); }
.sec-s{ color:var(--muted); margin-top:4px; }

/* sidebar */
[data-testid="stSidebar"]{ background:#110e27; border-right:1px solid var(--line); }
.side-brand{ display:flex; align-items:center; gap:12px; margin:4px 0 18px; }
.side-brand .logo{
  width:42px; height:42px; border-radius:14px; display:grid; place-items:center; font-size:1.3rem;
  background:linear-gradient(135deg,var(--violet),var(--pink));
}
.side-brand b{ display:block; font-family:var(--display); font-size:1.15rem; color:var(--text); }
.side-brand small{ color:var(--muted); }
[data-testid="stSidebar"] [role="radiogroup"]{ gap:6px; }
[data-testid="stSidebar"] [role="radiogroup"] label{ padding:10px 14px; border-radius:12px; transition:background .15s; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:rgba(255,255,255,.07); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){
  background:linear-gradient(90deg,rgba(139,92,246,.40),rgba(244,114,182,.18));
}

/* bordered containers become event cards */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:20px !important; border:1px solid var(--line) !important; background:rgba(255,255,255,.04);
}
[data-testid="stForm"]{ border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.03); }
[data-testid="stExpander"]{ border-radius:14px; border:1px solid var(--line); }
[data-testid="stAlert"]{ border-radius:14px; }
[data-testid="stFileUploaderDropzone"]{
  border:2px dashed rgba(139,92,246,.65); border-radius:18px; background:rgba(139,92,246,.08);
}
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div{ border-radius:12px !important; }

/* buttons */
button[kind="primary"], button[kind="primaryFormSubmit"],
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(120deg,var(--violet),var(--pink)) !important; color:#fff !important;
  border:0 !important; border-radius:999px !important; font-weight:700 !important;
  padding:.55rem 1.4rem !important; box-shadow:0 6px 20px rgba(139,92,246,.35);
  transition:transform .15s, filter .15s;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover,
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover{
  filter:brightness(1.12); transform:translateY(-1px);
}
button[kind="secondary"], button[kind="secondaryFormSubmit"],
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"]{
  border-radius:999px !important; border:1px solid rgba(139,92,246,.7) !important;
}

/* event card */
.ev{ display:flex; gap:18px; align-items:flex-start; }
.stamp{
  flex:0 0 68px; text-align:center; border-radius:16px; padding:10px 0;
  background:var(--c); color:#0c0a1f;
}
.stamp b{ display:block; font-family:var(--display); font-weight:800; font-size:1.9rem; line-height:1; }
.stamp span{ font-size:.82rem; font-weight:700; }
.ev-body{ min-width:0; }
.chips{ display:flex; gap:8px; flex-wrap:wrap; }
.chip{
  background:color-mix(in srgb, var(--c) 18%, transparent); color:var(--c);
  border:1px solid color-mix(in srgb, var(--c) 45%, transparent);
  padding:3px 12px; border-radius:999px; font-size:.78rem; font-weight:700;
}
.ev-title{ font-family:var(--display); font-weight:700; font-size:1.45rem; letter-spacing:-.01em; margin:10px 0 4px; color:var(--text); }
.ev-desc{ color:var(--muted); max-width:62ch; }
.meta{ display:flex; flex-wrap:wrap; gap:6px 18px; color:var(--text); opacity:.85; font-size:.9rem; margin-top:12px; }

/* seats */
.seats{ text-align:center; padding:6px 0 12px; }
.seats-n{ font-family:var(--display); font-weight:800; font-size:2.4rem; line-height:1; color:var(--c); }
.seats-l{ color:var(--muted); font-size:.85rem; margin:2px 0 8px; }
.bar{ height:6px; border-radius:99px; background:rgba(255,255,255,.10); overflow:hidden; }
.bar i{ display:block; height:100%; background:var(--c); border-radius:99px; }

/* analytics tiles */
.tile{
  border-radius:20px; padding:18px 20px; margin-bottom:10px;
  border:1px solid color-mix(in srgb, var(--c) 40%, transparent);
  background:linear-gradient(150deg, color-mix(in srgb, var(--c) 24%, transparent), rgba(255,255,255,.02));
}
.tile-i{ font-size:1.3rem; }
.tile-n{ font-family:var(--display); font-weight:800; font-size:2.5rem; line-height:1.1; color:var(--c); }
.tile-l{ color:var(--muted); font-size:.9rem; }

/* ticket */
.ticket{
  display:flex; position:relative; overflow:hidden; max-width:720px; margin:6px 0 14px; border-radius:22px;
  border:1px solid color-mix(in srgb, var(--c) 50%, transparent);
  background:linear-gradient(135deg, color-mix(in srgb, var(--c) 30%, #17142e), #17142e 70%);
  box-shadow:0 14px 40px color-mix(in srgb, var(--c) 22%, transparent);
}
.t-main{ flex:1; padding:22px 26px; min-width:0; }
.t-title{ font-family:var(--display); font-weight:800; font-size:1.7rem; letter-spacing:-.02em; margin:10px 0 4px; color:var(--text); }
.t-meta{ color:var(--muted); font-size:.9rem; }
.t-who{ margin-top:16px; }
.t-who span{ display:block; color:var(--muted); font-size:.8rem; }
.t-who b{ font-size:1.1rem; color:var(--text); }
.t-code{
  margin-top:14px; display:inline-block; padding:6px 12px; border-radius:10px;
  background:rgba(0,0,0,.35); font-family:ui-monospace,Consolas,monospace; letter-spacing:.06em; color:var(--text);
}
.t-stub{
  position:relative; flex:0 0 200px; padding:20px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px;
  border-left:2px dashed rgba(255,255,255,.28); text-align:center;
}
.t-stub img{ width:150px; height:150px; background:#fff; padding:8px; border-radius:14px; }
.t-stub span{ color:var(--muted); font-size:.8rem; }
.t-stub::before, .t-stub::after{
  content:""; position:absolute; left:-11px; width:20px; height:20px; border-radius:50%; background:var(--bg);
}
.t-stub::before{ top:-10px; }
.t-stub::after{ bottom:-10px; }

@media (max-width:640px){
  .hero{ padding:22px; } .hero .brand{ font-size:2.1rem; }
  .ev{ flex-direction:column; }
  .ticket{ flex-direction:column; }
  .t-stub{ border-left:0; border-top:2px dashed rgba(255,255,255,.28); flex-basis:auto; }
  .t-stub::before, .t-stub::after{ display:none; }
}
@media (prefers-reduced-motion:reduce){
  .ecg .beat{ animation:none; stroke-dasharray:none; filter:none; }
}
</style>
"""


def inject_css():
    st.markdown(_clean(CSS), unsafe_allow_html=True)
