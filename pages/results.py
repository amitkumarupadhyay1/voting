"""
Results rendering — used by both admin (live) and student (post-close).
Receives pre-fetched results dict; zero extra DB calls.
"""
import streamlit as st
import pandas as pd
from typing import Dict
from pages.components import ci, hm, avatar, RANK_ICONS, result_card_html, box


def render_results(results: Dict, show_tie_break: bool = False,
                   on_tie_break=None):
    """
    results: output of VotingEngine.get_results()
    show_tie_break: True only for admin in CLOSED phase
    on_tie_break: callable(committee_name, winner_adm, reason) — admin callback
    """
    if not results:
        st.markdown(box('info', '📋 No results yet — nominations and votes needed first.'),
                    unsafe_allow_html=True)
        return

    for ctype in ['School', 'House']:
        if ctype not in results:
            continue
        st.markdown(f"## {'🏫 School Committees' if ctype=='School' else '🏠 House Committees'}")

        for comm_name, data in sorted(results[ctype].items()):
            cands    = data['candidates']
            total_cv = data['total_votes']
            max_w    = data.get('max_winners', 1)
            info     = ci(comm_name)
            pos_label = f"{max_w} position{'s' if max_w > 1 else ''}"

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;
                        background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
                        border-radius:14px;padding:16px 20px;margin:20px 0 14px;">
                <span style="font-size:2rem;">{info['icon']}</span>
                <div>
                    <div style="font-size:1.15rem;font-weight:700;color:white;">{comm_name}</div>
                    <div style="font-size:.82rem;color:#64748b;">
                        {info['desc']} &nbsp;·&nbsp; {pos_label} &nbsp;·&nbsp; {total_cv} vote(s)
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

            if not cands:
                continue

            # Tie banner + tie-break UI
            tied_cands = [c for c in cands if c.get('is_tied')]
            if tied_cands:
                st.markdown(
                    box('warn', f'⚖️ <strong>TIE</strong> — {len(tied_cands)} candidates share '
                        f'the top position in <strong>{comm_name}</strong>.'),
                    unsafe_allow_html=True
                )
                if show_tie_break and on_tie_break:
                    with st.expander(f"🔨 Break tie for {comm_name}"):
                        options = {c['name']: c['adm'] for c in tied_cands}
                        chosen_name = st.selectbox(
                            'Select winner', list(options.keys()),
                            key=f'tb_sel_{comm_name}'
                        )
                        reason = st.text_input(
                            'Reason (required)', key=f'tb_reason_{comm_name}',
                            placeholder='e.g. Coin toss, teacher decision...'
                        )
                        if st.button('✅ Confirm Tie-Break', key=f'tb_btn_{comm_name}',
                                     type='primary'):
                            if not reason.strip():
                                st.error('Reason is required.')
                            else:
                                on_tie_break(comm_name, options[chosen_name], reason.strip())
                                st.rerun()

            # Podium (top 3, only when votes exist and ≥2 candidates)
            if total_cv > 0 and len(cands) >= 2:
                top3  = cands[:3]
                order = [1, 0, 2] if len(top3) >= 3 else [0, 1]
                pcols = st.columns(len(order))
                for pi, ri in enumerate(order):
                    if ri < len(top3):
                        c_   = top3[ri]
                        ht   = 100 if ri == 0 else (75 if ri == 1 else 55)
                        grad = ('linear-gradient(180deg,#f59e0b,#d97706)' if ri == 0
                                else 'linear-gradient(180deg,#94a3b8,#64748b)' if ri == 1
                                else 'linear-gradient(180deg,#b45309,#92400e)')
                        with pcols[pi]:
                            st.markdown(f"""
                            <div style="text-align:center;">
                                <div style="font-size:.85rem;font-weight:600;color:white;margin-bottom:4px;">
                                    {avatar(c_['name'])} {c_['name']}
                                </div>
                                <div style="font-size:.75rem;color:#94a3b8;margin-bottom:6px;">
                                    {int(c_['votes'])} votes
                                    {'⚖️' if c_.get('is_tied') else ''}
                                </div>
                                <div style="background:{grad};height:{ht}px;
                                            border-radius:12px 12px 0 0;
                                            display:flex;align-items:center;
                                            justify-content:center;font-size:1.8rem;">
                                    {RANK_ICONS[ri]}
                                </div>
                            </div>""", unsafe_allow_html=True)
                st.markdown('<br>', unsafe_allow_html=True)

            # Full ranked list
            for i, c_ in enumerate(cands):
                st.markdown(result_card_html(i + 1, c_, max_w, total_cv),
                            unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)
