"""
Results rendering — used by both admin (live) and student (post-close).
Receives pre-fetched results dict; zero extra DB calls.
"""

import hashlib
from typing import Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pages.components import RANK_ICONS, avatar, box, ci, hm, result_card_html


def _render_vote_distribution_chart(cands: list, comm_name: str, total_cv: int, widget_prefix: str = ""):
    """Sub-task 1.3.1: Create bar chart component for vote distribution"""
    if not cands or total_cv == 0:
        return

    # Prepare data for bar chart
    df = pd.DataFrame(
        [
            {
                "Candidate": c["name"],
                "Votes": int(c["votes"]),
                "Percentage": c["pct"],
                "House": c["house"],
            }
            for c in cands
        ]
    )

    # Create bar chart with house colors
    fig = go.Figure()

    for _, row in df.iterrows():
        house_color = hm(row["House"])["color"]
        fig.add_trace(
            go.Bar(
                x=[row["Votes"]],
                y=[row["Candidate"]],
                orientation="h",
                name=row["Candidate"],
                marker=dict(
                    color=house_color, line=dict(color="rgba(255,255,255,0.2)", width=1)
                ),
                text=f"{row['Votes']} ({row['Percentage']}%)",
                textposition="auto",
                hovertemplate=f"<b>{row['Candidate']}</b><br>"
                + f"Votes: {row['Votes']}<br>"
                + f"Percentage: {row['Percentage']}%<br>"
                + f"House: {row['House']}<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Vote Distribution - {comm_name}",
            font=dict(size=16, color="#e2e8f0", family="Inter"),
        ),
        xaxis=dict(title="Votes", gridcolor="rgba(255,255,255,0.1)", color="#94a3b8"),
        yaxis=dict(title="", color="#94a3b8"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(255,255,255,0.04)",
        font=dict(color="#e2e8f0", family="Inter"),
        height=max(300, len(cands) * 50),
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="closest",
    )

    # Use hash with all relevant data to ensure absolute uniqueness
    # Include widget_prefix, committee name, and all candidate admission numbers
    cand_adms = "_".join(sorted([str(c.get("adm", c["name"])) for c in cands]))
    unique_suffix = hashlib.md5(f"{widget_prefix}_{comm_name}_bar_{cand_adms}_{total_cv}".encode()).hexdigest()[:12]
    st.plotly_chart(fig, width='stretch', key=f"bar_{unique_suffix}")


def _render_house_participation_chart(cands: list, comm_name: str, widget_prefix: str = ""):
    """Sub-task 1.3.2: Add pie chart for participation by house"""
    if not cands:
        return

    # Aggregate votes by house
    house_votes = {}
    for c in cands:
        house = c["house"]
        house_votes[house] = house_votes.get(house, 0) + int(c["votes"])

    if not house_votes or sum(house_votes.values()) == 0:
        return

    # Prepare data
    df = pd.DataFrame(
        [{"House": house, "Votes": votes} for house, votes in house_votes.items()]
    )

    # Get house colors
    colors = [hm(house)["color"] for house in df["House"]]

    # Create pie chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df["House"],
                values=df["Votes"],
                marker=dict(
                    colors=colors, line=dict(color="rgba(255,255,255,0.2)", width=2)
                ),
                textinfo="label+percent",
                textfont=dict(size=14, color="white", family="Inter"),
                hovertemplate="<b>%{label}</b><br>"
                + "Votes: %{value}<br>"
                + "Percentage: %{percent}<extra></extra>",
                hole=0.4,
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text=f"House Participation - {comm_name}",
            font=dict(size=16, color="#e2e8f0", family="Inter"),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(255,255,255,0.04)",
        font=dict(color="#e2e8f0", family="Inter"),
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(color="#94a3b8"),
        ),
    )

    # Use hash with all relevant data to ensure absolute uniqueness
    # Include widget_prefix, committee name, and all candidate admission numbers
    cand_adms = "_".join(sorted([str(c.get("adm", c["name"])) for c in cands]))
    total_votes = sum(house_votes.values())
    unique_suffix = hashlib.md5(f"{widget_prefix}_{comm_name}_pie_{cand_adms}_{total_votes}".encode()).hexdigest()[:12]
    st.plotly_chart(fig, width='stretch', key=f"pie_{unique_suffix}")


def _render_animated_podium(cands: list, comm_name: str):
    """Display winner podium — single st.html() per card, all styles on one line."""
    if not cands or len(cands) < 2:
        return

    top3 = cands[:3]
    order = [1, 0, 2] if len(top3) >= 3 else [0, 1]

    cards = []
    for ri in order:
        if ri >= len(top3):
            cards.append('<div style="flex:1;"></div>')
            continue
        c_ = top3[ri]
        ht = 100 if ri == 0 else (75 if ri == 1 else 55)
        grad = ("linear-gradient(180deg,#f59e0b,#d97706)" if ri == 0
                else ("linear-gradient(180deg,#94a3b8,#64748b)" if ri == 1
                      else "linear-gradient(180deg,#b45309,#92400e)"))
        glow = "box-shadow:0 0 20px rgba(245,158,11,0.5);" if ri == 0 else ""
        tie = "⚖️" if c_.get("is_tied") else ""
        av = avatar(c_["name"])
        name = c_["name"]
        votes = int(c_["votes"])
        icon = RANK_ICONS[ri]

        cards.append(
            f'<div style="flex:1;text-align:center;padding:0 8px;">'
            f'<div style="font-size:.85rem;font-weight:600;color:white;margin-bottom:4px;font-family:Inter,sans-serif;">{av} {name}</div>'
            f'<div style="font-size:.75rem;color:#94a3b8;margin-bottom:6px;font-family:Inter,sans-serif;">{votes} votes {tie}</div>'
            f'<div style="background:{grad};height:{ht}px;border-radius:12px 12px 0 0;display:flex;align-items:center;justify-content:center;font-size:1.8rem;{glow}">{icon}</div>'
            f'</div>'
        )

    st.html(
        '<div style="display:flex;gap:8px;align-items:flex-end;margin:8px 0;">'
        + "".join(cards)
        + "</div>"
    )


# ── Grouping helpers ──────────────────────────────────────────────────────────

def _get_scope_class(comm_name: str, candidates: list) -> str:
    """
    Determine the class scope for a School committee.
    Tries to extract a class number from the committee name first,
    then falls back to the majority class of its candidates.
    Returns e.g. "9", "10", "11" or "" if unknown.
    """
    import re
    # Look for patterns like "Class 9", "Cl 10", "class-11", "9th", "10th", etc.
    m = re.search(r'\b(?:class|cl)[\s\-]?(\d{1,2})\b', comm_name, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:class|grade)?\b', comm_name, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 12:
            return str(num)
    # Fallback: majority class from candidates
    if candidates:
        class_counts: Dict[str, int] = {}
        for c in candidates:
            cls = str(c.get("class", "")).strip()
            if cls and cls != "?":
                class_counts[cls] = class_counts.get(cls, 0) + 1
        if class_counts:
            return max(class_counts, key=class_counts.get)
    return ""


def _get_scope_house(comm_name: str, candidates: list) -> str:
    """
    Determine the house scope for a House committee.
    Tries to detect the house name from candidates (all from same house usually).
    Returns the house name or "" if mixed/unknown.
    """
    if not candidates:
        return ""
    house_counts: Dict[str, int] = {}
    for c in candidates:
        h = str(c.get("house", "")).strip()
        if h and h != "?":
            house_counts[h] = house_counts.get(h, 0) + 1
    if not house_counts:
        return ""
    dominant = max(house_counts, key=house_counts.get)
    # Only return if clear majority (>50%)
    total = sum(house_counts.values())
    if house_counts[dominant] / total >= 0.5:
        return dominant
    return ""


def _group_school_by_class(committees: Dict) -> Dict[str, Dict]:
    """Return {class_key: {comm_name: data}} sorted by class then committee."""
    grouped: Dict[str, Dict] = {}
    for comm_name, data in committees.items():
        scope = _get_scope_class(comm_name, data["candidates"])
        key = scope if scope else "Other / School-Wide"
        grouped.setdefault(key, {})[comm_name] = data
    # Sort numerically by class
    def _sort_key(k):
        try:
            return (0, int(k))
        except ValueError:
            return (1, k)
    return dict(sorted(grouped.items(), key=lambda x: _sort_key(x[0])))


def _group_house_by_house(committees: Dict) -> Dict[str, Dict]:
    """Return {house_key: {comm_name: data}} sorted by house then committee."""
    grouped: Dict[str, Dict] = {}
    for comm_name, data in committees.items():
        scope = _get_scope_house(comm_name, data["candidates"])
        key = scope if scope else "Other / General"
        grouped.setdefault(key, {})[comm_name] = data
    return dict(sorted(grouped.items()))


# ── Single committee renderer ─────────────────────────────────────────────────

def _render_committee(
    comm_name: str,
    data: dict,
    student_votes: Dict,
    show_tie_break: bool,
    on_tie_break,
    widget_prefix: str = "",
):
    """Render one committee's results block (podium + charts + card list)."""
    cands = data["candidates"]
    total_cv = data["total_votes"]
    max_w = data.get("max_winners", 1)
    info = ci(comm_name)
    pos_label = f"{max_w} position{'s' if max_w > 1 else ''}"

    # Student voted indicator
    student_voted_here = student_votes and comm_name in student_votes
    voted_indicator = ""
    if student_voted_here:
        voted_indicator = '<span style="margin-left:10px;background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.4);color:#34d399;padding:4px 12px;border-radius:99px;font-size:.75rem;font-weight:700;">✓ You Voted</span>'

    st.html(
        f"""
<div style="display:flex;align-items:center;gap:14px;
        background:{'rgba(16,185,129,.08)' if student_voted_here else 'rgba(255,255,255,.04)'};
        border:1px solid {'rgba(16,185,129,.25)' if student_voted_here else 'rgba(255,255,255,.08)'};
        border-radius:14px;padding:16px 20px;margin:16px 0 12px;font-family:'Inter',sans-serif;">
    <span style="font-size:2rem;">{info['icon']}</span>
    <div style="flex:1;">
        <div style="font-size:1.15rem;font-weight:700;color:white;">{comm_name}{voted_indicator}</div>
        <div style="font-size:.82rem;color:#64748b;">
            {info['desc']} &nbsp;·&nbsp; {pos_label} &nbsp;·&nbsp; {total_cv} vote(s)
        </div>
    </div>
</div>""")

    if not cands:
        return

    # Tie banner + tie-break UI
    tied_cands = [c for c in cands if c.get("is_tied")]
    if tied_cands:
        st.html(
            box(
                "warn",
                f"⚖️ <strong>TIE</strong> — {len(tied_cands)} candidates share "
                f"the top position in <strong>{comm_name}</strong>.",
            )
        )
        if show_tie_break and on_tie_break:
            # Use hash with all relevant data to ensure absolute uniqueness
            # Include widget_prefix, committee name, and tied candidate admission numbers
            tied_adms = "_".join(sorted([str(c.get("adm", c["name"])) for c in tied_cands]))
            unique_suffix = hashlib.md5(f"{widget_prefix}_{comm_name}_tb_{tied_adms}".encode()).hexdigest()[:12]
            
            with st.expander(f"🔨 Break tie for {comm_name}"):
                options = {c["name"]: c["adm"] for c in tied_cands}
                chosen_name = st.selectbox(
                    "Select winner",
                    list(options.keys()),
                    key=f"tb_sel_{unique_suffix}",
                )
                reason = st.text_input(
                    "Reason (required)",
                    key=f"tb_reason_{unique_suffix}",
                    placeholder="e.g. Coin toss, teacher decision...",
                )
                if st.button(
                    "✅ Confirm Tie-Break",
                    key=f"tb_btn_{unique_suffix}",
                    type="primary",
                ):
                    if not reason.strip():
                        st.error("Reason is required.")
                    else:
                        on_tie_break(
                            comm_name, options[chosen_name], reason.strip()
                        )
                        st.rerun()

    # Animated podium
    if total_cv > 0 and len(cands) >= 2:
        _render_animated_podium(cands, comm_name)
        st.html("<br>")

    # Bar chart for vote distribution
    if total_cv > 0:
        with st.expander("📊 Vote Distribution Chart", expanded=False):
            _render_vote_distribution_chart(cands, comm_name, total_cv, widget_prefix)

    # Pie chart for house participation
    if total_cv > 0 and len(set(c["house"] for c in cands)) > 1:
        with st.expander("🏠 House Participation Chart", expanded=False):
            _render_house_participation_chart(cands, comm_name, widget_prefix)

    # Full ranked list
    student_voted_for = (
        student_votes.get(comm_name, {}).get("candidate_name", "")
        if student_votes
        else ""
    )
    for i, c_ in enumerate(cands):
        is_student_choice = (
            student_voted_for and c_["name"] == student_voted_for
        )
        st.html(result_card_html(i + 1, c_, max_w, total_cv, is_student_choice))
    st.html("<br>")


# ── Section header helpers ────────────────────────────────────────────────────

def _section_header_school_class(class_key: str):
    """Render a styled class-group header for School committees."""
    label = f"Class {class_key}" if class_key not in ("Other / School-Wide",) else class_key
    st.html(
        f"""
<div style="display:flex;align-items:center;gap:12px;
            background:linear-gradient(90deg,rgba(99,102,241,.18),rgba(139,92,246,.10),transparent);
            border-left:4px solid #6366f1;border-radius:0 12px 12px 0;
            padding:14px 20px;margin:28px 0 8px;font-family:'Inter',sans-serif;">
    <span style="font-size:1.5rem;">🎓</span>
    <div>
        <div style="font-size:1.1rem;font-weight:800;color:#a5b4fc;letter-spacing:-.3px;">{label}</div>
        <div style="font-size:.78rem;color:#64748b;margin-top:2px;">School Committee Results</div>
    </div>
</div>""")


def _section_header_house(house_key: str):
    """Render a styled house-group header for House committees."""
    from pages.components import hm as _hm
    meta = _hm(house_key)
    color = meta.get("color", "#6366f1")
    icon = meta.get("icon", "🏠")
    emoji = meta.get("emoji", "🏠")
    label = f"{house_key} House" if house_key not in ("Other / General",) else house_key
    st.html(
        f"""
<div style="display:flex;align-items:center;gap:12px;
            background:linear-gradient(90deg,{color}22,{color}11,transparent);
            border-left:4px solid {color};border-radius:0 12px 12px 0;
            padding:14px 20px;margin:28px 0 8px;font-family:'Inter',sans-serif;">
    <span style="font-size:1.5rem;">{icon}</span>
    <div>
        <div style="font-size:1.1rem;font-weight:800;color:{color};letter-spacing:-.3px;">{label}</div>
        <div style="font-size:.78rem;color:#64748b;margin-top:2px;">House Committee Results</div>
    </div>
</div>""")


# ── Main render function ──────────────────────────────────────────────────────

def render_results(
    results: Dict,
    show_tie_break: bool = False,
    on_tie_break=None,
    student_votes: Dict = None,
    widget_prefix: str = "",
):
    """
    results: output of VotingEngine.get_results()
    show_tie_break: True only for admin in CLOSED phase
    on_tie_break: callable(committee_name, winner_adm, reason) — admin callback
    student_votes: dict of {committee_name: {'candidate_name': str, ...}} for highlighting
    widget_prefix: unique prefix for Streamlit widget keys (needed if called multiple times)
    """
    if not results:
        st.html(box("info", "📋 No results yet — nominations and votes needed first."))
        return

    # ── View mode selectors ───────────────────────────────────────────────────
    view_cols = st.columns([1, 1, 2])
    school_view = "All (Alphabetical)"
    house_view = "All (Alphabetical)"

    if "School" in results and results["School"]:
        with view_cols[0]:
            school_view = st.selectbox(
                "🏫 School results view",
                ["All (Alphabetical)", "Group by Class"],
                key=f"{widget_prefix}school_view_mode",
            )

    if "House" in results and results["House"]:
        with view_cols[1]:
            house_view = st.selectbox(
                "🏠 House results view",
                ["All (Alphabetical)", "Group by House"],
                key=f"{widget_prefix}house_view_mode",
            )

    st.html("<hr style='border-color:rgba(255,255,255,.07);margin:16px 0 24px;'>")

    # ── School Committees ─────────────────────────────────────────────────────
    if "School" in results:
        st.markdown("## 🏫 School Committees")

        if school_view == "Group by Class":
            grouped = _group_school_by_class(results["School"])
            for class_key, comms in grouped.items():
                _section_header_school_class(class_key)
                for comm_name, data in sorted(comms.items()):
                    _render_committee(
                        comm_name, data, student_votes,
                        show_tie_break, on_tie_break,
                        widget_prefix=f"{widget_prefix}cls{class_key}_",
                    )
        else:
            for comm_name, data in sorted(results["School"].items()):
                _render_committee(
                    comm_name, data, student_votes,
                    show_tie_break, on_tie_break,
                    widget_prefix=widget_prefix,
                )

    # ── House Committees ──────────────────────────────────────────────────────
    if "House" in results:
        st.markdown("## 🏠 House Committees")

        if house_view == "Group by House":
            grouped = _group_house_by_house(results["House"])
            for house_key, comms in grouped.items():
                _section_header_house(house_key)
                for comm_name, data in sorted(comms.items()):
                    _render_committee(
                        comm_name, data, student_votes,
                        show_tie_break, on_tie_break,
                        widget_prefix=f"{widget_prefix}house{house_key}_",
                    )
        else:
            for comm_name, data in sorted(results["House"].items()):
                _render_committee(
                    comm_name, data, student_votes,
                    show_tie_break, on_tie_break,
                    widget_prefix=widget_prefix,
                )
