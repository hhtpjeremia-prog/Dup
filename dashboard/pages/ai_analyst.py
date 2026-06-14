"""
AI Business Analyst page — natural language insights via Groq.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from config import (
    currency, cur_sym, _c, _fmt_idr, hex_to_rgba, chart_theme,
    DARK_COLORS, DATA,
)
from components import compact_metric_card, metric_card_three_row, insight_mini_card
from loaders import load_json, load_historical_daily
from engines import FinancialEngine, ForecastEngine
from Groq_analyst import GroqAnalyst, build_context


def render_ai_analyst(context: dict) -> None:
    """🤖 AI Business Analyst — natural language insights via Groq."""
    fin_engine: FinancialEngine = context['fin_engine']
    fc_engine: ForecastEngine = context['fc_engine']
    meta: dict = context['meta']
    seg_counts: pd.DataFrame = context['seg_counts']
    rules_df: pd.DataFrame = context['rules_df']
    menu_df: pd.DataFrame = context['menu_df']
    is_member: bool = context['is_member']
    groq_analyst: GroqAnalyst = context['groq_analyst']

    CT = chart_theme()

    # ── Title ────────────────────────────────────────────────────────────────
    st.markdown('<h2>🤖 AI Business Analyst</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#888;margin-bottom:8px;">'
        'Tanya apapun tentang bisnis — AI akan jawab berdasarkan data real.</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 1: CHECK GROQ READINESS
    # ══════════════════════════════════════════════════════════════════════════

    if not groq_analyst.is_ready:
        st.info(
            "🔑 **Set API Key Groq**\n\n"
            "1. Buka https://console.groq.com (tidak perlu CC)\n"
            "2. Buat API key\n"
            "3. Set environment variable:\n"
            "   ```powershell\n"
            '   $env:GROQ_API_KEY = "gsk_..."\n'
            "   ```\n"
            "   Atau restart terminal, lalu jalankan ulang app."
        )
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 2: FILTERS (3 columns)
    # ══════════════════════════════════════════════════════════════════════════

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        seg_list = sorted(seg_counts["segment"].unique().tolist())
        sel_seg = st.selectbox("Target Segmen", seg_list, key="ai_segment")

    with col_f2:
        branch_list = sorted(
            load_historical_daily()["city"].unique().tolist()
        )
        bf = st.session_state.get('branch_filter', [])
        default_index = 0
        if bf:
            try:
                if bf[0] in branch_list:
                    default_index = branch_list.index(bf[0])
            except Exception:
                default_index = 0
        sel_branch = st.selectbox(
            "Cabang", branch_list, index=default_index, key="ai_branch"
        )

    with col_f3:
        day_type = st.radio(
            "Tipe Hari", ["Weekday", "Weekend"], horizontal=True, key="ai_day"
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 3: SUGGESTED QUESTIONS
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.85rem;margin-bottom:8px;">Coba tanya:</div>',
        unsafe_allow_html=True,
    )

    suggestions = [
        "Rekomendasi voucher apa yang tepat untuk segmen ini?",
        "Bundle produk apa yang cocok?",
        "Apa insight utama dari data ini?",
        "Custom...",
    ]
    cols = st.columns(4)
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, key=f"ai_sug_{i}", use_container_width=True):
                st.session_state["ai_question"] = (
                    suggestion if suggestion != "Custom..." else ""
                )
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 4: FREE TEXT INPUT
    # ══════════════════════════════════════════════════════════════════════════

    question = st.text_input(
        "✏️ Atau tulis pertanyaan sendiri:",
        key="ai_question",
        placeholder="Contoh: Rekomendasi bundling untuk Matcha Latte di USJ?",
        label_visibility="collapsed",
    )

    st.markdown('<br>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 5: GENERATE INSIGHT
    # ══════════════════════════════════════════════════════════════════════════

    # ── Load peak hours ────────────────────────────────────────────────────
    _peak_hours = load_json(DATA / "df_peak_hours.json")
    _peak_hour = str(_peak_hours.get(sel_branch, "8")) if _peak_hours else "-"

    if question:
        with st.spinner("🧠 Menganalisis data..."):
            context_json = build_context(
                segment_name=sel_seg,
                seg_counts=seg_counts,
                meta=meta,
                branch_name=sel_branch,
                branch_city=sel_branch,
                day_type=day_type,
                peak_hour=_peak_hour,
                rules_df=rules_df,
                menu_df=menu_df,
                fin_engine=fin_engine,
                fc_engine=fc_engine,
                question=question,
                currency=st.session_state.get('currency', 'RM'),
            )

            # Panggil Groq (di-cache 5 menit oleh GroqAnalyst.analyze)
            insight = groq_analyst.analyze(context_json)

        # ── Display insight ────────────────────────────────────────────────
        st.markdown("### 💡 Hasil Analisis")
        st.markdown(
            f'<div class="insight-card" style="line-height:1.7;">{insight}</div>',
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            '<div style="color:#666;text-align:center;padding:40px;">'
            "☝️ Pilih pertanyaan di atas atau tulis sendiri</div>",
            unsafe_allow_html=True,
        )
