"""
Shared UI helpers — zero Streamlit state, pure HTML/string functions.
No DB calls here.
"""

import random

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
_DEFAULT_HOUSE = {
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
_DEFAULT_CI = {"icon": "📋", "desc": "Serves the school community."}

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

PHASE_LABELS = {
    "setup": ("⚙️ Setup", "#6366f1", "Nominations open · Voting not started"),
    "live": ("🔴 LIVE", "#ef4444", "Voting is open"),
    "closed": ("✅ Closed", "#10b981", "Voting ended · Results public"),
}


def hm(house: str) -> dict:
    if not house:
        return _DEFAULT_HOUSE
    h = str(house).strip().title()
    # Direct mappings for common variations
    mapping = {"Ajanta": "Janata", "Sanchi": "Saachi"}
    normalized = mapping.get(h, h)
    return HOUSE_META.get(normalized, _DEFAULT_HOUSE)


def ci(committee: str) -> dict:
    return COMMITTEE_INFO.get(committee, _DEFAULT_CI)


def avatar(name: str) -> str:
    random.seed(str(name))
    return random.choice(AVATARS)


def phase_badge(phase: str) -> str:
    label, color, desc = PHASE_LABELS.get(phase, ("❓ Unknown", "#64748b", ""))
    return (
        f'<span style="display:inline-flex;align-items:center;gap:8px;'
        f"background:{color}22;border:1px solid {color}88;color:{color};"
        f'padding:6px 18px;border-radius:99px;font-weight:700;font-size:.9rem;">'
        f"{label}</span>"
        f'<span style="color:#64748b;font-size:.82rem;margin-left:10px;">{desc}</span>'
    )


def box(kind: str, text: str) -> str:
    """kind: info | warn | success | error"""
    cfg = {
        "info": ("#6366f1", "#c7d2fe"),
        "warn": ("#f59e0b", "#fde68a"),
        "success": ("#10b981", "#6ee7b7"),
        "error": ("#ef4444", "#fca5a5"),
    }
    border, fg = cfg.get(kind, cfg["info"])
    return (
        f'<div style="background:{border}14;border:1px solid {border}44;'
        f"border-radius:12px;padding:14px 18px;margin:10px 0;"
        f'font-size:.88rem;color:{fg};">{text}</div>'
    )


def result_card_html(
    rank: int,
    cand: dict,
    max_winners: int,
    total_votes: int,
    is_student_choice: bool = False,
) -> str:
    ph = hm(cand["house"])
    is_win = cand.get("is_winner", False)
    is_tied = cand.get("is_tied", False)
    rank_ico = RANK_ICONS[rank - 1] if rank <= len(RANK_ICONS) else str(rank)
    bar_cls = "bar-tied" if is_tied else ("bar-winner" if is_win else "bar-normal")
    card_cls = "tied" if is_tied else ("winner" if is_win else "")
    tie_tag = (
        ' <span style="color:#f59e0b;font-size:.75rem;">⚖️ TIE</span>'
        if is_tied
        else ""
    )
    win_tag = (
        ' <span style="color:#10b981;font-size:.75rem;">🏆</span>'
        if (is_win and not is_tied)
        else ""
    )
    choice_tag = (
        ' <span style="color:#6366f1;font-size:.75rem;">👤 Your Vote</span>'
        if is_student_choice
        else ""
    )

    # Add visual indicator for student's choice
    card_border = ""
    if is_student_choice:
        card_cls += " student-choice"
        card_border = "border-left:4px solid #6366f1;"

    return f"""
<div class="result-card {card_cls}" style="{card_border}">
    <span class="result-rank">{rank_ico}</span>
    <span style="font-size:1.4rem;">{avatar(cand['name'])}</span>
    <div class="result-info">
        <div class="result-name">{cand['name']}{win_tag}{tie_tag}{choice_tag}</div>
        <div class="result-sub">Class {cand['class']} &nbsp;·&nbsp;
            <span style="color:{ph['color']}">{cand['house']} House</span>
        </div>
    </div>
    <div class="bar-wrap">
        <div class="bar-fill {bar_cls}" style="width:{cand['pct']}%;"></div>
    </div>
    <div class="result-right">
        <div class="result-votes">{int(cand['votes'])}</div>
        <div class="result-pct">{cand['pct']}%</div>
    </div>
</div>"""


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
            f'<div style="position:fixed;width:{size}px;height:{size}px;top:-10px;'
            f"background:{color};left:{left}%;border-radius:2px;z-index:9999;"
            f"pointer-events:none;animation:confettiFall {dur:.1f}s {delay:.1f}s linear forwards;"
            f'transform:rotate({rot}deg);"></div>'
        )
    return (
        "<style>@keyframes confettiFall{0%{transform:translateY(0) rotate(0deg);opacity:1}"
        "100%{transform:translateY(110vh) rotate(720deg);opacity:0}}</style>"
        + "".join(pieces)
    )


def session_warning_banner(remaining_seconds: int) -> str:
    """
    Display session expiration warning with countdown timer.
    Shows when less than 2 minutes remain in the session.
    """
    minutes = int(remaining_seconds // 60)
    seconds = int(remaining_seconds % 60)

    # Color coding based on urgency
    if remaining_seconds > 60:
        color = "#f59e0b"  # Orange for 1-2 minutes
        bg_color = "rgba(245,158,11,.15)"
        border_color = "rgba(245,158,11,.4)"
    else:
        color = "#ef4444"  # Red for < 1 minute
        bg_color = "rgba(239,68,68,.15)"
        border_color = "rgba(239,68,68,.5)"

    return f"""
<div style="position:fixed;top:80px;left:50%;transform:translateX(-50%);
            z-index:10000;width:90%;max-width:600px;
            background:{bg_color};backdrop-filter:blur(20px);
            border:2px solid {border_color};border-radius:16px;
            padding:20px 24px;box-shadow:0 8px 32px rgba(0,0,0,.3);
            animation:slideDown 0.3s ease-out;">
    <div style="display:flex;align-items:center;gap:16px;">
        <span style="font-size:2rem;">⏱️</span>
        <div style="flex:1;">
            <div style="font-size:1.1rem;font-weight:800;color:{color};">
                Session Expiring Soon
            </div>
            <div style="color:#cbd5e1;margin-top:4px;font-size:.9rem;">
                Your session will expire in <strong style="color:white;">{minutes:02d}:{seconds:02d}</strong>
            </div>
            <div style="color:#94a3b8;margin-top:2px;font-size:.8rem;">
                Your progress has been auto-saved
            </div>
        </div>
    </div>
</div>
<style>
@keyframes slideDown {{
    from {{
        opacity: 0;
        transform: translateX(-50%) translateY(-20px);
    }}
    to {{
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }}
}}
</style>
"""
