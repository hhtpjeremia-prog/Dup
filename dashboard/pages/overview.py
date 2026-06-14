"""
Overview page — executive summary with KPIs, segment snapshot, and top rules.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from config import currency, cur_sym, _c, _fmt_idr, _chart_cv, hex_to_rgba, chart_theme, SEGMENT_DESCRIPTIONS, DARK_COLORS, IDR_RATE
from components import compact_metric_card, metric_card_three_row, insight_mini_card, get_filtered_seg_counts
from engines import FinancialEngine, ForecastEngine
from loaders import load_historical_daily, load_avg_tx_value


def render_overview(context: dict) -> None:
    """📊 Overview — Executive summary."""
    fin_engine: FinancialEngine = context['fin_engine']
    fc_engine: ForecastEngine = context['fc_engine']
    meta: dict = context['meta']
    seg_counts: pd.DataFrame = context['seg_counts']
    rules_df: pd.DataFrame = context['rules_df']
    menu_df: pd.DataFrame = context['menu_df']
    is_member: bool = context['is_member']

    CT = chart_theme()

    # ── Branch-aware segment counts ───────────────────────────────────────
    filtered_seg = get_filtered_seg_counts(is_member)

    # ── KPI Row ───────────────────────────────────────────────────────────
    total_members = int(filtered_seg['count'].sum()) if not filtered_seg.empty else 0
    n_segments = len(filtered_seg) if not filtered_seg.empty else 0

    avg_tx = fc_engine.avg_transaction_value if fc_engine is not None else 0.0
    menu_count = len(menu_df) if menu_df is not None else 0

    col1, col2, col3, col4 = st.columns(4, gap='small')
    col1.markdown(compact_metric_card('👥', 'Customer Base', f'{total_members:,}', note='Total segmented'), unsafe_allow_html=True)
    col2.markdown(compact_metric_card('📊', 'Segments Identified', str(n_segments), note='Behavioural clusters'), unsafe_allow_html=True)
    col3.markdown(compact_metric_card('☕', 'Menu Items', str(menu_count), note='Products tracked'), unsafe_allow_html=True)
    col4.markdown(compact_metric_card('💰', 'Avg Transaction', f'{currency(avg_tx)}', note='Overall average'), unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Segment Distribution (Pie + Table) ────────────────────────────────
    st.markdown('<h4>📊 Segment Distribution</h4>', unsafe_allow_html=True)
    col_pie, col_table = st.columns([0.5, 0.5], gap='medium')

    with col_pie:
        if not filtered_seg.empty:
            _plot_data = filtered_seg.sort_values('count', ascending=True)
            fig_pie = px.pie(
                _plot_data, values='count', names='segment',
                color_discrete_sequence=DARK_COLORS,
                hole=0.45,
            )
            fig_pie.update_traces(
                textposition='inside', textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>Pct: %{percent}<extra></extra>',
            )
            fig_pie.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=CT['font'],
                showlegend=False,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_table:
        if not filtered_seg.empty:
            display = filtered_seg.copy()
            display['count'] = display['count'].apply(lambda x: f'{x:,}')
            display['pct'] = display['pct'].apply(lambda x: f'{x:.1f}%')
            display.columns = ['Segment', 'Count', '%']
            st.dataframe(display, hide_index=True, use_container_width=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Segment Profiles ─────────────────────────────────────────────────
    st.markdown('<h4>📋 Segment Profiles</h4>', unsafe_allow_html=True)

    profiles = meta.get('cluster_profiles', [])
    labels = meta.get('cluster_labels', {})
    if profiles:
        # Determine columns: if member (RFM) or guest (features)
        has_rfm = any(k in profiles[0] for k in ('R_mean', 'F_mean', 'M_mean'))
        if has_rfm:
            profile_cols = st.columns(len(profiles))
            for i, p in enumerate(profiles):
                seg_name = labels.get(str(p['cluster']), f'Cluster {p["cluster"]}')
                desc = SEGMENT_DESCRIPTIONS.get(seg_name, '')
                with profile_cols[i]:
                    st.markdown(
                        metric_card_three_row(
                            '🎯', seg_name, desc,
                            currency(p.get('M_mean', 0), ',.0f'),
                            note=f'R: {p.get("R_mean", 0):.0f}d · F: {p.get("F_mean", 0):.1f}x · {p.get("count", 0):,} members'
                        ),
                        unsafe_allow_html=True
                    )
        else:
            # Guest profiles: show key feature averages
            profile_cols = st.columns(len(profiles))
            for i, p in enumerate(profiles):
                seg_name = labels.get(str(p['cluster']), f'Cluster {p["cluster"]}')
                with profile_cols[i]:
                    st.markdown(
                        metric_card_three_row(
                            '🎯', seg_name, f'{p.get("count", 0):,} guests',
                            f'avg ${p.get("final_amount", 0):.1f}',
                            note=f'basket: {p.get("basket_size", 0):.1f} · items: {p.get("item_count", 0):.1f}'
                        ),
                        unsafe_allow_html=True
                    )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Top Association Rules ────────────────────────────────────────────
    st.markdown('<h4>🛒 Top Association Rules</h4>', unsafe_allow_html=True)
    if rules_df is not None and len(rules_df) > 0:
        top_rules = rules_df.sort_values('lift', ascending=False).head(10)
        display_rules = top_rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].copy()
        display_rules['support'] = display_rules['support'].apply(lambda x: f'{x:.3f}')
        display_rules['confidence'] = display_rules['confidence'].apply(lambda x: f'{x:.2f}')
        display_rules['lift'] = display_rules['lift'].apply(lambda x: f'{x:.2f}')
        display_rules.columns = ['Product A', 'Product B', 'Support', 'Confidence', 'Lift']
        st.dataframe(display_rules, hide_index=True, use_container_width=True)
    else:
        st.info('No association rules available for the current segment.')

    # ── Forecast KPI Summary ─────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<h4>📈 Forecast at a Glance</h4>', unsafe_allow_html=True)

    try:
        avg_margin = fin_engine.get_net_margin('Latte')
        margin_pct = avg_margin['net_margin_pct'] / 100
        profit_fc = fc_engine.get_profit_forecast(margin_pct=margin_pct)
        if profit_fc is not None and len(profit_fc) > 0:
            cons = profit_fc[profit_fc['scenario'] == 'Conservative Growth']['projected_profit'].sum()
            aggr = profit_fc[profit_fc['scenario'] == 'Aggressive Growth']['projected_profit'].sum()
            c1, c2 = st.columns(2)
            c1.markdown(compact_metric_card('📈', 'Conservative 90d Profit', currency(cons, ',.0f')), unsafe_allow_html=True)
            c2.markdown(compact_metric_card('🚀', 'Aggressive 90d Profit', currency(aggr, ',.0f')), unsafe_allow_html=True)
    except Exception:
        st.info('Forecast data not available yet.')
