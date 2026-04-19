"""
Results rendering — used by both admin (live) and student (post-close).
Receives pre-fetched results dict; zero extra DB calls.
"""

from typing import Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pages.components import RANK_ICONS, avatar, box, ci, hm, result_card_html


def _render_vote_distribution_chart(cands: list, comm_name: str, total_cv: int):
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

    st.plotly_chart(fig, use_container_width=True, key=f"bar_{comm_name}")


def _render_house_participation_chart(cands: list, comm_name: str):
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

    st.plotly_chart(fig, use_container_width=True, key=f"pie_{comm_name}")


def _render_animated_podium(cands: list, comm_name: str):
    """Sub-task 1.3.3: Display winner podium with animations"""
    if not cands or len(cands) < 2:
        return

    top3 = cands[:3]
    order = [1, 0, 2] if len(top3) >= 3 else [0, 1]

    # Add CSS animation for podium
    st.markdown(
        """
    <style>
    @keyframes slideUp {
        from {
            transform: translateY(100px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }
    .podium-animated {
        animation: slideUp 0.6s ease-out forwards;
    }
    .podium-winner {
        animation: slideUp 0.6s ease-out forwards, pulse 2s ease-in-out infinite;
    }
    .podium-glow {
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.5);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    pcols = st.columns(len(order))
    for pi, ri in enumerate(order):
        if ri < len(top3):
            c_ = top3[ri]
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

            animation_class = "podium-winner" if ri == 0 else "podium-animated"
            glow_class = "podium-glow" if ri == 0 else ""
            delay_seconds = pi * 0.2

            with pcols[pi]:
                html_content = f"""
<div class="{animation_class}" style="animation-delay:{delay_seconds}s;text-align:center;">
    <div style="font-size:.85rem;font-weight:600;color:white;margin-bottom:4px;">
        {avatar(c_['name'])} {c_['name']}
    </div>
    <div style="font-size:.75rem;color:#94a3b8;margin-bottom:6px;">
        {int(c_['votes'])} votes
        {'⚖️' if c_.get('is_tied') else ''}
    </div>
    <div class="{glow_class}" style="background:{grad};height:{ht}px;
                border-radius:12px 12px 0 0;
                display:flex;align-items:center;
                justify-content:center;font-size:1.8rem;">
        {RANK_ICONS[ri]}
    </div>
</div>
"""
                st.markdown(html_content, unsafe_allow_html=True)


def render_results(
    results: Dict,
    show_tie_break: bool = False,
    on_tie_break=None,
    student_votes: Dict = None,
):
    """
    results: output of VotingEngine.get_results()
    show_tie_break: True only for admin in CLOSED phase
    on_tie_break: callable(committee_name, winner_adm, reason) — admin callback
    student_votes: dict of {committee_name: {'candidate_name': str, ...}} for highlighting
    """
    if not results:
        st.markdown(
            box("info", "📋 No results yet — nominations and votes needed first."),
            unsafe_allow_html=True,
        )
        return

    for ctype in ["School", "House"]:
        if ctype not in results:
            continue
        st.markdown(
            f"## {'🏫 School Committees' if ctype == 'School' else '🏠 House Committees'}",
            unsafe_allow_html=True,
        )

        for comm_name, data in sorted(results[ctype].items()):
            cands = data["candidates"]
            total_cv = data["total_votes"]
            max_w = data.get("max_winners", 1)
            info = ci(comm_name)
            pos_label = f"{max_w} position{'s' if max_w > 1 else ''}"

            # Check if student voted in this committee
            student_voted_here = student_votes and comm_name in student_votes
            voted_indicator = ""
            if student_voted_here:
                voted_indicator = '<span style="margin-left:10px;background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.4);color:#34d399;padding:4px 12px;border-radius:99px;font-size:.75rem;font-weight:700;">✓ You Voted</span>'

            st.markdown(
                f"""
<div style="display:flex;align-items:center;gap:14px;
            background:{'rgba(16,185,129,.08)' if student_voted_here else 'rgba(255,255,255,.04)'};
            border:1px solid {'rgba(16,185,129,.25)' if student_voted_here else 'rgba(255,255,255,.08)'};
            border-radius:14px;padding:16px 20px;margin:20px 0 14px;">
    <span style="font-size:2rem;">{info['icon']}</span>
    <div style="flex:1;">
        <div style="font-size:1.15rem;font-weight:700;color:white;">{comm_name}{voted_indicator}</div>
        <div style="font-size:.82rem;color:#64748b;">
            {info['desc']} &nbsp;·&nbsp; {pos_label} &nbsp;·&nbsp; {total_cv} vote(s)
        </div>
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
                    box(
                        "warn",
                        f"⚖️ <strong>TIE</strong> — {len(tied_cands)} candidates share "
                        f"the top position in <strong>{comm_name}</strong>.",
                    ),
                    unsafe_allow_html=True,
                )
                if show_tie_break and on_tie_break:
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
                            placeholder="e.g. Coin toss, teacher decision...",
                        )
                        if st.button(
                            "✅ Confirm Tie-Break",
                            key=f"tb_btn_{comm_name}",
                            type="primary",
                        ):
                            if not reason.strip():
                                st.error("Reason is required.")
                            else:
                                on_tie_break(
                                    comm_name, options[chosen_name], reason.strip()
                                )
                                st.rerun()

            # Sub-task 1.3.3: Animated podium (top 3, only when votes exist and ≥2 candidates)
            if total_cv > 0 and len(cands) >= 2:
                _render_animated_podium(cands, comm_name)
                st.markdown("<br>", unsafe_allow_html=True)

            # Sub-task 1.3.1: Bar chart for vote distribution
            if total_cv > 0:
                with st.expander("📊 Vote Distribution Chart", expanded=False):
                    _render_vote_distribution_chart(cands, comm_name, total_cv)

            # Sub-task 1.3.2: Pie chart for house participation
            if total_cv > 0 and len(set(c["house"] for c in cands)) > 1:
                with st.expander("🏠 House Participation Chart", expanded=False):
                    _render_house_participation_chart(cands, comm_name)

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
                st.markdown(
                    result_card_html(i + 1, c_, max_w, total_cv, is_student_choice),
                    unsafe_allow_html=True,
                )
            st.markdown("<br>", unsafe_allow_html=True)
