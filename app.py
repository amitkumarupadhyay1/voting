"""
JB Academy Election Portal
Bulletproof edition — thread-safe, race-condition-proof, election-ethics compliant.
"""

import random
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import Auth
from models import AuditLog, Candidate, Committee, Database, Election, Student, Vote
from utils import Utils
from voting import VotingEngine
from pages.components import phase_badge
from pages.results import render_results

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JB Academy Elections",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
HOUSE_META = {
    "Taxila": {
        "color": "#3b82f6",
        "bg": "rgba(59,130,246,0.12)",
        "border": "rgba(59,130,246,0.4)",
        "emoji": "🔵",
        "icon": "🏛️",
    },
    "Janata": {
        "color": "#22c55e",
        "bg": "rgba(34,197,94,0.12)",
        "border": "rgba(34,197,94,0.4)",
        "emoji": "🟢",
        "icon": "🌿",
    },
    "Saachi": {
        "color": "#ef4444",
        "bg": "rgba(239,68,68,0.12)",
        "border": "rgba(239,68,68,0.4)",
        "emoji": "🔴",
        "icon": "🔥",
    },
    "Nalanda": {
        "color": "#f59e0b",
        "bg": "rgba(245,158,11,0.12)",
        "border": "rgba(245,158,11,0.4)",
        "emoji": "🟡",
        "icon": "📚",
    },
}
DEFAULT_HOUSE = {
    "color": "#6366f1",
    "bg": "rgba(99,102,241,0.12)",
    "border": "rgba(99,102,241,0.4)",
    "emoji": "🏠",
    "icon": "🏠",
}

COMMITTEE_INFO = {
    "Sports": {
        "icon": "⚽",
        "desc": "Organises sports days, tournaments & inter-house competitions",
    },
    "Literary": {
        "icon": "📖",
        "desc": "Runs debates, quiz bowls, school magazine & reading clubs",
    },
    "Eco": {
        "icon": "🌱",
        "desc": "Champions green initiatives, recycling & environment drives",
    },
    "Cultural": {
        "icon": "🎭",
        "desc": "Plans cultural fests, art shows, music & drama events",
    },
    "Maintenance": {
        "icon": "🔧",
        "desc": "Keeps classrooms, labs & common areas clean and functional",
    },
    "Discipline": {
        "icon": "⚖️",
        "desc": "Upholds school rules, resolves conflicts & promotes respect",
    },
    "CCA": {
        "icon": "🎨",
        "desc": "Co-curricular activities — clubs, hobby groups & talent shows",
    },
}

CIVIC_FACTS = [
    "🗳️ The word 'vote' comes from the Latin 'votum' — meaning a wish or vow.",
    "🌍 New Zealand was the first country to give all adults the right to vote, in 1893.",
    "📜 A secret ballot protects your freedom to vote without fear or pressure.",
    "🏛️ Ancient Athens held the world's first democratic elections over 2,500 years ago.",
    "✊ Every vote matters — many elections in history were decided by just one vote.",
    "🎓 Student elections teach the same skills used in real-world democracy.",
    "🤝 Good leaders listen more than they speak.",
    "💡 The best leaders serve their community, not themselves.",
]

AVATARS = [
    "🧑‍🎓",
    "👨‍🎓",
    "👩‍🎓",
    "🧑",
    "👦",
    "👧",
    "🙋",
    "🙋‍♂️",
    "🙋‍♀️",
    "🎓",
    "🧑‍💼",
    "👩‍💼",
]
RANK_ICONS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
ABSTAIN = "__abstain__"


def avatar(name: str) -> str:
    random.seed(str(name))
    return random.choice(AVATARS)


def hm(house: str) -> dict:
    return HOUSE_META.get(house, DEFAULT_HOUSE)


def ci(committee: str) -> dict:
    return COMMITTEE_INFO.get(
        committee, {"icon": "📋", "desc": "Serves the school community."}
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*,*::before,*::after{font-family:'Inter',sans-serif!important;box-sizing:border-box;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
.stApp{background:radial-gradient(ellipse at 20% 50%,#1a0533 0%,#0a0a1a 40%,#001a33 100%);min-height:100vh;color:#e2e8f0}
header,footer,#MainMenu{visibility:hidden!important}
.block-container{padding-top:1rem!important}
.particles{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden}
.particle{position:absolute;border-radius:50%;background:rgba(255,255,255,0.15);animation:floatUp linear infinite}
@keyframes floatUp{0%{transform:translateY(100vh) scale(0);opacity:0}10%{opacity:1}90%{opacity:.6}100%{transform:translateY(-10vh) scale(1);opacity:0}}
.glass{background:rgba(255,255,255,.06);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.12);border-radius:20px}
.glass-strong{background:rgba(255,255,255,.10);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);border:1px solid rgba(255,255,255,.18);border-radius:20px}
.hero-wrap{position:relative;overflow:hidden;background:linear-gradient(135deg,#1e0a3c 0%,#0d1b4b 50%,#0a2a1a 100%);border-radius:24px;padding:48px 40px;text-align:center;border:1px solid rgba(255,255,255,.1);margin-bottom:28px}
.hero-wrap::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:conic-gradient(from 0deg,transparent 0deg,rgba(99,102,241,.15) 60deg,transparent 120deg);animation:rotateBg 12s linear infinite}
@keyframes rotateBg{to{transform:rotate(360deg)}}
.hero-title{font-size:clamp(1.8rem,4vw,3rem);font-weight:900;color:white;letter-spacing:-1.5px;position:relative;z-index:1;text-shadow:0 0 40px rgba(99,102,241,.6)}
.hero-sub{color:#a5b4fc;font-size:1.05rem;margin-top:8px;position:relative;z-index:1}
.live-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(239,68,68,.2);border:1px solid rgba(239,68,68,.5);color:#fca5a5;padding:6px 18px;border-radius:99px;font-weight:700;font-size:.9rem;margin-top:14px;position:relative;z-index:1}
.live-dot{width:8px;height:8px;background:#ef4444;border-radius:50%;animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(1.6)}}
.stopped-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(100,116,139,.2);border:1px solid rgba(100,116,139,.4);color:#94a3b8;padding:6px 18px;border-radius:99px;font-weight:600;font-size:.9rem;margin-top:14px;position:relative;z-index:1}
.stat-card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:20px 16px;text-align:center;transition:transform .2s,border-color .2s}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(99,102,241,.4)}
.stat-num{font-size:2rem;font-weight:800;color:#818cf8;line-height:1}
.stat-label{font-size:.78rem;color:#64748b;margin-top:6px;text-transform:uppercase;letter-spacing:.5px}
.cand-card{background:rgba(255,255,255,.05);border:2px solid rgba(255,255,255,.08);border-radius:18px;padding:22px 18px;text-align:center;cursor:pointer;transition:all .25s ease;position:relative;overflow:hidden}
.cand-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#6366f1,#8b5cf6,#ec4899);opacity:0;transition:opacity .25s}
.cand-card:hover{transform:translateY(-4px);border-color:rgba(99,102,241,.5);box-shadow:0 12px 40px rgba(99,102,241,.2)}
.cand-card:hover::before{opacity:1}
.cand-card.selected{border-color:#10b981!important;background:rgba(16,185,129,.12)!important;box-shadow:0 0 0 3px rgba(16,185,129,.2),0 12px 40px rgba(16,185,129,.15)}
.cand-card.selected::before{background:linear-gradient(90deg,#10b981,#34d399);opacity:1}
.cand-avatar{font-size:3rem;margin-bottom:10px;display:block}
.cand-name{font-size:1.05rem;font-weight:700;color:white;margin-bottom:4px}
.cand-meta{font-size:.8rem;color:#94a3b8}
.cand-house{font-size:.78rem;font-weight:600;margin-top:6px}
.cand-manifesto{margin-top:12px;padding:10px 12px;background:rgba(0,0,0,.25);border-radius:10px;border-left:3px solid #6366f1;font-size:.78rem;color:#cbd5e1;font-style:italic;text-align:left;line-height:1.5}
.cand-selected-check{position:absolute;top:12px;right:12px;background:#10b981;color:white;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700}
.comm-header{display:flex;align-items:center;gap:14px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 20px;margin:20px 0 14px}
.comm-icon{font-size:2rem}
.comm-title{font-size:1.15rem;font-weight:700;color:white}
.comm-desc{font-size:.82rem;color:#64748b;margin-top:2px}
.steps{display:flex;align-items:center;justify-content:center;gap:0;margin:20px 0 28px}
.step{display:flex;align-items:center;gap:8px;padding:8px 20px;border-radius:99px;font-size:.85rem;font-weight:600;color:#475569;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08)}
.step.active{background:rgba(99,102,241,.2);border-color:#6366f1;color:#a5b4fc}
.step.done{background:rgba(16,185,129,.15);border-color:#10b981;color:#6ee7b7}
.step-line{width:40px;height:2px;background:rgba(255,255,255,.1)}
.step-line.done{background:#10b981}
.result-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 20px;margin:8px 0;display:flex;align-items:center;gap:16px;transition:transform .2s}
.result-card:hover{transform:translateX(4px)}
.result-card.winner{background:rgba(16,185,129,.08);border-color:rgba(16,185,129,.3)}
.result-card.tied{background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.4)}
.result-rank{font-size:1.6rem;min-width:40px}
.result-info{flex:1}
.result-name{font-weight:700;color:white;font-size:1rem}
.result-sub{font-size:.8rem;color:#64748b;margin-top:2px}
.result-right{text-align:right;min-width:90px}
.result-votes{font-size:1.1rem;font-weight:800;color:white}
.result-pct{font-size:.78rem;color:#64748b}
.bar-wrap{flex:2;min-width:100px;background:rgba(255,255,255,.07);border-radius:99px;height:8px;overflow:hidden}
.bar-fill{height:8px;border-radius:99px;transition:width 1s ease}
.bar-winner{background:linear-gradient(90deg,#10b981,#34d399)}
.bar-tied{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.bar-normal{background:linear-gradient(90deg,#6366f1,#8b5cf6)}
.confirm-row{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.25);border-radius:12px;padding:14px 18px;margin:8px 0;display:flex;align-items:center;gap:12px}
.confirm-abstain{background:rgba(100,116,139,.08);border:1px solid rgba(100,116,139,.2);border-radius:12px;padding:14px 18px;margin:8px 0;color:#64748b}
.nom-card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:20px;margin:12px 0}
.nom-pending{border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.06)}
.nom-approved{border-color:rgba(16,185,129,.4);background:rgba(16,185,129,.06)}
.nom-rejected{border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.05)}
.badge{display:inline-block;padding:3px 12px;border-radius:99px;font-size:.72rem;font-weight:700;letter-spacing:.5px}
.badge-pending{background:rgba(245,158,11,.2);color:#fbbf24;border:1px solid rgba(245,158,11,.4)}
.badge-approved{background:rgba(16,185,129,.2);color:#34d399;border:1px solid rgba(16,185,129,.4)}
.badge-rejected{background:rgba(239,68,68,.2);color:#f87171;border:1px solid rgba(239,68,68,.4)}
.badge-live{background:rgba(239,68,68,.2);color:#fca5a5;border:1px solid rgba(239,68,68,.4)}
.badge-stopped{background:rgba(100,116,139,.2);color:#94a3b8;border:1px solid rgba(100,116,139,.4)}
.house-card{border-radius:16px;padding:20px;text-align:center;border:1px solid;transition:transform .2s}
.house-card:hover{transform:scale(1.02)}
.welcome-card{border-radius:20px;padding:24px 28px;display:flex;align-items:center;gap:20px;margin-bottom:20px;border:1px solid}
.info-box{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.25);border-radius:12px;padding:14px 18px;margin:12px 0;font-size:.88rem;color:#c7d2fe}
.warn-box{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.3);border-radius:12px;padding:14px 18px;margin:12px 0;font-size:.88rem;color:#fde68a}
.success-box{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.3);border-radius:12px;padding:14px 18px;margin:12px 0;font-size:.88rem;color:#6ee7b7}
.error-box{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:12px;padding:14px 18px;margin:12px 0;font-size:.88rem;color:#fca5a5}
.civic-fact{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);border-radius:12px;padding:12px 18px;font-size:.85rem;color:#a5b4fc;margin:16px 0}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:transparent!important}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.05)!important;border-radius:10px!important;color:#64748b!important;font-weight:600!important;border:1px solid rgba(255,255,255,.08)!important;padding:8px 16px!important}
.stTabs [aria-selected="true"]{background:rgba(99,102,241,.25)!important;color:#a5b4fc!important;border-color:rgba(99,102,241,.4)!important}
.stTabs [data-baseweb="tab-panel"]{padding-top:20px!important}
.stButton>button{border-radius:12px!important;font-weight:600!important;transition:all .2s ease!important;letter-spacing:.2px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:6px!important}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366f1,#8b5cf6)!important;border:none!important;box-shadow:0 4px 20px rgba(99,102,241,.35)!important}
.stButton>button[kind="primary"]:hover{transform:translateY(-2px)!important;box-shadow:0 8px 30px rgba(99,102,241,.5)!important}
.stTextInput>div>div>input,.stTextArea textarea,.stSelectbox>div>div,.stNumberInput>div>div>input{background:rgba(255,255,255,.07)!important;border:1px solid rgba(255,255,255,.12)!important;border-radius:10px!important;color:white!important}
.stTextInput>div>div>input:focus,.stTextArea textarea:focus{border-color:rgba(99,102,241,.6)!important;box-shadow:0 0 0 3px rgba(99,102,241,.15)!important}
.stDataFrame{border-radius:12px!important;overflow:hidden}
[data-testid="stFileUploader"] label{display:none!important}
[data-testid="stFileUploaderDropzone"]{background:rgba(255,255,255,.05)!important;border:2px dashed rgba(99,102,241,.4)!important;border-radius:14px!important}
[data-testid="stFileUploaderDropzone"]:hover{border-color:rgba(99,102,241,.8)!important;background:rgba(99,102,241,.08)!important}
[data-testid="stFileUploaderDropzoneInstructions"] span{color:#a5b4fc!important}
[data-testid="stFileUploaderDropzone"] button span:last-child{display:none!important}
hr{border-color:rgba(255,255,255,.07)!important;margin:20px 0!important}
[data-testid="metric-container"]{background:rgba(255,255,255,.05)!important;border:1px solid rgba(255,255,255,.1)!important;border-radius:14px!important;padding:16px!important}
[data-testid="stExpander"] summary{font-size:1rem!important;font-weight:600!important;padding:12px 16px!important}
[data-testid="stExpander"] div[data-testid="stExpanderDetails"]{padding:16px!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label{font-size:0.9rem!important;font-weight:600!important;margin-bottom:6px!important;display:block!important;color:#cbd5e1!important}
.stTextInput label p,.stTextArea label p,.stSelectbox label p,.stNumberInput label p{margin:0!important;padding:0!important;line-height:1.4!important}
div[data-testid="column"]{isolation:isolate!important}
.element-container{isolation:isolate!important}
[data-testid="stMarkdownContainer"] p{margin:0!important;padding:0!important}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# PARTICLES
# ─────────────────────────────────────────────────────────────────────────────
def particles_html() -> str:
    items = []
    for _ in range(18):
        size = random.randint(3, 7)
        left = random.randint(0, 100)
        delay = random.uniform(0, 20)
        dur = random.uniform(15, 35)
        items.append(
            f'<div class="particle" style="width:{size}px;height:{size}px;'
            f'left:{left}%;animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s;"></div>'
        )
    return f'<div class="particles">{"".join(items)}</div>'


st.markdown(particles_html(), unsafe_allow_html=True)


def confetti_html() -> str:
    colors = [
        "#6366f1",
        "#8b5cf6",
        "#ec4899",
        "#10b981",
        "#f59e0b",
        "#3b82f6",
        "#ef4444",
        "#34d399",
    ]
    pieces = []
    for _ in range(60):
        color = random.choice(colors)
        left = random.randint(0, 100)
        delay = random.uniform(0, 1.5)
        dur = random.uniform(2.5, 4.5)
        size = random.randint(6, 14)
        rot = random.randint(0, 360)
        pieces.append(
            f'<div class="confetti-piece" style="position:fixed;width:{size}px;height:{size}px;'
            f"top:-10px;background:{color};left:{left}%;border-radius:2px;z-index:9999;"
            f"pointer-events:none;animation:confettiFall {dur:.1f}s {delay:.1f}s linear forwards;"
            f'transform:rotate({rot}deg);"></div>'
        )
    return (
        "<style>@keyframes confettiFall{"
        "0%{transform:translateY(0) rotate(0deg);opacity:1}"
        "100%{transform:translateY(110vh) rotate(720deg);opacity:0}}</style>"
        + "".join(pieces)
    )


# ─────────────────────────────────────────────────────────────────────────────
# INIT  (cache_resource = one DB instance per server process, not per user)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def init():
    db = Database("school_voting.db")
    auth = Auth(db)
    voting = VotingEngine(db)
    elec = Election(db)
    alog = AuditLog(db)
    return db, auth, voting, elec, alog


db, auth, voting, election, audit = init()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "user_type": None,
    "user_data": None,
    "review_votes": False,
    "temp_votes": {},
    "confirm_start": False,
    "confirm_stop": False,
    "confirm_reset": False,
    "last_activity": time.time(),
    "vote_step": 0,
    "show_add": False,
    "show_edit": False,
    "show_reset": False,
    "show_del": False,
    "show_change_pwd": False,
    "saved_votes": None,
    "saved_votes_timestamp": None,
    "warning_autosave_done": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Session timeout — 15 min (900 seconds)
SESSION_TIMEOUT = 900
WARNING_THRESHOLD = 120  # Show warning at 2 minutes remaining

if st.session_state.user_type is not None:
    elapsed = time.time() - st.session_state.last_activity
    remaining = SESSION_TIMEOUT - elapsed

    if elapsed > SESSION_TIMEOUT:
        who = st.session_state.user_data[0] if st.session_state.user_data else "admin"
        audit.log("SESSION_TIMEOUT", who)
        for k, v in _defaults.items():
            st.session_state[k] = v
        st.warning("⏱️ Session expired. Please log in again.")
        st.rerun()
    else:
        st.session_state.last_activity = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# VOTE PROGRESS PERSISTENCE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def save_vote_progress(student_id: str, temp_votes: dict):
    """
    Save temp_votes to session storage with timestamp.
    Serializes vote selections to JSON format.
    """
    import json

    if not temp_votes:
        return

    vote_data = {
        "student_id": student_id,
        "votes": temp_votes,
        "timestamp": time.time(),
        "saved_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Serialize to JSON and store in session state
    st.session_state.saved_votes = json.dumps(vote_data)
    st.session_state.saved_votes_timestamp = vote_data["timestamp"]


def load_vote_progress(student_id: str) -> dict:
    """
    Load saved vote progress from session storage.
    Returns empty dict if no saved data or if data is invalid.
    """
    import json

    if not st.session_state.saved_votes:
        return {}

    try:
        vote_data = json.loads(st.session_state.saved_votes)

        # Validate the saved data belongs to current student
        if vote_data.get("student_id") != student_id:
            return {}

        # Return the votes dictionary
        return vote_data.get("votes", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def clear_vote_progress():
    """Clear saved vote progress from session storage."""
    st.session_state.saved_votes = None
    st.session_state.saved_votes_timestamp = None


# ─────────────────────────────────────────────────────────────────────────────
# HERO BANNER
# ─────────────────────────────────────────────────────────────────────────────

phase = election.get_phase()
is_live = election.is_live()
status_html = phase_badge(phase)
st.markdown(
    f"""
<div class="hero-wrap">
    <div class="hero-title">🗳️ JB Academy Elections</div>
    <div class="hero-sub">Your voice. Your school. Your future.</div>
    <div>{status_html}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION WARNING (Task 3.3)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.user_type is not None:
    from pages.components import session_warning_banner

    elapsed = time.time() - st.session_state.last_activity
    remaining = SESSION_TIMEOUT - elapsed

    # Show warning when less than 2 minutes remain (Task 3.3.1)
    if 0 < remaining <= WARNING_THRESHOLD:
        st.markdown(session_warning_banner(remaining), unsafe_allow_html=True)

        # Extend session button (Task 3.3.2)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(
                "🔄 Extend Session",
                use_container_width=True,
                type="primary",
                key="extend_session",
            ):
                st.session_state.last_activity = time.time()
                # Auto-save current progress for students (Task 3.3.3)
                if (
                    st.session_state.user_type == "student"
                    and st.session_state.user_data
                ):
                    if st.session_state.get("temp_votes"):
                        save_vote_progress(
                            st.session_state.user_data[0], st.session_state.temp_votes
                        )
                st.success("✅ Session extended for 15 more minutes!")
                time.sleep(1)
                st.rerun()

        # Auto-save progress when warning appears (Task 3.3.3)
        if st.session_state.user_type == "student" and st.session_state.user_data:
            if st.session_state.get("temp_votes") and not st.session_state.get(
                "warning_autosave_done"
            ):
                save_vote_progress(
                    st.session_state.user_data[0], st.session_state.temp_votes
                )
                st.session_state.warning_autosave_done = True

        # Auto-refresh to update countdown
        time.sleep(1)
        st.rerun()

random.seed(int(time.time() // 3600))
fact = random.choice(CIVIC_FACTS)


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.user_type is None:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(
            """
        <div class="glass-strong" style="padding:36px 32px;margin-top:8px;">
            <div style="text-align:center;margin-bottom:28px;">
                <div style="font-size:3.5rem;">🏫</div>
                <div style="font-size:1.4rem;font-weight:800;color:white;margin-top:8px;">Welcome Back</div>
                <div style="color:#64748b;font-size:.9rem;margin-top:4px;">Sign in to participate in your school election</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        lid = st.text_input(
            "Admission No / Admin ID", placeholder="e.g. JB001", key="lid"
        )
        lpwd = st.text_input(
            "Password", type="password", placeholder="Your password", key="lpwd"
        )

        if st.button("🔓  Sign In", use_container_width=True, type="primary"):
            if not lid or not lpwd:
                st.markdown(
                    '<div class="error-box">❌ Please enter both ID and password.</div>',
                    unsafe_allow_html=True,
                )
            else:
                res = auth.validate_credentials(lid, lpwd)
                if res["type"] == "admin":
                    st.session_state.user_type = "admin"
                    st.session_state.last_activity = time.time()
                    audit.log("ADMIN_LOGIN", lid.lower())
                    st.rerun()
                elif res["type"] == "student":
                    st.session_state.user_type = "student"
                    st.session_state.user_data = res["data"]
                    st.session_state.last_activity = time.time()
                    audit.log("STUDENT_LOGIN", res["data"][0])
                    st.rerun()
                elif res["type"] == "locked":
                    st.markdown(
                        f'<div class="error-box">🔒 {res["message"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="error-box">❌ {res["message"]}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown(
            """
            <div style="text-align:center;margin-top:20px;color:#334155;font-size:.8rem;">
                Forgot your password? Ask your teacher.
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="civic-fact" style="margin-top:32px;">💡 {fact}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.user_type == "admin":

    ah1, ah2 = st.columns([9, 1])
    with ah1:
        st.markdown(
            '<div style="font-size:1.1rem;font-weight:700;color:#94a3b8;">🛠️ Administrator Dashboard</div>',
            unsafe_allow_html=True,
        )
    with ah2:
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            audit.log("ADMIN_LOGOUT", "admin")
            for k, v in _defaults.items():
                st.session_state[k] = v
            st.rerun()

    # ── Quick stats ──
    stats = election.get_statistics()
    pending_count = len(Candidate(db).get_pending())
    live_now = election.is_live()

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    for col, num, lbl in [
        (s1, stats["total_students"], "Students"),
        (s2, stats["voted_students"], "Voted"),
        (s3, stats["not_voted"], "Pending"),
        (s4, f"{stats['participation_rate']:.0f}%", "Turnout"),
        (s5, pending_count, "⏳ Nominations"),
        (s6, "🔴 LIVE" if live_now else "⚫ OFF", "Election"),
    ]:
        col.markdown(
            f'<div class="stat-card"><div class="stat-num">{num}</div>'
            f'<div class="stat-label">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if pending_count > 0:
        st.markdown(
            f'<div class="warn-box">⏳ <strong>{pending_count} nomination(s)</strong> '
            f"are waiting for your approval — check the Nominations tab.</div>",
            unsafe_allow_html=True,
        )

    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs(
        [
            "📥 Import",
            "👥 Students",
            "🏛️ Committees",
            "🎯 Nominations",
            "🎛️ Election",
            "📊 Results",
            "📈 Analytics",
            "🔍 Records",
            "🔐 Admin",
        ]
    )

    # ── TAB 1: IMPORT ─────────────────────────────────────────────────────────
    with t1:
        st.markdown("#### 📤 Import Students from Excel", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">Excel columns required: '
            "<strong>admission_no, name, class, section, house</strong></div>",
            unsafe_allow_html=True,
        )
        f = st.file_uploader(
            "📂 Upload Excel (.xlsx)", type=["xlsx"], label_visibility="hidden"
        )
        if f:
            try:
                df = pd.read_excel(f, dtype=str)
                imp, errs, elist = Utils.import_students_from_excel(df, db)
                if imp > 0:
                    st.markdown(
                        f'<div class="success-box">✅ {imp} students imported successfully.</div>',
                        unsafe_allow_html=True,
                    )
                    audit.log("IMPORT_STUDENTS", "admin", f"{imp} imported")
                    if errs:
                        with st.expander(f"⚠️ {errs} rows skipped"):
                            for e in elist:
                                st.error(e)
                    pwd_file = Utils.create_password_file(Student(db).get_all())
                    st.download_button(
                        "📥 Download Password List",
                        data=pwd_file,
                        file_name=f'passwords_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    st.markdown(
                        f'<div class="error-box">❌ No students imported. {errs} error(s).</div>',
                        unsafe_allow_html=True,
                    )
                    for e in elist:
                        st.error(e)
            except Exception as ex:
                st.markdown(
                    f'<div class="error-box">❌ {ex}</div>', unsafe_allow_html=True
                )

    # ── TAB 2: STUDENTS ───────────────────────────────────────────────────────
    with t2:
        if st.button(
            "📥 Download All Passwords", use_container_width=True, type="primary"
        ):
            pwd_file = Utils.create_password_file(Student(db).get_all())
            st.download_button(
                "📥 Download Now",
                data=pwd_file,
                file_name=f'passwords_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
        st.divider()

        c1, c2, c3 = st.columns(3)
        with c1:
            srch = (
                st.text_input("🔍 Search", placeholder="Name or Adm No").strip().lower()
            )
        with c2:
            fcls = st.selectbox("Class", ["All", "7", "8", "9", "10", "11", "12"])
        with c3:
            fhs = st.selectbox("House", ["All"] + voting.HOUSES)

        all_s = Student(db).get_all()
        df_s = pd.DataFrame(
            all_s,
            columns=[
                "Adm",
                "Name",
                "Class",
                "Sec",
                "House",
                "Hash",
                "Pwd",
                "Voted",
                "Crt",
                "Upd",
            ],
        )
        if srch:
            df_s = df_s[
                df_s["Name"].str.lower().str.contains(srch, na=False)
                | df_s["Adm"].str.lower().str.contains(srch, na=False)
            ]
        if fcls != "All":
            df_s = df_s[df_s["Class"] == fcls]
        if fhs != "All":
            df_s = df_s[df_s["House"] == fhs]

        vc = int((df_s["Voted"] == 1).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Showing", len(df_s))
        m2.metric("Voted", vc)
        m3.metric("Not Voted", len(df_s) - vc)
        st.dataframe(
            df_s[["Adm", "Name", "Class", "Sec", "House", "Pwd", "Voted"]],
            use_container_width=True,
            hide_index=True,
        )
        st.divider()

        op1, op2, op3, op4 = st.columns(4)
        with op1:
            if st.button("➕ Add", use_container_width=True):
                st.session_state.show_add = not st.session_state.show_add
        with op2:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.show_edit = not st.session_state.show_edit
        with op3:
            if st.button("🔑 Reset Pwd", use_container_width=True):
                st.session_state.show_reset = not st.session_state.show_reset
        with op4:
            if st.button("🗑️ Delete", use_container_width=True):
                st.session_state.show_del = not st.session_state.show_del

        if st.session_state.show_add:
            st.markdown("#### ➕ Add Student", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                na = st.text_input("Admission No", key="na").strip().lower()
                nn = st.text_input("Full Name", key="nn")
                nc = st.selectbox("Class", ["7", "8", "9", "10", "11", "12"], key="nc")
            with c2:
                ns = st.selectbox("Section", ["A", "B", "C", "D", "E"], key="ns")
                nh = st.selectbox("House", voting.HOUSES, key="nh")
            if st.button("✅ Add Student", type="primary", use_container_width=True):
                if not na or not nn:
                    st.markdown(
                        '<div class="error-box">❌ Admission No and Name are required.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    pwd = Utils.generate_password()
                    if Student(db).add(
                        na, nn, nc, ns, nh, Auth.hash_password(pwd), pwd
                    ):
                        st.markdown(
                            f'<div class="success-box">✅ Added! Password: <strong>{pwd}</strong></div>',
                            unsafe_allow_html=True,
                        )
                        audit.log("ADD_STUDENT", "admin", f"{nn} ({na})")
                        st.rerun()
                    else:
                        st.markdown(
                            '<div class="error-box">❌ Failed — admission number may already exist.</div>',
                            unsafe_allow_html=True,
                        )

        if st.session_state.show_edit:
            st.markdown("#### ✏️ Edit Student", unsafe_allow_html=True)
            sl = Student(db).get_all()
            if sl:
                ea = st.selectbox(
                    "Select",
                    [s[0] for s in sl],
                    format_func=lambda x: f"{x} — {next((s[1] for s in sl if s[0]==x), x)}",
                )
                s = Student(db).get(ea)
                if s:
                    c1, c2 = st.columns(2)
                    with c1:
                        en = st.text_input("Name", value=s[1])
                        ec = st.selectbox(
                            "Class",
                            ["7", "8", "9", "10", "11", "12"],
                            index=(
                                ["7", "8", "9", "10", "11", "12"].index(s[2])
                                if s[2] in ["7", "8", "9", "10", "11", "12"]
                                else 0
                            ),
                        )
                    with c2:
                        es = st.selectbox(
                            "Section",
                            ["A", "B", "C", "D", "E"],
                            index=(
                                ["A", "B", "C", "D", "E"].index(s[3])
                                if s[3] in ["A", "B", "C", "D", "E"]
                                else 0
                            ),
                        )
                        eh = st.selectbox(
                            "House",
                            voting.HOUSES,
                            index=(
                                voting.HOUSES.index(s[4])
                                if s[4] in voting.HOUSES
                                else 0
                            ),
                        )
                    if st.button("💾 Save", type="primary", use_container_width=True):
                        if Student(db).update(ea, en, ec, es, eh):
                            st.markdown(
                                '<div class="success-box">✅ Updated!</div>',
                                unsafe_allow_html=True,
                            )
                            audit.log("EDIT_STUDENT", "admin", f"{en} ({ea})")
                            st.rerun()

        if st.session_state.show_reset:
            st.markdown("#### 🔑 Reset Password", unsafe_allow_html=True)
            sl = Student(db).get_all()
            if sl:
                ra = st.selectbox(
                    "Select",
                    [s[0] for s in sl],
                    format_func=lambda x: f"{x} — {next((s[1] for s in sl if s[0]==x), x)}",
                    key="ra",
                )
                if st.button(
                    "🔄 Generate New Password", type="primary", use_container_width=True
                ):
                    np_ = Utils.generate_password()
                    if Student(db).reset_password(ra, Auth.hash_password(np_), np_):
                        st.markdown(
                            f'<div class="success-box">✅ New password: <strong>{np_}</strong></div>',
                            unsafe_allow_html=True,
                        )
                        audit.log("RESET_PASSWORD", "admin", f"Reset for {ra}")

        if st.session_state.show_del:
            st.markdown("#### 🗑️ Delete Student", unsafe_allow_html=True)
            sl = Student(db).get_all()
            if sl:
                da = st.selectbox(
                    "Select",
                    [s[0] for s in sl],
                    format_func=lambda x: f"{x} — {next((s[1] for s in sl if s[0]==x), x)}",
                    key="da",
                )
                s = Student(db).get(da)
                if s:
                    st.markdown(
                        f'<div class="warn-box">⚠️ Delete <strong>{s[1]}</strong> ({da})?</div>',
                        unsafe_allow_html=True,
                    )
                    if s[7] == 1:
                        st.markdown(
                            '<div class="error-box">❌ Cannot delete — student has already voted.</div>',
                            unsafe_allow_html=True,
                        )
                    elif st.checkbox("I confirm permanent deletion", key="del_ck"):
                        if st.button(
                            "🗑️ Confirm Delete",
                            type="secondary",
                            use_container_width=True,
                        ):
                            if Student(db).delete(da):
                                st.markdown(
                                    f'<div class="success-box">✅ Deleted {s[1]}</div>',
                                    unsafe_allow_html=True,
                                )
                                audit.log("DELETE_STUDENT", "admin", f"{s[1]} ({da})")
                                st.rerun()

        # Admin password change
        st.divider()
        with st.expander("🔐 Change Admin Password"):
            cp1 = st.text_input("New Password", type="password", key="cp1")
            cp2 = st.text_input("Confirm New Password", type="password", key="cp2")
            if st.button("Update Admin Password", type="primary"):
                if len(cp1) < 8:
                    st.markdown(
                        '<div class="error-box">❌ Password must be at least 8 characters.</div>',
                        unsafe_allow_html=True,
                    )
                elif cp1 != cp2:
                    st.markdown(
                        '<div class="error-box">❌ Passwords do not match.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if auth.set_admin_password(cp1):
                        st.markdown(
                            '<div class="success-box">✅ Admin password updated. Please log in again.</div>',
                            unsafe_allow_html=True,
                        )
                        audit.log("ADMIN_PASSWORD_CHANGE", "admin")
                        for k, v in _defaults.items():
                            st.session_state[k] = v
                        st.rerun()

    # ── TAB 3: COMMITTEES ─────────────────────────────────────────────────────
    with t3:
        cm = Committee(db)
        cs1, cs2 = st.tabs(["📋 Current Committees", "➕ Add New"])

        with cs1:
            all_c = cm.get_all()
            for ctype in ["School", "House"]:
                rows = [r for r in all_c if r[2] == ctype]
                if not rows:
                    continue
                st.markdown(
                    f"**{'🏫 School' if ctype=='School' else '🏠 House'} Committees**",
                    unsafe_allow_html=True,
                )
                for r in rows:
                    info = ci(r[1])
                    desc = r[3] if len(r) > 3 and r[3] else info["desc"]
                    max_w = int(r[4]) if len(r) > 4 and r[4] else 1
                    pos_label = f"{max_w} position{'s' if max_w > 1 else ''}"
                    cc1, cc2 = st.columns([7, 1])
                    cc1.markdown(
                        f"{info['icon']} **{r[1]}** ({pos_label}) — "
                        f"<span style='color:#64748b;font-size:.82rem;'>{desc}</span>",
                        unsafe_allow_html=True,
                    )
                    if cc2.button("🗑️", key=f"dc_{r[0]}"):
                        ok, msg = cm.delete(r[0])
                        if ok:
                            audit.log("DELETE_COMMITTEE", "admin", r[1])
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                st.markdown("", unsafe_allow_html=True)

        with cs2:
            ncn = st.text_input("Committee Name")
            nct = st.selectbox("Type", ["School", "House"])
            ncd = st.text_input(
                "Description (optional)", placeholder="What does this committee do?"
            )
            nmw = st.number_input(
                "Max Winners (positions)",
                min_value=1,
                max_value=5,
                value=1,
                help="Set to 2 for Captain + Vice-Captain, 3 for Captain + 2 Vice-Captains, etc.",
            )
            if st.button("➕ Add Committee", type="primary", use_container_width=True):
                ok, msg = cm.add(ncn, nct, ncd, max_winners=nmw)
                if ok:
                    audit.log(
                        "ADD_COMMITTEE", "admin", f"{ncn} ({nct}, {nmw} positions)"
                    )
                    st.markdown(
                        f'<div class="success-box">✅ {msg}</div>',
                        unsafe_allow_html=True,
                    )
                    st.rerun()
                else:
                    st.markdown(
                        f'<div class="error-box">❌ {msg}</div>', unsafe_allow_html=True
                    )

    # ── TAB 4: NOMINATIONS ────────────────────────────────────────────────────
    with t4:
        ns1, ns2, ns3, ns4 = st.tabs(
            [
                "⏳ Pending Approval",
                "➕ Nominate (Admin)",
                "📤 Bulk Upload",
                "📋 All Nominations",
            ]
        )

        with ns1:
            pending = Candidate(db).get_pending()
            if not pending:
                st.markdown(
                    '<div class="success-box">🎉 All nominations reviewed — nothing pending!</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="warn-box">⏳ <strong>{len(pending)}</strong> nomination(s) need your review.</div>',
                    unsafe_allow_html=True,
                )
                for row in pending:
                    (
                        cid,
                        adm,
                        name,
                        ctype,
                        comm,
                        sc,
                        sh,
                        sg,
                        manifesto,
                        status,
                        nom_by,
                        created,
                    ) = row
                    st.markdown(
                        f"""
                    <div class="nom-card nom-pending">
                        <div style="display:flex;align-items:center;gap:14px;">
                            <span style="font-size:2.5rem;">{avatar(name or adm)}</span>
                            <div style="flex:1;">
                                <div style="font-weight:700;color:white;font-size:1.05rem;">{name or adm}</div>
                                <div style="color:#94a3b8;font-size:.83rem;">
                                    {ci(comm)['icon']} <strong>{comm}</strong> &nbsp;·&nbsp; {ctype}
                                    {'&nbsp;·&nbsp; Class '+sc if sc else ''}
                                    {'&nbsp;·&nbsp; '+sh+' House' if sh else ''}
                                    {'&nbsp;·&nbsp; '+sg if sg else ''}
                                </div>
                                <div style="color:#64748b;font-size:.78rem;margin-top:2px;">
                                    Self-nominated · {Utils.format_timestamp(created or '')}
                                </div>
                            </div>
                            <span class="badge badge-pending">PENDING</span>
                        </div>
                        {f'<div class="cand-manifesto" style="margin-top:12px;">"{manifesto}"</div>' if manifesto else ''}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    ac1, ac2, _ = st.columns([2, 2, 4])
                    with ac1:
                        if st.button(
                            "✅ Approve",
                            key=f"app_{cid}",
                            type="primary",
                            use_container_width=True,
                        ):
                            Candidate(db).approve(cid)
                            audit.log("APPROVE_NOM", "admin", f"{name}→{comm}")
                            st.rerun()
                    with ac2:
                        if st.button(
                            "❌ Reject",
                            key=f"rej_{cid}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            Candidate(db).reject(cid)
                            audit.log("REJECT_NOM", "admin", f"{name}→{comm}")
                            st.rerun()

        with ns2:
            if live_now:
                st.markdown(
                    '<div class="warn-box">⚠️ Election is live — nominations are locked. Stop the election to add nominations.</div>',
                    unsafe_allow_html=True,
                )
            else:
                c1, c2 = st.columns(2)
                with c1:
                    nom_adm = st.text_input("Admission Number").strip().lower()
                    nom_type = st.selectbox("Committee Type", ["School", "House"])
                    sc_l = voting.SCHOOL_COMMITTEES
                    hc_l = voting.HOUSE_COMMITTEES
                    if nom_type == "School":
                        nom_comm = st.selectbox("Committee", sc_l) if sc_l else None
                        nom_cls = st.selectbox(
                            "Class", ["7", "8", "9", "10", "11", "12"]
                        )
                        nom_hs = nom_grp = None
                    else:
                        nom_comm = st.selectbox("Committee", hc_l) if hc_l else None
                        nom_hs = st.selectbox("House", voting.HOUSES)
                        nom_grp = (
                            st.selectbox("Group", ["Junior (7-8)", "Senior (9-12)"])
                            .split("(")[0]
                            .strip()
                        )
                        nom_cls = None
                    nom_man = st.text_area("Manifesto (optional)", max_chars=200)
                with c2:
                    if nom_adm:
                        cp = Student(db).get(nom_adm)
                        if cp:
                            h = hm(cp[4])
                            st.markdown(
                                f"""
                            <div style="background:{h['bg']};border:1px solid {h['border']};
                                        border-radius:16px;padding:24px;text-align:center;">
                                <div style="font-size:3rem;">{avatar(cp[1])}</div>
                                <div style="font-weight:700;color:white;font-size:1.1rem;margin-top:8px;">{cp[1]}</div>
                                <div style="color:#94a3b8;">Class {cp[2]} · Section {cp[3]}</div>
                                <div style="color:{h['color']};font-weight:600;margin-top:4px;">{h['emoji']} {cp[4]} House</div>
                            </div>""",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<div class="warn-box">⚠️ Student not found</div>',
                                unsafe_allow_html=True,
                            )

                if st.button("✅ Nominate", type="primary", use_container_width=True):
                    if not nom_comm:
                        st.markdown(
                            '<div class="error-box">❌ No committees available.</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        cand = Student(db).get(nom_adm)
                        if not cand:
                            st.markdown(
                                f'<div class="error-box">❌ Student {nom_adm} not found.</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            ok, msg = Candidate(db).add(
                                nom_adm,
                                nom_type,
                                nom_comm,
                                nom_cls,
                                nom_hs,
                                nom_grp,
                                nom_man,
                                "approved",
                                "admin",
                            )
                            if ok:
                                st.markdown(
                                    f'<div class="success-box">✅ {cand[1]} nominated for {nom_comm}.</div>',
                                    unsafe_allow_html=True,
                                )
                                audit.log("NOMINATE", "admin", f"{cand[1]}→{nom_comm}")
                            else:
                                st.markdown(
                                    f'<div class="error-box">❌ {msg}</div>',
                                    unsafe_allow_html=True,
                                )

        with ns3:
            st.markdown("### 📤 Bulk Nomination Upload", unsafe_allow_html=True)
            st.markdown("""
            Upload an Excel file with columns: `admission_no`, `committee_type`, `committee_name`
            
            **Example:**
            | admission_no | committee_type | committee_name |
            |--------------|----------------|----------------|
            | jb001        | School         | Sports         |
            | jb002        | House          | Literary       |
            """)

            uploaded = st.file_uploader(
                "Choose Excel file", type=["xlsx", "xls"], key="bulk_nom"
            )

            if uploaded:
                try:
                    df = pd.read_excel(uploaded)
                    rows, parse_errors = Utils.parse_bulk_nomination_excel(df)

                    if parse_errors:
                        st.markdown(
                            '<div class="warn-box">⚠️ <strong>Parsing Errors:</strong></div>',
                            unsafe_allow_html=True,
                        )
                        for err in parse_errors:
                            st.error(err)

                    if rows:
                        st.markdown(
                            f'<div class="info-box">📋 Found {len(rows)} valid nomination(s)</div>',
                            unsafe_allow_html=True,
                        )
                        st.dataframe(
                            pd.DataFrame(
                                rows,
                                columns=[
                                    "admission_no",
                                    "committee_type",
                                    "committee_name",
                                ],
                            )
                        )

                        if st.button(
                            "✅ Import All", type="primary", key="bulk_import_btn"
                        ):
                            imported, import_errors = Candidate(db).bulk_add(rows)

                            if imported > 0:
                                st.markdown(
                                    f'<div class="success-box">✅ Imported {imported} nomination(s)</div>',
                                    unsafe_allow_html=True,
                                )
                                audit.log(
                                    "BULK_NOMINATE", "admin", f"{imported} nominations"
                                )

                            if import_errors:
                                st.markdown(
                                    '<div class="error-box">❌ <strong>Import Errors:</strong></div>',
                                    unsafe_allow_html=True,
                                )
                                for err in import_errors:
                                    st.error(err)

                            if imported > 0:
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.markdown(
                            '<div class="warn-box">⚠️ No valid rows found</div>',
                            unsafe_allow_html=True,
                        )

                except Exception as e:
                    st.markdown(
                        f'<div class="error-box">❌ Error reading file: {str(e)}</div>',
                        unsafe_allow_html=True,
                    )

        with ns4:
            all_noms = Candidate(db).get_all_with_names()
            if not all_noms:
                st.info("No nominations yet.")
            else:
                for ctype in ["School", "House"]:
                    rows = [r for r in all_noms if r[3] == ctype]
                    if not rows:
                        continue
                    st.markdown(
                        f"**{'🏫 School' if ctype=='School' else '🏠 House'}**",
                        unsafe_allow_html=True,
                    )
                    for row in rows:
                        (
                            cid,
                            adm,
                            name,
                            ct,
                            comm,
                            sc,
                            sh,
                            sg,
                            manifesto,
                            status,
                            nom_by,
                            created,
                        ) = row
                        badge_html = f'<span class="badge badge-{status}">{status.upper()}</span>'
                        nc1, nc2 = st.columns([7, 1])
                        nc1.markdown(
                            f"{avatar(name or adm)} **{name or adm}** → {ci(comm)['icon']} {comm} {badge_html}",
                            unsafe_allow_html=True,
                        )
                        if nc2.button("🗑️", key=f"rn_{cid}"):
                            Candidate(db).remove(cid)
                            audit.log("REMOVE_NOM", "admin", f"{name}←{comm}")
                            st.rerun()

    # ── TAB 5: ELECTION CONTROL ───────────────────────────────────────────────
    with t5:
        phase = election.get_phase()

        # Phase status banner
        if phase == "setup":
            st.markdown(
                '<div style="background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.4);'
                'border-radius:14px;padding:20px;text-align:center;">'
                '<strong style="color:#a5b4fc;font-size:1.2rem;">⚙️ SETUP Phase</strong><br>'
                '<span style="color:#94a3b8;font-size:.85rem;">Nominations open · Voting not started</span></div>',
                unsafe_allow_html=True,
            )
        elif phase == "live":
            st.markdown(
                '<div style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.4);'
                'border-radius:14px;padding:20px;text-align:center;">'
                '<span class="live-dot" style="display:inline-block;"></span> '
                '<strong style="color:#fca5a5;font-size:1.2rem;">🔴 LIVE Phase</strong><br>'
                '<span style="color:#94a3b8;font-size:.85rem;">Students can vote now</span></div>',
                unsafe_allow_html=True,
            )
        else:  # closed
            st.markdown(
                '<div style="background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.4);'
                'border-radius:14px;padding:20px;text-align:center;">'
                '<strong style="color:#6ee7b7;font-size:1.2rem;">✅ CLOSED Phase</strong><br>'
                '<span style="color:#94a3b8;font-size:.85rem;">Voting ended · Results public</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        ec1, ec2, ec3 = st.columns(3)

        # GO LIVE button (SETUP → LIVE)
        with ec1:
            if phase == "setup":
                if st.button("🚀 GO LIVE", use_container_width=True, type="primary"):
                    st.session_state.confirm_start = True
                if st.session_state.confirm_start:
                    st.markdown(
                        '<div class="info-box">⚡ Voting opens. Nominations lock. Pending nominations auto-reject.</div>',
                        unsafe_allow_html=True,
                    )
                    y1, y2 = st.columns(2)
                    with y1:
                        if st.button("✅ Confirm", key="ys"):
                            ok, msg = election.go_live()
                            if ok:
                                audit.log("GO_LIVE", "admin")
                                st.session_state.confirm_start = False
                                st.rerun()
                            else:
                                st.markdown(
                                    f'<div class="error-box">❌ {msg}</div>',
                                    unsafe_allow_html=True,
                                )
                                st.session_state.confirm_start = False
                    with y2:
                        if st.button("Cancel", key="ns"):
                            st.session_state.confirm_start = False
                            st.rerun()

        # CLOSE button (LIVE → CLOSED)
        with ec2:
            if phase == "live":
                if st.button(
                    "⏹ CLOSE Election", use_container_width=True, type="secondary"
                ):
                    st.session_state.confirm_stop = True
                if st.session_state.confirm_stop:
                    st.markdown(
                        '<div class="warn-box">⚠️ Voting stops. Results become public.</div>',
                        unsafe_allow_html=True,
                    )
                    y1, y2 = st.columns(2)
                    with y1:
                        if st.button("✅ Confirm", key="yst"):
                            ok, msg = election.close()
                            if ok:
                                audit.log("CLOSE_ELECTION", "admin")
                                st.session_state.confirm_stop = False
                                st.rerun()
                            else:
                                st.markdown(
                                    f'<div class="error-box">❌ {msg}</div>',
                                    unsafe_allow_html=True,
                                )
                    with y2:
                        if st.button("Cancel", key="nst"):
                            st.session_state.confirm_stop = False
                            st.rerun()

        # RESET button (any phase → SETUP with backup)
        with ec3:
            if st.button("🔄 RESET Election", use_container_width=True):
                st.session_state.confirm_reset = True
            if st.session_state.confirm_reset:
                st.markdown(
                    '<div class="error-box">🚨 Clears ALL votes. Backup created first.</div>',
                    unsafe_allow_html=True,
                )
                if st.checkbox("I understand and confirm reset", key="rack"):
                    y1, y2 = st.columns(2)
                    with y1:
                        if st.button("✅ Reset", key="yr"):
                            # Backup first
                            results = voting.get_results()
                            stats = election.get_statistics()
                            filename = Utils.backup_results(results, stats)
                            st.info(f"📦 Backup: {filename}")

                            # Now reset
                            ok, msg = election.reset()
                            if ok:
                                audit.log(
                                    "ELECTION_RESET", "admin", f"Backup: {filename}"
                                )
                                st.markdown(
                                    f'<div class="success-box">✅ {msg}</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f'<div class="error-box">❌ {msg}</div>',
                                    unsafe_allow_html=True,
                                )
                            st.session_state.confirm_reset = False
                            st.rerun()

        st.markdown("---", unsafe_allow_html=True)

        # Download pending voters
        st.markdown("### 📥 Download Pending Voters", unsafe_allow_html=True)
        pending = Student(db).get_pending_voters()
        if pending:
            excel_bytes = Utils.create_pending_voters_file(pending)
            st.download_button(
                "📊 Download Pending Voters Excel",
                excel_bytes,
                "pending_voters.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_pending",
            )
            st.caption(f"{len(pending)} student(s) have not voted yet.")
        else:
            st.success("✅ All students have voted!")

        st.divider()
        stats = election.get_statistics()
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Total Students", stats["total_students"])
        sc2.metric("Voted", stats["voted_students"])
        sc3.metric("Not Voted", stats["not_voted"])
        sc4.metric("Turnout", f"{stats['participation_rate']:.1f}%")

        if stats["not_voted"] > 0:
            with st.expander(
                f"👀 View {stats['not_voted']} student(s) who haven't voted yet"
            ):
                pv = db.execute(
                    "SELECT admission_no,name,class,house FROM students WHERE has_voted=0 ORDER BY name"
                ).fetchall()
                if pv:
                    st.dataframe(
                        pd.DataFrame(pv, columns=["Adm No", "Name", "Class", "House"]),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("All students have voted!")

    # ── TAB 6: RESULTS ────────────────────────────────────────────────────────
    with t6:
        rs1, rs2, rs3 = st.tabs(["🏆 Results", "📈 Statistics", "📋 Audit Log"])

        with rs1:
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()

            # Download buttons
            results_data = voting.get_results()
            stats_data = election.get_statistics()

            with rc2:
                if results_data:
                    res_file = Utils.create_results_file(results_data, stats_data)
                    st.download_button(
                        "📥 Download Full Results (Excel)",
                        data=res_file,
                        file_name=f'results_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary",
                    )
            with rc3:
                if results_data:
                    house_file = Utils.create_house_results_file(db, results_data)
                    st.download_button(
                        "🏠 Download House Results (Excel)",
                        data=house_file,
                        file_name=f'house_results_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

            if not results_data:
                st.markdown(
                    '<div class="info-box">📋 No results yet — nominations and votes needed first.</div>',
                    unsafe_allow_html=True,
                )
            else:
                for ctype in ["School", "House"]:
                    if ctype not in results_data:
                        continue
                    st.markdown(
                        f"## {'🏫 School Committees' if ctype=='School' else '🏠 House Committees'}",
                        unsafe_allow_html=True,
                    )

                    for comm_name, data in sorted(results_data[ctype].items()):
                        cands = data["candidates"]
                        total_cv = data["total_votes"]
                        max_w = data.get("max_winners", 1)
                        info = ci(comm_name)
                        pos_label = f"{max_w} position{'s' if max_w > 1 else ''}"

                        st.markdown(
                            f"""
                        <div class="comm-header">
                            <span class="comm-icon">{info['icon']}</span>
                            <div>
                                <div class="comm-title">{comm_name}</div>
                                <div class="comm-desc">{info['desc']} &nbsp;·&nbsp; {pos_label} &nbsp;·&nbsp; {total_cv} vote(s) cast</div>
                            </div>
                        </div>""",
                            unsafe_allow_html=True,
                        )

                        if not cands:
                            continue

                        # Tie banner + tie-break UI
                        tied_cands = [c for c in cands if c.get("is_tied")]
                        if tied_cands:
                            st.markdown(
                                '<div class="warn-box">⚖️ <strong>TIE</strong> — Multiple candidates share the top position. '
                                "Use the tie-break tool below to record your decision.</div>",
                                unsafe_allow_html=True,
                            )

                            # Tie-break UI (only in CLOSED phase)
                            if election.is_closed():
                                with st.expander(f"🔨 Break tie for {comm_name}"):
                                    options = {c["name"]: c["adm"] for c in tied_cands}
                                    chosen_name = st.selectbox(
                                        "Select winner",
                                        list(options.keys()),
                                        key=f"tb_sel_{comm_name}",
                                    )
                                    reason = st.text_input(
                                        "Reason (required)",
                                        key=f"tb_reason_{comm_name}",
                                        placeholder="e.g. Coin toss, teacher decision, re-vote...",
                                    )
                                    if st.button(
                                        "✅ Confirm Tie-Break",
                                        key=f"tb_btn_{comm_name}",
                                        type="primary",
                                    ):
                                        if not reason.strip():
                                            st.error("Reason is required.")
                                        else:
                                            Vote(db).record_tie_break(
                                                comm_name,
                                                options[chosen_name],
                                                reason.strip(),
                                                "admin",
                                            )
                                            st.success(
                                                f"✅ Tie-break recorded: {chosen_name} wins."
                                            )
                                            audit.log(
                                                "TIE_BREAK",
                                                "admin",
                                                f"{comm_name}: {chosen_name} ({reason})",
                                            )
                                            time.sleep(1)
                                            st.rerun()

                        # Podium (top 3, only when votes exist)
                        if total_cv > 0 and len(cands) >= 2:
                            top3 = cands[:3]
                            order = [1, 0, 2] if len(top3) >= 3 else [0, 1]
                            pcols = st.columns(len(order))
                            for pi, ri in enumerate(order):
                                if ri < len(top3):
                                    c_ = top3[ri]
                                    ph = hm(c_["house"])
                                    ht = 100 if ri == 0 else (75 if ri == 1 else 55)
                                    grad = (
                                        "linear-gradient(180deg,#f59e0b,#d97706)"
                                        if ri == 0
                                        else (
                                            "linear-gradient(180deg,#94a3b8,#64748b)"
                                            if ri == 1
                                            else "linear-gradient(180deg,#b45309,#92400e)"
                                        )
                                    )
                                    with pcols[pi]:
                                        st.markdown(
                                            f"""
                                        <div style="text-align:center;">
                                            <div style="font-size:.85rem;font-weight:600;color:white;margin-bottom:4px;">
                                                {avatar(c_['name'])} {c_['name']}
                                            </div>
                                            <div style="font-size:.75rem;color:#94a3b8;margin-bottom:6px;">
                                                {int(c_['votes'])} votes
                                                {'⚖️ TIE' if c_.get('is_tied') else ''}
                                            </div>
                                            <div style="background:{grad};height:{ht}px;border-radius:12px 12px 0 0;
                                                        display:flex;align-items:center;justify-content:center;font-size:1.8rem;">
                                                {RANK_ICONS[ri]}
                                            </div>
                                        </div>""",
                                            unsafe_allow_html=True,
                                        )
                            st.markdown("<br>", unsafe_allow_html=True)

                        # Full ranked list
                        for i, c_ in enumerate(cands):
                            ph = hm(c_["house"])
                            is_win = c_["is_winner"]
                            is_tied = c_.get("is_tied", False)
                            card_cls = (
                                "tied" if is_tied else ("winner" if is_win else "")
                            )
                            bar_cls = (
                                "bar-tied"
                                if is_tied
                                else ("bar-winner" if is_win else "bar-normal")
                            )
                            rank_ico = (
                                RANK_ICONS[i] if i < len(RANK_ICONS) else str(i + 1)
                            )
                            tie_tag = (
                                ' <span style="color:#f59e0b;font-size:.75rem;">⚖️ TIE</span>'
                                if is_tied
                                else ""
                            )
                            st.markdown(
                                f"""
                            <div class="result-card {card_cls}">
                                <span class="result-rank">{rank_ico}</span>
                                <span style="font-size:1.4rem;">{avatar(c_['name'])}</span>
                                <div class="result-info">
                                    <div class="result-name">{c_['name']}{tie_tag}</div>
                                    <div class="result-sub">
                                        Class {c_['class']} &nbsp;·&nbsp;
                                        <span style="color:{ph['color']}">{c_['house']} House</span>
                                    </div>
                                </div>
                                <div class="bar-wrap">
                                    <div class="bar-fill {bar_cls}" style="width:{c_['pct']}%;"></div>
                                </div>
                                <div class="result-right">
                                    <div class="result-votes">{int(c_['votes'])}</div>
                                    <div class="result-pct">{c_['pct']}%</div>
                                </div>
                            </div>""",
                                unsafe_allow_html=True,
                            )
                        st.markdown("<br>", unsafe_allow_html=True)

        with rs2:
            stats = Utils.get_vote_statistics(db)
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Total Students", stats["total_students"])
            sc2.metric(
                "Participated",
                f"{stats['voted_students']} ({stats['participation_rate']:.1f}%)",
            )
            sc3.metric("Total Votes Cast", stats["total_votes"])

            st.markdown("**House Participation**", unsafe_allow_html=True)
            hcols = st.columns(4)
            for i, house in enumerate(voting.HOUSES):
                total_h = db.execute(
                    "SELECT COUNT(*) FROM students WHERE house=?", (house,)
                ).fetchone()[0]
                voted_h = db.execute(
                    "SELECT COUNT(*) FROM students WHERE house=? AND has_voted=1",
                    (house,),
                ).fetchone()[0]
                pct_h = (voted_h / total_h * 100) if total_h > 0 else 0
                h_ = hm(house)
                hcols[i].markdown(
                    f"""
                <div class="house-card" style="background:{h_['bg']};border-color:{h_['border']};">
                    <div style="font-size:2rem;">{h_['icon']}</div>
                    <div style="font-weight:700;color:{h_['color']};font-size:1rem;">{house}</div>
                    <div style="font-size:1.4rem;font-weight:800;color:white;">{voted_h}/{total_h}</div>
                    <div style="font-size:.78rem;color:#94a3b8;">{pct_h:.0f}% voted</div>
                </div>""",
                    unsafe_allow_html=True,
                )

            if stats.get("votes_by_committee"):
                st.markdown("<br>**Votes by Committee**", unsafe_allow_html=True)
                df_vc = pd.DataFrame(
                    list(stats["votes_by_committee"].items()),
                    columns=["Committee", "Votes"],
                ).sort_values("Votes", ascending=False)
                st.dataframe(df_vc, use_container_width=True, hide_index=True)

        with rs3:
            logs = audit.get_all()
            if logs:
                df_l = pd.DataFrame(
                    logs, columns=["ID", "Action", "User", "Details", "IP", "Timestamp"]
                )
                df_l["Timestamp"] = df_l["Timestamp"].apply(Utils.format_timestamp)
                st.dataframe(
                    df_l[["ID", "Action", "User", "Details", "Timestamp"]],
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "📥 Export Audit Log (CSV)",
                    data=df_l[["ID", "Action", "User", "Details", "Timestamp"]].to_csv(
                        index=False
                    ),
                    file_name=f'audit_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv',
                )
            else:
                st.info("No audit logs yet.")

    # ── TAB 7: ANALYTICS ──────────────────────────────────────────────────────
    with t7:
        st.markdown("### 📈 Election Analytics Dashboard", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">📊 Comprehensive analytics and insights about the election</div>',
            unsafe_allow_html=True,
        )

        # Metrics Grid Layout
        st.markdown("#### 🎯 Key Metrics", unsafe_allow_html=True)

        # Row 1: Overall Statistics
        m1, m2, m3, m4 = st.columns(4)

        stats = election.get_statistics()

        with m1:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{stats['total_students']}</div>
                <div class="stat-label">Total Students</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with m2:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{stats['voted_students']}</div>
                <div class="stat-label">Students Voted</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with m3:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{stats['participation_rate']:.1f}%</div>
                <div class="stat-label">Participation Rate</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with m4:
            total_votes = stats.get("total_votes", 0)
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{total_votes}</div>
                <div class="stat-label">Total Votes Cast</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 2: Committee Statistics
        st.markdown("#### 🏛️ Committee Statistics", unsafe_allow_html=True)

        committees = Committee(db).get_all()
        school_committees = [c for c in committees if c[2] == "School"]
        house_committees = [c for c in committees if c[2] == "House"]

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{len(committees)}</div>
                <div class="stat-label">Total Committees</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{len(school_committees)}</div>
                <div class="stat-label">School Committees</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{len(house_committees)}</div>
                <div class="stat-label">House Committees</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with c4:
            total_candidates = len(Candidate(db).get_all())
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-num">{total_candidates}</div>
                <div class="stat-label">Total Candidates</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 3: House Participation
        st.markdown("#### 🏠 House Participation", unsafe_allow_html=True)

        house_cols = st.columns(4)
        for i, house in enumerate(voting.HOUSES):
            total_h = db.execute(
                "SELECT COUNT(*) FROM students WHERE house=?", (house,)
            ).fetchone()[0]
            voted_h = db.execute(
                "SELECT COUNT(*) FROM students WHERE house=? AND has_voted=1", (house,)
            ).fetchone()[0]
            pct_h = (voted_h / total_h * 100) if total_h > 0 else 0
            h_ = hm(house)

            with house_cols[i]:
                st.markdown(
                    f"""
                <div class="house-card" style="background:{h_['bg']};border-color:{h_['border']};">
                    <div style="font-size:2rem;">{h_['icon']}</div>
                    <div style="font-weight:700;color:{h_['color']};font-size:1rem;">{house}</div>
                    <div style="font-size:1.4rem;font-weight:800;color:white;">{voted_h}/{total_h}</div>
                    <div style="font-size:.78rem;color:#94a3b8;">{pct_h:.1f}% voted</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Task 4.2: Class-wise participation breakdown
        st.markdown(
            "#### 📚 Class-wise Participation Breakdown", unsafe_allow_html=True
        )

        # Sub-task 4.2.1 & 4.2.2: Query votes grouped by class and calculate participation rate
        class_data = db.execute("""
            SELECT 
                class,
                COUNT(*) as total,
                SUM(has_voted) as voted,
                ROUND(CAST(SUM(has_voted) AS FLOAT) / COUNT(*) * 100, 1) as participation_rate
            FROM students
            GROUP BY class
            ORDER BY class
        """).fetchall()

        if class_data:
            # Convert to list of dicts for easier manipulation
            class_stats = [
                {
                    "class": row[0],
                    "total": row[1],
                    "voted": row[2],
                    "participation_rate": row[3],
                }
                for row in class_data
            ]

            # Sub-task 4.2.4: Identify top 3 and bottom 3 classes
            sorted_by_rate = sorted(
                class_stats, key=lambda x: x["participation_rate"], reverse=True
            )
            top_3_classes = set(c["class"] for c in sorted_by_rate[:3])
            bottom_3_classes = set(c["class"] for c in sorted_by_rate[-3:])

            # Sub-task 4.2.3: Display as horizontal bar chart
            # Prepare data for chart
            classes = [c["class"] for c in class_stats]
            rates = [c["participation_rate"] for c in class_stats]
            voted = [c["voted"] for c in class_stats]
            total = [c["total"] for c in class_stats]

            # Color bars based on top 3 / bottom 3
            colors = []
            for c in class_stats:
                if c["class"] in top_3_classes:
                    colors.append("#22c55e")  # Green for top 3
                elif c["class"] in bottom_3_classes:
                    colors.append("#ef4444")  # Red for bottom 3
                else:
                    colors.append("#6366f1")  # Default purple

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    y=classes,
                    x=rates,
                    orientation="h",
                    marker=dict(
                        color=colors, line=dict(color="rgba(255,255,255,0.2)", width=1)
                    ),
                    text=[f"{r}% ({v}/{t})" for r, v, t in zip(rates, voted, total)],
                    textposition="auto",
                    hovertemplate="<b>Class %{y}</b><br>"
                    + "Participation: %{x}%<br>"
                    + "<extra></extra>",
                )
            )

            fig.update_layout(
                title=dict(
                    text="Participation Rate by Class",
                    font=dict(size=16, color="white"),
                ),
                xaxis=dict(
                    title="Participation Rate (%)",
                    range=[0, 100],
                    gridcolor="rgba(255,255,255,0.1)",
                    color="white",
                ),
                yaxis=dict(
                    title="Class", gridcolor="rgba(255,255,255,0.1)", color="white"
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                height=400,
                margin=dict(l=60, r=40, t=60, b=60),
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display top 3 and bottom 3 in cards
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("##### 🏆 Top 3 Performing Classes", unsafe_allow_html=True)
                for i, cls in enumerate(sorted_by_rate[:3], 1):
                    medal = ["🥇", "🥈", "🥉"][i - 1]
                    st.markdown(
                        f"""
                    <div class="stat-card" style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);">
                        <div style="font-size:1.5rem;">{medal} Class {cls['class']}</div>
                        <div style="font-size:1.2rem;font-weight:700;color:#22c55e;">{cls['participation_rate']}%</div>
                        <div style="font-size:0.9rem;color:#94a3b8;">{cls['voted']} out of {cls['total']} students voted</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            with col2:
                st.markdown(
                    "##### 📉 Bottom 3 Performing Classes", unsafe_allow_html=True
                )
                for i, cls in enumerate(sorted_by_rate[-3:][::-1], 1):
                    st.markdown(
                        f"""
                    <div class="stat-card" style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);">
                        <div style="font-size:1.5rem;">Class {cls['class']}</div>
                        <div style="font-size:1.2rem;font-weight:700;color:#ef4444;">{cls['participation_rate']}%</div>
                        <div style="font-size:0.9rem;color:#94a3b8;">{cls['voted']} out of {cls['total']} students voted</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No class data available yet.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Task 4.3: House-wise participation breakdown
        st.markdown(
            "#### 🏠 House-wise Participation Breakdown", unsafe_allow_html=True
        )

        # Sub-task 4.3.1 & 4.3.2: Query votes grouped by house and calculate participation rate
        house_data = db.execute("""
            SELECT 
                house,
                COUNT(*) as total,
                SUM(has_voted) as voted,
                ROUND(CAST(SUM(has_voted) AS FLOAT) / COUNT(*) * 100, 1) as participation_rate
            FROM students
            GROUP BY house
            ORDER BY participation_rate DESC
        """).fetchall()

        if house_data:
            # Convert to list of dicts for easier manipulation
            house_stats = [
                {
                    "house": row[0],
                    "total": row[1],
                    "voted": row[2],
                    "participation_rate": row[3],
                }
                for row in house_data
            ]

            # Sub-task 4.3.3: Display with house colors
            # Prepare data for chart
            houses = [h["house"] for h in house_stats]
            rates = [h["participation_rate"] for h in house_stats]
            voted = [h["voted"] for h in house_stats]
            total = [h["total"] for h in house_stats]

            # Use house-specific colors
            colors = [hm(h["house"])["color"] for h in house_stats]

            fig_house = go.Figure()

            fig_house.add_trace(
                go.Bar(
                    y=houses,
                    x=rates,
                    orientation="h",
                    marker=dict(
                        color=colors, line=dict(color="rgba(255,255,255,0.2)", width=1)
                    ),
                    text=[f"{r}% ({v}/{t})" for r, v, t in zip(rates, voted, total)],
                    textposition="auto",
                    hovertemplate="<b>%{y} House</b><br>"
                    + "Participation: %{x}%<br>"
                    + "<extra></extra>",
                )
            )

            fig_house.update_layout(
                title=dict(
                    text="Participation Rate by House",
                    font=dict(size=16, color="white"),
                ),
                xaxis=dict(
                    title="Participation Rate (%)",
                    range=[0, 100],
                    gridcolor="rgba(255,255,255,0.1)",
                    color="white",
                ),
                yaxis=dict(
                    title="House", gridcolor="rgba(255,255,255,0.1)", color="white"
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                height=350,
                margin=dict(l=80, r=40, t=60, b=60),
            )

            st.plotly_chart(fig_house, use_container_width=True)

            # Sub-task 4.3.4: Add house competition leaderboard
            st.markdown(
                "##### 🏆 House Competition Leaderboard", unsafe_allow_html=True
            )

            leaderboard_cols = st.columns(4)

            for i, house_stat in enumerate(house_stats):
                house_name = house_stat["house"]
                h_meta = hm(house_name)
                rank = i + 1
                rank_icon = ["🥇", "🥈", "🥉", "4️⃣"][i] if i < 4 else "🏠"

                with leaderboard_cols[i]:
                    st.markdown(
                        f"""
                    <div class="house-card" style="background:{h_meta['bg']};border:2px solid {h_meta['border']};border-radius:16px;padding:20px;text-align:center;">
                        <div style="font-size:2.5rem;margin-bottom:8px;">{rank_icon}</div>
                        <div style="font-size:1.8rem;margin-bottom:4px;">{h_meta['icon']}</div>
                        <div style="font-weight:800;color:{h_meta['color']};font-size:1.1rem;margin-bottom:8px;">{house_name}</div>
                        <div style="font-size:1.8rem;font-weight:900;color:white;margin-bottom:4px;">{house_stat['participation_rate']}%</div>
                        <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:8px;">{house_stat['voted']}/{house_stat['total']} students</div>
                        <div style="font-size:0.75rem;color:{h_meta['color']};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Rank #{rank}</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Show house competition summary
            st.markdown("<br>", unsafe_allow_html=True)

            winner_house = house_stats[0]
            h_winner = hm(winner_house["house"])

            st.markdown(
                f"""
            <div class="info-box" style="background:{h_winner['bg']};border:2px solid {h_winner['border']};text-align:center;padding:24px;">
                <div style="font-size:1.5rem;margin-bottom:8px;">{h_winner['icon']} 🏆</div>
                <div style="font-size:1.2rem;font-weight:700;color:{h_winner['color']};margin-bottom:4px;">
                    {winner_house['house']} House Leads the Competition!
                </div>
                <div style="font-size:0.95rem;color:#94a3b8;">
                    With {winner_house['participation_rate']}% participation rate, {winner_house['house']} House shows the strongest democratic engagement.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No house data available yet.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Task 4.4: Voting timeline (hourly trends)
        st.markdown("#### ⏰ Voting Timeline (Hourly Trends)", unsafe_allow_html=True)

        # Sub-task 4.4.1: Parse vote timestamps by hour
        vote_timestamps = db.execute("""
            SELECT created_at
            FROM votes
            ORDER BY created_at
        """).fetchall()

        if vote_timestamps and len(vote_timestamps) > 0:
            import pandas as pd

            # Parse timestamps and group by hour
            timestamps = [row[0] for row in vote_timestamps]
            df_votes = pd.DataFrame({"timestamp": timestamps})

            # Convert to datetime and extract hour
            df_votes["datetime"] = pd.to_datetime(df_votes["timestamp"])
            df_votes["date"] = df_votes["datetime"].dt.date
            df_votes["hour"] = df_votes["datetime"].dt.hour
            df_votes["date_hour"] = df_votes["datetime"].dt.strftime("%Y-%m-%d %H:00")

            # Group by hour and count votes
            hourly_counts = (
                df_votes.groupby("date_hour").size().reset_index(name="votes")
            )
            hourly_counts["datetime"] = pd.to_datetime(hourly_counts["date_hour"])
            hourly_counts = hourly_counts.sort_values("datetime")

            # Sub-task 4.4.4: Calculate average votes per hour
            total_votes = len(vote_timestamps)
            hours_with_votes = len(hourly_counts)
            avg_votes_per_hour = (
                total_votes / hours_with_votes if hours_with_votes > 0 else 0
            )

            # Sub-task 4.4.3: Identify peak voting hours
            peak_hour_data = hourly_counts.loc[hourly_counts["votes"].idxmax()]
            peak_hour = peak_hour_data["date_hour"]
            peak_votes = peak_hour_data["votes"]

            # Display key metrics
            metric_cols = st.columns(3)

            with metric_cols[0]:
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);">
                    <div style="font-size:2rem;font-weight:800;color:#818cf8;">{total_votes}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Total Votes Cast</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with metric_cols[1]:
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);">
                    <div style="font-size:2rem;font-weight:800;color:#22c55e;">{avg_votes_per_hour:.1f}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Avg Votes/Hour</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with metric_cols[2]:
                peak_time = pd.to_datetime(peak_hour).strftime("%I:%M %p")
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);">
                    <div style="font-size:1.3rem;font-weight:800;color:#f59e0b;">{peak_time}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Peak Hour ({peak_votes} votes)</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Sub-task 4.4.2: Create line chart showing votes over time
            # Prepare data for line chart
            hours_display = [
                pd.to_datetime(h).strftime("%I:%M %p<br>%b %d")
                for h in hourly_counts["date_hour"]
            ]
            votes_count = hourly_counts["votes"].tolist()

            # Highlight peak hours
            colors = ["#f59e0b" if v == peak_votes else "#6366f1" for v in votes_count]

            fig_timeline = go.Figure()

            # Add line trace
            fig_timeline.add_trace(
                go.Scatter(
                    x=hourly_counts["datetime"],
                    y=votes_count,
                    mode="lines+markers",
                    name="Votes",
                    line=dict(color="#6366f1", width=3),
                    marker=dict(
                        size=10,
                        color=colors,
                        line=dict(color="rgba(255,255,255,0.3)", width=2),
                    ),
                    fill="tozeroy",
                    fillcolor="rgba(99,102,241,0.1)",
                    hovertemplate="<b>%{x|%I:%M %p, %b %d}</b><br>"
                    + "Votes: %{y}<br>"
                    + "<extra></extra>",
                )
            )

            # Add average line
            fig_timeline.add_hline(
                y=avg_votes_per_hour,
                line_dash="dash",
                line_color="#22c55e",
                annotation_text=f"Average: {avg_votes_per_hour:.1f} votes/hour",
                annotation_position="right",
                annotation_font_color="#22c55e",
            )

            fig_timeline.update_layout(
                title=dict(
                    text="Voting Activity Over Time",
                    font=dict(size=18, color="white", family="Inter"),
                ),
                xaxis=dict(
                    title="Time",
                    gridcolor="rgba(255,255,255,0.1)",
                    color="white",
                    tickformat="%I:%M %p<br>%b %d",
                ),
                yaxis=dict(
                    title="Number of Votes",
                    gridcolor="rgba(255,255,255,0.1)",
                    color="white",
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white", family="Inter"),
                height=450,
                margin=dict(l=60, r=40, t=80, b=60),
                hovermode="x unified",
                showlegend=False,
            )

            st.plotly_chart(fig_timeline, use_container_width=True)

            # Show peak hours details
            st.markdown("##### 🔥 Peak Voting Hours", unsafe_allow_html=True)

            # Get top 3 peak hours
            top_hours = hourly_counts.nlargest(3, "votes")

            peak_cols = st.columns(3)

            for i, (idx, row) in enumerate(top_hours.iterrows()):
                medal = ["🥇", "🥈", "🥉"][i]
                hour_time = pd.to_datetime(row["date_hour"]).strftime("%I:%M %p")
                hour_date = pd.to_datetime(row["date_hour"]).strftime("%b %d, %Y")

                with peak_cols[i]:
                    st.markdown(
                        f"""
                    <div class="stat-card" style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);">
                        <div style="font-size:2rem;margin-bottom:8px;">{medal}</div>
                        <div style="font-size:1.3rem;font-weight:700;color:#f59e0b;margin-bottom:4px;">{hour_time}</div>
                        <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:8px;">{hour_date}</div>
                        <div style="font-size:1.5rem;font-weight:800;color:white;">{row['votes']} votes</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Show hourly breakdown table
            with st.expander("📊 View Detailed Hourly Breakdown"):
                df_display = hourly_counts.copy()
                df_display["Time"] = df_display["datetime"].dt.strftime("%I:%M %p")
                df_display["Date"] = df_display["datetime"].dt.strftime("%b %d, %Y")
                df_display["Votes"] = df_display["votes"]
                df_display["% of Total"] = (
                    df_display["votes"] / total_votes * 100
                ).round(1)

                st.dataframe(
                    df_display[["Date", "Time", "Votes", "% of Total"]],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.markdown(
                '<div class="info-box">📊 No voting data available yet. '
                "The timeline will appear once students start voting.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Task 4.5: Committee Popularity Metrics
        st.markdown("#### 📊 Committee Popularity Metrics", unsafe_allow_html=True)

        # Sub-task 4.5.1: Calculate total votes per committee
        committee_votes = db.execute("""
            SELECT 
                committee_name,
                COUNT(*) as total_votes
            FROM votes
            GROUP BY committee_name
            ORDER BY total_votes DESC
        """).fetchall()

        if committee_votes and len(committee_votes) > 0:
            # Convert to list of dicts
            committee_stats = [
                {"committee": row[0], "total_votes": row[1]} for row in committee_votes
            ]

            # Get candidate counts per committee
            candidate_counts = db.execute("""
                SELECT 
                    committee_name,
                    COUNT(*) as candidate_count
                FROM candidates
                WHERE status = 'approved'
                GROUP BY committee_name
            """).fetchall()

            candidate_map = {row[0]: row[1] for row in candidate_counts}

            # Get total voters (students who voted)
            total_voters = stats["voted_students"]

            # Enrich committee stats with candidate counts and ratios
            for comm in committee_stats:
                comm["candidates"] = candidate_map.get(comm["committee"], 0)
                # Sub-task 4.5.3: Calculate candidate-to-voter ratio
                if total_voters > 0:
                    comm["candidate_voter_ratio"] = comm["candidates"] / total_voters
                    comm["participation_rate"] = (
                        comm["total_votes"] / total_voters
                    ) * 100
                else:
                    comm["candidate_voter_ratio"] = 0
                    comm["participation_rate"] = 0

            # Sub-task 4.5.2: Identify most contested committees (highest candidate-to-vote ratio)
            # A committee is "contested" when it has many candidates relative to votes received
            for comm in committee_stats:
                if comm["total_votes"] > 0:
                    comm["contest_ratio"] = comm["candidates"] / comm["total_votes"]
                else:
                    comm["contest_ratio"] = 0

            sorted_by_contest = sorted(
                committee_stats, key=lambda x: x["contest_ratio"], reverse=True
            )
            most_contested = sorted_by_contest[:3]

            # Sub-task 4.5.4: Identify committees with low participation
            sorted_by_participation = sorted(
                committee_stats, key=lambda x: x["participation_rate"]
            )
            low_participation = [
                c for c in sorted_by_participation if c["participation_rate"] < 50
            ][:3]

            # Display metrics grid
            metric_cols = st.columns(4)

            with metric_cols[0]:
                total_committee_votes = sum(c["total_votes"] for c in committee_stats)
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);">
                    <div style="font-size:2rem;font-weight:800;color:#818cf8;">{total_committee_votes}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Total Committee Votes</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with metric_cols[1]:
                avg_votes_per_committee = (
                    total_committee_votes / len(committee_stats)
                    if len(committee_stats) > 0
                    else 0
                )
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);">
                    <div style="font-size:2rem;font-weight:800;color:#22c55e;">{avg_votes_per_committee:.1f}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Avg Votes/Committee</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with metric_cols[2]:
                most_popular = max(committee_stats, key=lambda x: x["total_votes"])
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);">
                    <div style="font-size:1.2rem;font-weight:800;color:#f59e0b;">{most_popular['committee']}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Most Popular ({most_popular['total_votes']} votes)</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with metric_cols[3]:
                active_committees = len(committee_stats)
                st.markdown(
                    f"""
                <div class="stat-card" style="background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.3);">
                    <div style="font-size:2rem;font-weight:800;color:#a855f7;">{active_committees}</div>
                    <div style="font-size:0.85rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Active Committees</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Chart: Total votes per committee
            st.markdown(
                "##### 📊 Votes Distribution by Committee", unsafe_allow_html=True
            )

            committees = [c["committee"] for c in committee_stats]
            votes = [c["total_votes"] for c in committee_stats]
            candidates = [c["candidates"] for c in committee_stats]

            fig_committee = go.Figure()

            # Add votes bar
            fig_committee.add_trace(
                go.Bar(
                    x=committees,
                    y=votes,
                    name="Votes Received",
                    marker=dict(
                        color="#6366f1",
                        line=dict(color="rgba(255,255,255,0.2)", width=1),
                    ),
                    text=votes,
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>"
                    + "Votes: %{y}<br>"
                    + "<extra></extra>",
                )
            )

            # Add candidates line
            fig_committee.add_trace(
                go.Scatter(
                    x=committees,
                    y=candidates,
                    name="Candidates",
                    mode="lines+markers",
                    line=dict(color="#f59e0b", width=3),
                    marker=dict(size=10, color="#f59e0b"),
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>"
                    + "Candidates: %{y}<br>"
                    + "<extra></extra>",
                )
            )

            fig_committee.update_layout(
                title=dict(
                    text="Committee Votes vs Candidates",
                    font=dict(size=16, color="white"),
                ),
                xaxis=dict(
                    title="Committee", gridcolor="rgba(255,255,255,0.1)", color="white"
                ),
                yaxis=dict(
                    title="Votes Received",
                    gridcolor="rgba(255,255,255,0.1)",
                    color="white",
                ),
                yaxis2=dict(
                    title="Number of Candidates",
                    overlaying="y",
                    side="right",
                    color="#f59e0b",
                    gridcolor="rgba(0,0,0,0)",
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                height=400,
                margin=dict(l=60, r=60, t=60, b=100),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )

            st.plotly_chart(fig_committee, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Sub-task 4.5.2: Show most contested committees
            st.markdown("##### 🔥 Most Contested Committees", unsafe_allow_html=True)
            st.markdown(
                '<div class="info-box">Committees with the highest competition (candidates per vote received)</div>',
                unsafe_allow_html=True,
            )

            contest_cols = st.columns(3)

            for i, comm in enumerate(most_contested[:3]):
                medal = ["🥇", "🥈", "🥉"][i]

                with contest_cols[i]:
                    st.markdown(
                        f"""
                    <div class="stat-card" style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);">
                        <div style="font-size:2rem;margin-bottom:8px;">{medal}</div>
                        <div style="font-size:1.2rem;font-weight:700;color:#ef4444;margin-bottom:4px;">{comm['committee']}</div>
                        <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:8px;">{comm['candidates']} candidates, {comm['total_votes']} votes</div>
                        <div style="font-size:1.3rem;font-weight:800;color:white;">Ratio: {comm['contest_ratio']:.2f}</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # Sub-task 4.5.3: Display candidate-to-voter ratio
            st.markdown("##### 👥 Candidate-to-Voter Ratios", unsafe_allow_html=True)

            # Create a table view
            ratio_data = []
            for comm in committee_stats:
                ratio_data.append(
                    {
                        "Committee": comm["committee"],
                        "Candidates": comm["candidates"],
                        "Votes": comm["total_votes"],
                        "Participation": f"{comm['participation_rate']:.1f}%",
                        "Candidate/Voter Ratio": f"{comm['candidate_voter_ratio']:.4f}",
                    }
                )

            df_ratios = pd.DataFrame(ratio_data)
            st.dataframe(df_ratios, use_container_width=True, hide_index=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Sub-task 4.5.4: Identify committees with low participation
            if low_participation:
                st.markdown(
                    "##### 📉 Committees with Low Participation", unsafe_allow_html=True
                )
                st.markdown(
                    '<div class="warn-box">⚠️ These committees received votes from less than 50% of voters</div>',
                    unsafe_allow_html=True,
                )

                low_cols = st.columns(min(3, len(low_participation)))

                for i, comm in enumerate(low_participation):
                    with low_cols[i]:
                        st.markdown(
                            f"""
                        <div class="stat-card" style="background:rgba(100,116,139,0.1);border:1px solid rgba(100,116,139,0.3);">
                            <div style="font-size:1.2rem;font-weight:700;color:#64748b;margin-bottom:8px;">{comm['committee']}</div>
                            <div style="font-size:1.5rem;font-weight:800;color:#94a3b8;margin-bottom:4px;">{comm['participation_rate']:.1f}%</div>
                            <div style="font-size:0.85rem;color:#64748b;">{comm['total_votes']} votes from {total_voters} voters</div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    '<div class="success-box">✅ All committees have healthy participation rates (50%+)</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="info-box">📊 No committee voting data available yet. '
                "Metrics will appear once students start voting.</div>",
                unsafe_allow_html=True,
            )

    # ── TAB 8: RECORDS ────────────────────────────────────────────────────────
    with t8:
        st.markdown(
            '<div class="info-box">🔒 Anonymous records only — vote tokens are shown, '
            "not voter identities.</div>",
            unsafe_allow_html=True,
        )
        votes = Vote(db).get_all_votes()
        if votes:
            # Build candidate name cache in one query
            name_map = {s[0]: s[1] for s in Student(db).get_all()}
            df_v = pd.DataFrame(
                votes, columns=["ID", "Cand Adm", "Committee", "Timestamp"]
            )
            df_v["Candidate"] = df_v["Cand Adm"].map(name_map).fillna("Unknown")
            df_v["Timestamp"] = df_v["Timestamp"].apply(Utils.format_timestamp)
            st.dataframe(
                df_v[["ID", "Candidate", "Committee", "Timestamp"]],
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "📥 Export Votes CSV",
                data=df_v[["ID", "Candidate", "Committee", "Timestamp"]].to_csv(
                    index=False
                ),
                file_name=f'votes_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv',
            )
            st.divider()
            st.markdown(
                "#### 🗑️ Delete a Vote (Admin Override)", unsafe_allow_html=True
            )
            st.markdown(
                '<div class="warn-box">⚠️ Permanently logged. A reason is required.</div>',
                unsafe_allow_html=True,
            )
            dv_id = st.number_input("Vote ID", min_value=1, step=1)
            dv_r = st.text_input("Reason (required)")
            if st.button("Delete Vote", type="secondary"):
                if not dv_r.strip():
                    st.markdown(
                        '<div class="error-box">❌ Reason required.</div>',
                        unsafe_allow_html=True,
                    )
                elif Vote(db).delete_vote(int(dv_id)):
                    audit.log("DELETE_VOTE", "admin", f"ID {dv_id}: {dv_r}")
                    st.markdown(
                        '<div class="success-box">✅ Deleted and logged.</div>',
                        unsafe_allow_html=True,
                    )
                    st.rerun()
                else:
                    st.markdown(
                        '<div class="error-box">❌ Vote ID not found.</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No votes recorded yet.")

    # ── TAB 9: ADMIN MANAGEMENT ───────────────────────────────────────────────
    with t9:
        st.markdown("#### 🔐 Admin User Management", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">🔒 Manage administrator credentials and security settings.</div>',
            unsafe_allow_html=True,
        )

        # Display current admin info
        st.markdown("##### Current Admin Account", unsafe_allow_html=True)
        admin_id = auth.ADMIN_ID

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
            <div class="stat-card">
                <div style="font-size:1rem;color:#64748b;margin-bottom:8px;">Admin Username</div>
                <div style="font-size:1.3rem;font-weight:700;color:white;">{admin_id}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            # Check if password is still default
            default_hash = auth._legacy_hash("JB2026Secure")
            is_default = auth._admin_hash == default_hash
            status_color = "#ef4444" if is_default else "#10b981"
            status_text = "⚠️ Default Password" if is_default else "✅ Custom Password"

            st.markdown(
                f"""
            <div class="stat-card" style="border-color:{status_color}33;">
                <div style="font-size:1rem;color:#64748b;margin-bottom:8px;">Password Status</div>
                <div style="font-size:1.1rem;font-weight:700;color:{status_color};">{status_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if is_default:
            st.markdown(
                '<div class="warn-box">⚠️ <strong>Security Warning:</strong> You are using the default password. '
                "Please change it immediately to secure your admin account.</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # Change password section
        st.markdown("##### 🔑 Change Admin Password", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">💡 Choose a strong password with at least 8 characters, '
            "including uppercase, lowercase, numbers, and special characters.</div>",
            unsafe_allow_html=True,
        )

        with st.form("change_admin_password"):
            current_pwd = st.text_input(
                "Current Password", type="password", key="admin_current_pwd"
            )
            new_pwd = st.text_input(
                "New Password", type="password", key="admin_new_pwd"
            )
            confirm_pwd = st.text_input(
                "Confirm New Password", type="password", key="admin_confirm_pwd"
            )

            col1, col2 = st.columns([3, 1])
            with col2:
                submit = st.form_submit_button(
                    "🔄 Change Password", use_container_width=True, type="primary"
                )

            if submit:
                # Validate current password
                if not auth._verify_password(current_pwd, auth._admin_hash):
                    st.markdown(
                        '<div class="error-box">❌ Current password is incorrect.</div>',
                        unsafe_allow_html=True,
                    )
                elif len(new_pwd) < 8:
                    st.markdown(
                        '<div class="error-box">❌ New password must be at least 8 characters long.</div>',
                        unsafe_allow_html=True,
                    )
                elif new_pwd != confirm_pwd:
                    st.markdown(
                        '<div class="error-box">❌ New passwords do not match.</div>',
                        unsafe_allow_html=True,
                    )
                elif new_pwd == current_pwd:
                    st.markdown(
                        '<div class="error-box">❌ New password must be different from current password.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Password strength check
                    has_upper = any(c.isupper() for c in new_pwd)
                    has_lower = any(c.islower() for c in new_pwd)
                    has_digit = any(c.isdigit() for c in new_pwd)
                    has_special = any(
                        c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_pwd
                    )

                    strength_score = sum([has_upper, has_lower, has_digit, has_special])

                    if strength_score < 3:
                        st.markdown(
                            '<div class="warn-box">⚠️ Weak password. Consider adding uppercase, lowercase, '
                            "numbers, and special characters for better security.</div>",
                            unsafe_allow_html=True,
                        )

                    # Change the password
                    if auth.set_admin_password(new_pwd):
                        # Update the in-memory hash
                        auth._admin_hash = auth._pbkdf2_hash(new_pwd)
                        audit.log(
                            "ADMIN_PASSWORD_CHANGED",
                            "admin",
                            "Password updated successfully",
                        )
                        st.markdown(
                            '<div class="success-box">✅ Admin password changed successfully! '
                            "Please remember your new password.</div>",
                            unsafe_allow_html=True,
                        )
                        st.balloons()
                    else:
                        st.markdown(
                            '<div class="error-box">❌ Failed to update password. Database error.</div>',
                            unsafe_allow_html=True,
                        )

        st.divider()

        # Security best practices
        st.markdown("##### 🛡️ Security Best Practices", unsafe_allow_html=True)
        st.markdown(
            """
        <div class="glass" style="padding:20px;">
            <ul style="color:#cbd5e1;line-height:1.8;">
                <li><strong>Use a strong password:</strong> At least 8 characters with mixed case, numbers, and symbols</li>
                <li><strong>Don't share credentials:</strong> Keep your admin password confidential</li>
                <li><strong>Change regularly:</strong> Update your password periodically</li>
                <li><strong>Avoid common passwords:</strong> Don't use easily guessable passwords like "admin123" or "password"</li>
                <li><strong>Use unique passwords:</strong> Don't reuse passwords from other accounts</li>
                <li><strong>Monitor audit logs:</strong> Check the Records tab regularly for suspicious activity</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Password reset warning
        st.markdown("##### ⚠️ Lost Password Recovery", unsafe_allow_html=True)
        st.markdown(
            '<div class="warn-box">If you forget your admin password, you will need to manually reset it '
            "by deleting the <code>admin_password_hash</code> entry from the <code>settings</code> table "
            "in the database, which will restore the default password <code>JB2026Secure</code>.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="civic-fact" style="margin-top:32px;">💡 {fact}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  STUDENT PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.user_type == "student":
    sd = st.session_state.user_data
    fresh = Student(db).get(sd[0])
    h = hm(fresh[4])
    grp = voting.get_eligible_house_group(fresh[2])

    # ── Check for saved votes on login (Task 3.2.1) ──────────────────────────
    # Only check once per session, not on every rerun
    if "checked_saved_votes" not in st.session_state:
        st.session_state.checked_saved_votes = False

    if not st.session_state.checked_saved_votes and fresh[7] == 0:  # Not voted yet
        saved_votes = load_vote_progress(fresh[0])

        if saved_votes:
            # Task 3.2.2: Validate saved votes are still valid
            valid_votes = {}
            invalid_reasons = []

            # Check if election is still live
            if not election.is_live():
                invalid_reasons.append("Election is no longer live")
            else:
                # Validate each saved vote
                for comm_key, candidate_adm in saved_votes.items():
                    if candidate_adm == ABSTAIN:
                        valid_votes[comm_key] = candidate_adm
                        continue

                    # Check if candidate is still approved
                    db_committee = comm_key.replace("House-", "")
                    is_valid, msg = voting.verify_vote_integrity(
                        fresh[0], candidate_adm, db_committee
                    )

                    if is_valid:
                        valid_votes[comm_key] = candidate_adm
                    else:
                        invalid_reasons.append(f"{db_committee}: {msg}")

            # Task 3.2.3: Show "Resume voting" option if valid votes found
            if valid_votes and not invalid_reasons:
                st.session_state.has_valid_saved_votes = True
                st.session_state.valid_saved_votes = valid_votes
                st.session_state.saved_votes_count = len(
                    [v for v in valid_votes.values() if v != ABSTAIN]
                )
                st.session_state.saved_votes_timestamp = (
                    st.session_state.saved_votes_timestamp
                )
            elif valid_votes and invalid_reasons:
                # Some votes are valid, some are not
                st.session_state.has_valid_saved_votes = True
                st.session_state.valid_saved_votes = valid_votes
                st.session_state.saved_votes_count = len(
                    [v for v in valid_votes.values() if v != ABSTAIN]
                )
                st.session_state.saved_votes_warnings = invalid_reasons
            else:
                # No valid votes, clear saved data
                clear_vote_progress()
                st.session_state.has_valid_saved_votes = False
        else:
            st.session_state.has_valid_saved_votes = False

        st.session_state.checked_saved_votes = True

    # ── Welcome header ──
    wc1, wc2 = st.columns([8, 1])
    with wc1:
        st.markdown(
            f"""
        <div class="welcome-card" style="background:{h['bg']};border-color:{h['border']};">
            <span style="font-size:3.2rem;">{avatar(fresh[1])}</span>
            <div>
                <div style="font-size:1.4rem;font-weight:800;color:white;">{fresh[1]}</div>
                <div style="color:#94a3b8;margin-top:2px;">
                    Class {fresh[2]} &nbsp;·&nbsp; Section {fresh[3]} &nbsp;·&nbsp;
                    <span style="color:{h['color']};font-weight:700;">{h['emoji']} {fresh[4]} House</span>
                    &nbsp;·&nbsp; <span style="color:#64748b;">{grp} Group</span>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with wc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            audit.log("STUDENT_LOGOUT", fresh[0])
            for k, v in _defaults.items():
                st.session_state[k] = v
            st.rerun()

    # ── Resume voting banner (Task 3.2.3) ─────────────────────────────────────
    if st.session_state.get("has_valid_saved_votes", False) and fresh[7] == 0:
        saved_count = st.session_state.get("saved_votes_count", 0)
        warnings = st.session_state.get("saved_votes_warnings", [])

        # Format timestamp
        import pandas as pd

        if st.session_state.saved_votes_timestamp:
            saved_time = pd.Timestamp.fromtimestamp(
                st.session_state.saved_votes_timestamp
            ).strftime("%b %d, %Y at %I:%M %p")
        else:
            saved_time = "recently"

        st.markdown(
            f"""
        <div style="background:linear-gradient(135deg,rgba(245,158,11,.15),rgba(251,191,36,.08));
                    border:2px solid rgba(245,158,11,.4);border-radius:18px;
                    padding:24px;margin:16px 0;">
            <div style="display:flex;align-items:center;gap:16px;">
                <span style="font-size:2.5rem;">💾</span>
                <div style="flex:1;">
                    <div style="font-size:1.2rem;font-weight:800;color:#fbbf24;">Resume Your Voting Session</div>
                    <div style="color:#94a3b8;margin-top:6px;font-size:.9rem;">
                        You have <strong>{saved_count} vote{'s' if saved_count != 1 else ''}</strong> saved from {saved_time}.
                        {' Some selections may no longer be valid.' if warnings else ' All selections are still valid.'}
                    </div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if warnings:
            with st.expander("⚠️ View validation warnings"):
                for warning in warnings:
                    st.warning(warning)

        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("🔄 Resume Voting", use_container_width=True, type="primary"):
                # Load saved votes into temp_votes
                st.session_state.temp_votes = st.session_state.valid_saved_votes.copy()
                st.session_state.has_valid_saved_votes = False  # Hide banner
                audit.log(
                    "RESUME_VOTING", fresh[0], f"Resumed with {saved_count} saved votes"
                )
                st.success(
                    f"✅ Resumed with {saved_count} saved vote{'s' if saved_count != 1 else ''}!"
                )
                time.sleep(0.5)
                st.rerun()
        with rc2:
            if st.button("🆕 Start Fresh", use_container_width=True, type="secondary"):
                # Clear saved votes and start fresh
                clear_vote_progress()
                st.session_state.temp_votes = {}
                st.session_state.has_valid_saved_votes = False
                audit.log("START_FRESH", fresh[0], "Cleared saved votes")
                st.info("Starting fresh voting session...")
                time.sleep(0.5)
                st.rerun()

    # ── ALREADY VOTED ─────────────────────────────────────────────────────────
    if fresh[7] == 1:
        st.markdown(confetti_html(), unsafe_allow_html=True)
        st.markdown(
            """
        <div style="background:linear-gradient(135deg,rgba(16,185,129,.15),rgba(52,211,153,.08));
                    border:2px solid rgba(16,185,129,.4);border-radius:20px;
                    padding:36px;text-align:center;margin:16px 0;">
            <div style="font-size:4rem;">🎉</div>
            <div style="font-size:1.8rem;font-weight:900;color:#10b981;margin-top:8px;">You've Voted!</div>
            <div style="color:#94a3b8;margin-top:8px;font-size:1rem;">
                Your voice has been heard. Thank you for participating!
            </div>
            <div style="margin-top:16px;display:inline-block;background:rgba(16,185,129,.2);
                        border:1px solid rgba(16,185,129,.4);border-radius:12px;
                        padding:10px 24px;color:#34d399;font-weight:700;font-size:.9rem;">
                🏅 I Voted — JB Academy Elections
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Show their votes (read-only)
        my_votes = voting.get_student_votes(fresh[0])
        if my_votes:
            st.markdown("**Your selections (read-only):**", unsafe_allow_html=True)
            for comm, vi in my_votes.items():
                info = ci(comm)
                st.markdown(
                    f"""
                <div class="confirm-row">
                    <span style="font-size:1.5rem;">{info['icon']}</span>
                    <div style="flex:1;">
                        <div style="font-weight:700;color:white;">{comm}</div>
                        <div style="color:#94a3b8;font-size:.82rem;">{Utils.format_timestamp(vi['voted_at'])}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:600;color:#34d399;">{avatar(vi['candidate_name'])} {vi['candidate_name']}</div>
                        <div style="color:#64748b;font-size:.8rem;">Class {vi['candidate_class']}</div>
                    </div>
                </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", key="lo2", use_container_width=True):
            audit.log("STUDENT_LOGOUT", fresh[0])
            for k, v in _defaults.items():
                st.session_state[k] = v
            st.rerun()

        st.markdown(
            f'<div class="civic-fact" style="margin-top:24px;">💡 {fact}</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    # ── STUDENT TABS ──────────────────────────────────────────────────────────
    # Check election phase to determine if results tab should be shown
    show_results = voting.results_public()

    # Create tabs based on election phase
    if show_results:
        stab1, stab2, stab3 = st.tabs(
            ["🗳️ Cast Your Vote", "✋ Nominate Yourself", "📊 View Results"]
        )
    else:
        stab1, stab2 = st.tabs(["🗳️ Cast Your Vote", "✋ Nominate Yourself"])

    # ── SELF-NOMINATION ───────────────────────────────────────────────────────
    with stab2:
        if not voting.nominations_open():
            st.markdown(
                """
            <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);
                        border-radius:18px;padding:28px;text-align:center;">
                <div style="font-size:2.5rem;">🔒</div>
                <div style="font-size:1.1rem;font-weight:700;color:#fca5a5;margin-top:10px;">
                    Nominations are closed
                </div>
                <div style="color:#64748b;margin-top:6px;font-size:.9rem;">
                    The election is currently live. Nominations closed when voting started.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div style="background:linear-gradient(135deg,rgba(99,102,241,.12),rgba(139,92,246,.08));
                        border:1px solid rgba(99,102,241,.3);border-radius:18px;padding:24px;margin-bottom:20px;">
                <div style="font-size:1.2rem;font-weight:800;color:white;">Want to be a leader? 🌟</div>
                <div style="color:#94a3b8;margin-top:8px;line-height:1.6;">
                    Nominate yourself for a committee. Write a short manifesto — tell your classmates
                    what you will do if elected. Your teacher will review and approve your nomination
                    before it appears on the ballot.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Show existing nominations
            my_noms = db.execute(
                "SELECT committee_name,status,created_at FROM candidates WHERE LOWER(TRIM(admission_no))=?",
                (fresh[0],),
            ).fetchall()
            if my_noms:
                st.markdown("**Your nominations:**", unsafe_allow_html=True)
                for cn, cs, crt in my_noms:
                    info = ci(cn)
                    st.markdown(
                        f"""
                    <div class="nom-card nom-{cs}">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div>{info['icon']} <strong style="color:white;">{cn}</strong></div>
                            <span class="badge badge-{cs}">{cs.upper()}</span>
                        </div>
                        <div style="color:#64748b;font-size:.78rem;margin-top:4px;">{Utils.format_timestamp(crt or '')}</div>
                        {('<div style="color:#fde68a;font-size:.82rem;margin-top:6px;">⏳ Awaiting teacher approval...</div>' if cs=="pending" else "")}
                        {('<div style="color:#34d399;font-size:.82rem;margin-top:6px;">✅ Approved — you are on the ballot!</div>' if cs=="approved" else "")}
                        {('<div style="color:#f87171;font-size:.82rem;margin-top:6px;">❌ Not approved this time. You can try another committee.</div>' if cs=="rejected" else "")}
                    </div>""",
                        unsafe_allow_html=True,
                    )

                    # Withdrawal button (only in SETUP phase and for approved/pending nominations)
                    if election.is_setup() and cs in ["approved", "pending"]:
                        if st.button(
                            f"🚫 Withdraw from {cn}",
                            key=f"withdraw_{cn}",
                            type="secondary",
                        ):
                            ok, msg = Candidate(db).withdraw(fresh[0], cn)
                            if ok:
                                st.success(msg)
                                audit.log("WITHDRAW_NOM", fresh[0], f"{cn}")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(msg)

                st.markdown("<br>", unsafe_allow_html=True)

            # Nomination form
            nom_type_s = st.selectbox(
                "I want to stand for a", ["School Committee", "House Committee"]
            )
            is_school = nom_type_s == "School Committee"

            if is_school:
                sc_l = voting.SCHOOL_COMMITTEES
                nom_comm_s = st.selectbox("Which committee?", sc_l) if sc_l else None
                nom_cls_s = fresh[2]
                nom_hs_s = nom_grp_s = None
                if nom_comm_s:
                    info = ci(nom_comm_s)
                    st.markdown(
                        f'<div class="info-box">{info["icon"]} <strong>{nom_comm_s}</strong> — {info["desc"]}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                hc_l = voting.HOUSE_COMMITTEES
                nom_comm_s = st.selectbox("Which committee?", hc_l) if hc_l else None
                nom_hs_s = fresh[4]
                nom_grp_s = grp
                nom_cls_s = None
                st.markdown(
                    f'<div class="info-box">{h["emoji"]} You will represent <strong>{fresh[4]} House</strong> · <strong>{grp}</strong> group.</div>',
                    unsafe_allow_html=True,
                )

            # Show existing approved candidates for selected committee
            if nom_comm_s:
                existing_candidates = db.execute(
                    """
                    SELECT c.admission_no, s.name, s.class, s.house, c.manifesto
                    FROM candidates c
                    LEFT JOIN students s ON LOWER(TRIM(c.admission_no)) = LOWER(TRIM(s.admission_no))
                    WHERE c.committee_name = ? AND c.status = "approved"
                    ORDER BY s.name
                """,
                    (nom_comm_s,),
                ).fetchall()

                if existing_candidates:
                    cand_count = len(existing_candidates)
                    with st.expander(
                        f'👥 View Candidates ({cand_count} candidate{"s" if cand_count != 1 else ""})',
                        expanded=False,
                    ):
                        st.markdown(
                            f'<div style="color:#94a3b8;font-size:.88rem;margin-bottom:16px;">These students have already been approved for <strong>{nom_comm_s}</strong>:</div>',
                            unsafe_allow_html=True,
                        )
                        for adm, name, cls, house, manifesto in existing_candidates:
                            h_meta = hm(house or "")
                            manifesto_html = (
                                f'<div class="cand-manifesto">"{manifesto}"</div>'
                                if manifesto
                                else '<div class="cand-manifesto" style="opacity:0.6;">No manifesto provided</div>'
                            )
                            st.markdown(
                                f"""
                            <div class="cand-card" style="cursor:default;margin-bottom:12px;">
                                <span class="cand-avatar">{avatar(name or adm)}</span>
                                <div class="cand-name">{name or adm}</div>
                                <div class="cand-meta">Class {cls or '?'}</div>
                                <div class="cand-house" style="color:{h_meta['color']};">{h_meta['emoji']} {house or '?'} House</div>
                                {manifesto_html}
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

            nom_man_s = st.text_area(
                "✍️ Your Election Manifesto",
                max_chars=200,
                placeholder='Example: "I will organise weekly sports sessions and make sure every student gets to play. Vote for me for a healthier, happier school!"',
                help="This is shown to every voter. Make it count!",
            )
            st.caption(
                f"{len(nom_man_s)}/200 characters · {200 - len(nom_man_s)} remaining"
            )

            if st.button(
                "✋ Submit My Nomination", type="primary", use_container_width=True
            ):
                if not nom_comm_s:
                    st.markdown(
                        '<div class="error-box">❌ No committees available yet.</div>',
                        unsafe_allow_html=True,
                    )
                elif len(nom_man_s.strip()) < 20:
                    st.markdown(
                        '<div class="warn-box">✍️ Please write at least 20 characters.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    ok, msg = Candidate(db).add(
                        fresh[0],
                        "School" if is_school else "House",
                        nom_comm_s,
                        nom_cls_s,
                        nom_hs_s,
                        nom_grp_s,
                        nom_man_s.strip(),
                        "pending",
                        fresh[0],
                    )
                    if ok:
                        audit.log(
                            "SELF_NOMINATION", fresh[0], f"{fresh[1]}→{nom_comm_s}"
                        )
                        st.markdown(
                            """
                        <div class="success-box">
                            🎉 <strong>Nomination submitted!</strong><br>
                            Your teacher will review it soon. Good luck! 🌟
                        </div>""",
                            unsafe_allow_html=True,
                        )
                        st.balloons()
                        st.rerun()
                    else:
                        st.markdown(
                            f'<div class="error-box">❌ {msg}</div>',
                            unsafe_allow_html=True,
                        )

    # ── VOTING TAB ────────────────────────────────────────────────────────────
    with stab1:
        if not election.is_live():
            st.markdown(
                f"""
            <div style="background:rgba(100,116,139,.1);border:1px solid rgba(100,116,139,.3);
                        border-radius:18px;padding:40px;text-align:center;margin:20px 0;">
                <div style="font-size:4rem;">⏸️</div>
                <div style="font-size:1.3rem;font-weight:700;color:#94a3b8;margin-top:12px;">Election hasn't started yet</div>
                <div style="color:#475569;margin-top:8px;">Your teacher will start the election soon. Stay tuned!</div>
                <div style="margin-top:20px;color:#334155;font-size:.85rem;">
                    While you wait — you can nominate yourself in the <strong>Nominate Yourself</strong> tab 👆
                </div>
            </div>
            <div class="civic-fact">💡 {fact}</div>
            """,
                unsafe_allow_html=True,
            )
            st.stop()

        # ── Step indicator ──
        step = 1 if st.session_state.review_votes else 0
        st.markdown(
            f"""
        <div class="steps">
            <div class="step {'done' if step>0 else 'active'}">
                {'✓' if step>0 else '1'} &nbsp; Select Candidates
            </div>
            <div class="step-line {'done' if step>0 else ''}"></div>
            <div class="step {'active' if step==1 else ''}">
                2 &nbsp; Review & Confirm
            </div>
            <div class="step-line"></div>
            <div class="step">3 &nbsp; Done!</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── STEP 1: SELECT ────────────────────────────────────────────────────
        if not st.session_state.review_votes:
            vote_choices = st.session_state.temp_votes.copy()

            st.markdown(
                """
            <div class="info-box">
                🗳️ <strong>How to vote:</strong> Select one candidate per committee.
                Read their manifesto before choosing. You can skip a committee by selecting "Abstain".
                When done, click <strong>Review My Votes</strong>.
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Pre-fetch all candidates in two queries (no N+1)
            school_cands_raw = db.execute(
                """
                SELECT c.committee_name, c.admission_no, c.manifesto,
                       s.name, s.class, s.section, s.house
                FROM candidates c
                LEFT JOIN students s ON LOWER(TRIM(c.admission_no))=LOWER(TRIM(s.admission_no))
                WHERE c.committee_type="School" AND c.scope_class=? AND c.status="approved"
                ORDER BY c.committee_name, s.name
            """,
                (fresh[2],),
            ).fetchall()

            house_cands_raw = db.execute(
                """
                SELECT c.committee_name, c.admission_no, c.manifesto,
                       s.name, s.class, s.section, s.house
                FROM candidates c
                LEFT JOIN students s ON LOWER(TRIM(c.admission_no))=LOWER(TRIM(s.admission_no))
                WHERE c.committee_type="House" AND c.scope_house=?
                  AND c.section_group=? AND c.status="approved"
                ORDER BY c.committee_name, s.name
            """,
                (fresh[4], grp),
            ).fetchall()

            # Group by committee
            from collections import defaultdict

            school_by_comm = defaultdict(list)
            for row in school_cands_raw:
                school_by_comm[row[0]].append(row)
            house_by_comm = defaultdict(list)
            for row in house_cands_raw:
                house_by_comm[row[0]].append(row)

            def render_committee(comm_key, cands_rows, label_override=None):
                display_name = label_override or comm_key.replace("House-", "")
                info = ci(display_name)
                st.markdown(
                    f"""
                <div class="comm-header">
                    <span class="comm-icon">{info['icon']}</span>
                    <div>
                        <div class="comm-title">{display_name}</div>
                        <div class="comm-desc">{info['desc']}</div>
                    </div>
                </div>""",
                    unsafe_allow_html=True,
                )

                options = [ABSTAIN] + [r[1] for r in cands_rows]
                data_map = {
                    r[1]: {
                        "adm": r[1],
                        "name": r[3] or r[1],
                        "class": r[4] or "?",
                        "sec": r[5] or "?",
                        "house": r[6] or "?",
                        "manifesto": r[2] or "",
                    }
                    for r in cands_rows
                }

                current_sel = vote_choices.get(comm_key, ABSTAIN)
                if current_sel not in options:
                    current_sel = ABSTAIN

                cols = st.columns(min(len(options), 4))
                for idx, opt_key in enumerate(options):
                    col = cols[idx % min(len(options), 4)]
                    with col:
                        is_sel = current_sel == opt_key
                        if opt_key == ABSTAIN:
                            if st.button(
                                f"{'✓ ' if is_sel else ''}⬜ Abstain",
                                key=f"btn_{comm_key}_abstain",
                                use_container_width=True,
                                type="secondary",
                            ):
                                vote_choices[comm_key] = ABSTAIN
                                st.session_state.temp_votes = vote_choices
                                # Auto-save vote progress
                                save_vote_progress(fresh[0], vote_choices)
                                st.rerun()
                        else:
                            d = data_map[opt_key]
                            ch = hm(d["house"])
                            check = (
                                '<div class="cand-selected-check">✓</div>'
                                if is_sel
                                else ""
                            )
                            manifesto_html = (
                                f'<div class="cand-manifesto">"{d["manifesto"]}"</div>'
                                if d["manifesto"]
                                else ""
                            )
                            st.markdown(
                                f"""
                            <div class="cand-card {'selected' if is_sel else ''}" style="position:relative;">
                                {check}
                                <span class="cand-avatar">{avatar(d['name'])}</span>
                                <div class="cand-name">{d['name']}</div>
                                <div class="cand-meta">Class {d['class']} · Section {d['sec']}</div>
                                <div class="cand-house" style="color:{ch['color']};">{ch['emoji']} {d['house']} House</div>
                                {manifesto_html}
                            </div>""",
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                f"{'✓ Selected' if is_sel else '🗳️ Vote for ' + d['name'].split()[0]}",
                                key=f"btn_{comm_key}_{opt_key}",
                                use_container_width=True,
                                type="primary" if is_sel else "secondary",
                            ):
                                vote_choices[comm_key] = opt_key
                                st.session_state.temp_votes = vote_choices
                                # Auto-save vote progress
                                save_vote_progress(fresh[0], vote_choices)
                                st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                return vote_choices

            school_shown = False
            for comm in voting.SCHOOL_COMMITTEES:
                if school_by_comm.get(comm):
                    if not school_shown:
                        st.markdown("## 🏫 School Committees", unsafe_allow_html=True)
                        school_shown = True
                    vote_choices = render_committee(comm, school_by_comm[comm])

            house_shown = False
            for comm in voting.HOUSE_COMMITTEES:
                if house_by_comm.get(comm):
                    if not house_shown:
                        st.markdown(
                            f"## {h['emoji']} {fresh[4]} House Committees",
                            unsafe_allow_html=True,
                        )
                        house_shown = True
                    vote_choices = render_committee(
                        f"House-{comm}",
                        house_by_comm[comm],
                        label_override=f"{comm} ({fresh[4]} House)",
                    )

            if not school_shown and not house_shown:
                st.markdown(
                    """
                <div style="text-align:center;padding:40px;color:#475569;">
                    <div style="font-size:3rem;">📋</div>
                    <div style="font-size:1.1rem;margin-top:12px;">No candidates nominated yet.</div>
                    <div style="font-size:.85rem;margin-top:6px;">Check back after your teacher sets up the nominations.</div>
                </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.divider()
                c1, c2 = st.columns([3, 1])
                with c1:
                    if st.button(
                        "👁️  Review My Votes →",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state.temp_votes = vote_choices
                        st.session_state.review_votes = True
                        st.rerun()
                with c2:
                    if st.button("🚪 Exit Without Voting", use_container_width=True):
                        audit.log("STUDENT_EXIT_NO_VOTE", fresh[0])
                        for k, v in _defaults.items():
                            st.session_state[k] = v
                        st.rerun()

        # ── STEP 2: REVIEW & CONFIRM ──────────────────────────────────────────
        else:
            vote_choices = st.session_state.temp_votes

            st.markdown(
                """
            <div class="warn-box">
                ⚠️ <strong>Final Review</strong> — Check carefully before submitting.
                Once confirmed, your vote is <strong>permanent and cannot be changed</strong>.
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("### Your Selections:", unsafe_allow_html=True)
            real_votes = 0
            name_map = {s[0]: s for s in Student(db).get_all()}

            for comm, val in vote_choices.items():
                display_comm = comm.replace("House-", "")
                info = ci(display_comm)
                if val == ABSTAIN:
                    st.markdown(
                        f"""
                    <div class="confirm-abstain">
                        {info['icon']} <strong>{display_comm}</strong>
                        &nbsp;→&nbsp; <em>Abstained (skipped)</em>
                    </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    cand = name_map.get(val)
                    if cand:
                        real_votes += 1
                        ch = hm(cand[4])
                        st.markdown(
                            f"""
                        <div class="confirm-row">
                            <span style="font-size:1.5rem;">{info['icon']}</span>
                            <div style="flex:1;">
                                <div style="font-weight:700;color:white;">{display_comm}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:700;color:#34d399;">{avatar(cand[1])} {cand[1]}</div>
                                <div style="color:#64748b;font-size:.8rem;">
                                    Class {cand[2]} · <span style="color:{ch['color']}">{cand[4]} House</span>
                                </div>
                            </div>
                        </div>""",
                            unsafe_allow_html=True,
                        )

            if real_votes == 0:
                st.markdown(
                    '<div class="warn-box">⚠️ You have abstained from all committees. Are you sure?</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "✅  CONFIRM & SUBMIT MY VOTE",
                    use_container_width=True,
                    type="primary",
                ):
                    success, msg = voting.submit_votes(fresh[0], vote_choices)
                    if success:
                        audit.log("VOTE_SUBMITTED", fresh[0], msg)
                        # Clear saved vote progress after successful submission
                        clear_vote_progress()
                        st.markdown(confetti_html(), unsafe_allow_html=True)
                        st.markdown(
                            f"""
                        <div style="background:linear-gradient(135deg,rgba(16,185,129,.2),rgba(52,211,153,.1));
                                    border:2px solid rgba(16,185,129,.5);border-radius:20px;
                                    padding:40px;text-align:center;margin:16px 0;">
                            <div style="font-size:5rem;">🎉</div>
                            <div style="font-size:2rem;font-weight:900;color:#10b981;margin-top:12px;">Vote Submitted!</div>
                            <div style="color:#94a3b8;margin-top:10px;font-size:1.05rem;">
                                Your voice has been heard, {fresh[1].split()[0]}!<br>
                                Thank you for being a responsible citizen of JB Academy.
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                        st.balloons()
                        time.sleep(2)
                        for k, v in _defaults.items():
                            st.session_state[k] = v
                        st.rerun()
                    else:
                        st.markdown(
                            f'<div class="error-box">❌ {msg}</div>',
                            unsafe_allow_html=True,
                        )
            with c2:
                if st.button("🔙 Go Back & Edit", use_container_width=True):
                    st.session_state.review_votes = False
                    st.rerun()

    # ── VIEW RESULTS TAB ──────────────────────────────────────────────────────
    if show_results:
        with stab3:
            st.markdown(
                """
            <div style="background:linear-gradient(135deg,rgba(16,185,129,.12),rgba(52,211,153,.08));
                        border:1px solid rgba(16,185,129,.3);border-radius:18px;padding:24px;margin-bottom:20px;">
                <div style="font-size:1.2rem;font-weight:800;color:white;">📊 Election Results</div>
                <div style="color:#94a3b8;margin-top:8px;line-height:1.6;">
                    The election has concluded. Here are the final results for all committees.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Fetch student's votes to highlight their choices
            my_votes = voting.get_student_votes(fresh[0])

            # Fetch and display results using the existing render_results function
            results = voting.get_results()
            render_results(results, show_tie_break=False, student_votes=my_votes)

    st.markdown(
        f'<div class="civic-fact" style="margin-top:32px;">💡 {fact}</div>',
        unsafe_allow_html=True,
    )
