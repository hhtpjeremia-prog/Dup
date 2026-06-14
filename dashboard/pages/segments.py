"""
Customer Segments page — member loyalty profiles with RFM radar or guest behavioural clusters.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import currency, chart_theme, DARK_COLORS, SEGMENT_DESCRIPTIONS
from components import metric_card_three_row, insight_mini_card, get_filtered_seg_counts
from engines import FinancialEngine, ForecastEngine


def render_segments(context: dict) -> None:
    """👥 Customer Segments — profiles with business-friendly language."""
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

    # ═══════════════════════════════════════════════════════════════════════
    #  MEMBER SEGMENTS
    # ═══════════════════════════════════════════════════════════════════════
    if is_member:
        st.markdown('<h2>👥 Member Loyalty Segments</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div style="color:#888;margin-bottom:16px;">'
            'Based on Recency, Frequency & Monetary value — '
            'showing how customers engage with the brand.</div>',
            unsafe_allow_html=True,
        )

        # ── KPI Row (4 compact cards) ────────────────────────────────────
        total_customers = int(filtered_seg['count'].sum()) if not filtered_seg.empty else 0

        try:
            if not filtered_seg.empty:
                largest = filtered_seg.nlargest(1, 'count').iloc[0]
                largest_name = largest['segment']
                largest_count = int(largest['count'])
            else:
                largest_name = 'N/A'
                largest_count = 0
        except Exception:
            largest_name = 'N/A'
            largest_count = 0

        # Revenue leader (from cluster profiles if available)
        try:
            profiles = meta.get('cluster_profiles', [])
            if profiles:
                top_rev = max(profiles, key=lambda p: p.get('revenue_share_pct', 0))
                rev_seg = meta['cluster_labels'][str(top_rev['cluster'])]
                rev_value = float(top_rev.get('M_mean', 0)) * int(top_rev.get('count', 0))
            else:
                rev_seg = largest_name
                rev_value = 0
        except Exception:
            rev_seg = 'N/A'
            rev_value = 0

        # At-risk segment (highest average recency gap)
        try:
            if profiles:
                at_risk = max(profiles, key=lambda p: p.get('R_mean', 0))
                at_risk_name = meta['cluster_labels'][str(at_risk['cluster'])]
                at_risk_count = int(at_risk.get('count', 0))
            else:
                at_risk_name = 'N/A'
                at_risk_count = 0
        except Exception:
            at_risk_name = 'N/A'
            at_risk_count = 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            metric_card_three_row('👥', 'Total Customers', 'Members', f'{int(total_customers):,}'),
            unsafe_allow_html=True,
        )
        c2.markdown(
            metric_card_three_row('🏆', 'Largest Segment', largest_name, f'{largest_count:,}'),
            unsafe_allow_html=True,
        )
        c3.markdown(
            metric_card_three_row('💰', 'Revenue Leader', rev_seg, f'{currency(rev_value, ",.0f")}'),
            unsafe_allow_html=True,
        )
        c4.markdown(
            metric_card_three_row('⚠', 'At Risk Customers', at_risk_name, f'{at_risk_count:,}'),
            unsafe_allow_html=True,
        )

        # ── Segment distribution ─────────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<h4>📊 Segment Distribution</h4>', unsafe_allow_html=True)

        dist_col1, dist_col2 = st.columns([1, 1.5])

        _pie_data = filtered_seg if not filtered_seg.empty else seg_counts
        fig_pie = px.pie(
            _pie_data, values='count', names='segment',
            title=None, color_discrete_sequence=DARK_COLORS, hole=0.4,
        )
        fig_pie.update_traces(
            textposition='inside', textinfo='percent',
            marker=dict(line=dict(color=CT['font'], width=1.5)),
            textfont=dict(color=CT['font'], size=11),
        )
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color=CT['font'], margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(font=dict(color=CT['legend'])), height=350,
        )
        dist_col1.plotly_chart(fig_pie, use_container_width=True)

        # Right: AI Segmentation Insight (stacked top->bottom)
        try:
            sc = filtered_seg.sort_values('count', ascending=False).reset_index(drop=True) if not filtered_seg.empty else seg_counts.sort_values('count', ascending=False).reset_index(drop=True)
            largest_name = sc.loc[0, 'segment'] if len(sc) > 0 else 'N/A'
            largest_count = int(sc.loc[0, 'count']) if len(sc) > 0 else 0
            pct_val = float(sc.loc[0, 'pct']) if ('pct' in sc.columns and len(sc) > 0) else 0.0
            biggest_name = sc.loc[1, 'segment'] if len(sc) > 1 else sc.loc[0, 'segment']
            biggest_count = int(sc.loc[1, 'count']) if len(sc) > 1 else largest_count
            biggest_pct = float(sc.loc[1, 'pct']) if ('pct' in sc.columns and len(sc) > 1) else (0.0 if len(sc) <= 1 else float(sc.loc[0, 'pct']))
        except Exception:
            largest_name = largest_name if 'largest_name' in locals() else 'N/A'
            largest_count = largest_count if 'largest_count' in locals() else 0
            pct_val = 0.0
            biggest_name = 'N/A'
            biggest_count = 0
            biggest_pct = 0.0

        # Simple recommended action heuristic
        if biggest_name == rev_seg:
            action = 'Drive high-value bundle promotions to this segment.'
        elif biggest_name == at_risk_name:
            action = 'Run reactivation & loyalty offers to recover lapsed customers.'
        else:
            action = f'Target {biggest_name} with a tailored promo and cross-sell bundles.'

        dist_col2.markdown(
            insight_mini_card('Largest Segment', largest_name, f'{largest_count:,} customers · {pct_val:.1f}%', color='#6C5CE7'),
            unsafe_allow_html=True,
        )
        dist_col2.markdown(
            insight_mini_card('Biggest Opportunity', biggest_name, f'{biggest_count:,} customers · {biggest_pct:.1f}%', color='#00B894'),
            unsafe_allow_html=True,
        )
        dist_col2.markdown(
            insight_mini_card('Recommended Action', action, 'Prioritize Q3 campaign execution', color='#FDAA5E'),
            unsafe_allow_html=True,
        )

        # ── Segment Profiles Table ───────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<h4>📋 Segment Profiles</h4>', unsafe_allow_html=True)

        profiles_data = []
        for p in meta['cluster_profiles']:
            seg_name = meta['cluster_labels'][str(p['cluster'])]
            desc = SEGMENT_DESCRIPTIONS.get(seg_name, '')
            profiles_data.append({
                'Segment': seg_name,
                'Description': desc,
                'Customers': f"{p['count']:,}",
                'Size': f"{p['pct']:.1f}%",
                'Avg Visit Gap': f"{p['R_mean']:.0f} days",
                'Avg Visits': f"{p['F_mean']:.1f}",
                'Avg Spend': currency(p['M_mean'], ',.0f'),
                'Revenue Share': f"{p['revenue_share_pct']:.1f}%",
            })
        st.dataframe(
            pd.DataFrame(profiles_data),
            hide_index=True,
            use_container_width=True,
            column_config={
                'Description': st.column_config.TextColumn(width='large'),
            },
        )

        # ── RFM Radar ────────────────────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<h4>📈 Loyalty Profile Comparison</h4>', unsafe_allow_html=True)

        max_r = max(p['R_mean'] for p in meta['cluster_profiles'])
        max_f = max(p['F_mean'] for p in meta['cluster_profiles'])
        max_m = max(p['M_mean'] for p in meta['cluster_profiles'])

        fig_radar = go.Figure()
        for i, p in enumerate(meta['cluster_profiles']):
            seg_name = meta['cluster_labels'][str(p['cluster'])]
            fig_radar.add_trace(go.Scatterpolar(
                r=[
                    1 - p['R_mean'] / max_r,
                    p['F_mean'] / max_f,
                    p['M_mean'] / max_m,
                    1 - p['R_mean'] / max_r,
                ],
                theta=['Visit Frequency (higher=better)', 'Visit Count', 'Total Spend', 'Visit Frequency'],
                name=seg_name,
                fill='toself',
                line_color=DARK_COLORS[i % len(DARK_COLORS)],
            ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], color=CT['axis']),
                bgcolor='rgba(0,0,0,0)',
            ),
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=CT['font'],
            legend=dict(font=dict(color=CT['legend'])),
            height=400,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  GUEST SEGMENTS
    # ═══════════════════════════════════════════════════════════════════════
    else:
        st.markdown('<h2>👥 Guest Behavioral Segments</h2>', unsafe_allow_html=True)
        st.markdown(
            '<div style="color:#888;margin-bottom:16px;">'
            'Based on transaction behavior — basket size, spending, visit timing, and voucher usage.</div>',
            unsafe_allow_html=True,
        )

        # ── KPI Row (4 compact cards) ────────────────────────────────────
        total_customers = int(filtered_seg['count'].sum()) if not filtered_seg.empty else 0

        try:
            if not filtered_seg.empty:
                largest = filtered_seg.nlargest(1, 'count').iloc[0]
                largest_name = largest['segment']
                largest_count = int(largest['count'])
            else:
                largest_name = 'N/A'
                largest_count = 0
        except Exception:
            largest_name = 'N/A'
            largest_count = 0

        # Revenue leader fallback
        try:
            profiles = meta.get('cluster_profiles', [])
            if profiles:
                top_rev = max(profiles, key=lambda p: p.get('revenue_share_pct', 0))
                rev_seg = meta['cluster_labels'][str(top_rev['cluster'])]
                rev_value = float(top_rev.get('M_mean', 0)) * int(top_rev.get('count', 0))
            else:
                rev_seg = largest_name
                rev_value = 0
        except Exception:
            rev_seg = 'N/A'
            rev_value = 0

        try:
            if profiles:
                at_risk = max(profiles, key=lambda p: p.get('R_mean', 0))
                at_risk_name = meta['cluster_labels'][str(at_risk['cluster'])]
                at_risk_count = int(at_risk.get('count', 0))
            else:
                at_risk_name = 'N/A'
                at_risk_count = 0
        except Exception:
            at_risk_name = 'N/A'
            at_risk_count = 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            metric_card_three_row('👥', 'Total Customers', 'Guests', f'{total_customers:,}'),
            unsafe_allow_html=True,
        )
        c2.markdown(
            metric_card_three_row('🏆', 'Largest Segment', largest_name, f'{largest_count:,}'),
            unsafe_allow_html=True,
        )
        c3.markdown(
            metric_card_three_row('💰', 'Revenue Leader', rev_seg, f'{currency(rev_value, ",.0f")}'),
            unsafe_allow_html=True,
        )
        c4.markdown(
            metric_card_three_row('⚠', 'At Risk Customers', at_risk_name, f'{at_risk_count:,}'),
            unsafe_allow_html=True,
        )

        # ── Segment distribution ─────────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<h4>📊 Segment Distribution</h4>', unsafe_allow_html=True)

        dist_col1, dist_col2 = st.columns([1, 1.5])

        _pie_data = filtered_seg if not filtered_seg.empty else seg_counts
        fig_pie = px.pie(
            _pie_data, values='count', names='segment',
            title=None, color_discrete_sequence=DARK_COLORS, hole=0.4,
        )
        fig_pie.update_traces(
            textposition='outside', textinfo='percent+label',
            marker=dict(line=dict(color=CT['font'], width=2)),
            textfont=dict(color=CT['font']),
        )
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color=CT['font'], margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(font=dict(color=CT['legend'])), height=350,
        )
        dist_col1.plotly_chart(fig_pie, use_container_width=True)

        _table_data = filtered_seg if not filtered_seg.empty else seg_counts
        dist_col2.dataframe(
            _table_data.style.format({'pct': '{:.1f}%', 'count': '{:,}'}),
            hide_index=True,
            use_container_width=True,
        )

        # ── Segment Profiles Table ───────────────────────────────────────
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<h4>📋 Segment Profiles</h4>', unsafe_allow_html=True)

        seg_info = []
        for cid, cname in meta['cluster_id_to_name'].items():
            desc = SEGMENT_DESCRIPTIONS.get(cname, '')
            seg_info.append({'Segment': cname, 'Description': desc})
        st.dataframe(pd.DataFrame(seg_info), hide_index=True, use_container_width=True)

    # ── Model info expander (common to both member & guest) ─────────────
    st.markdown('<br>', unsafe_allow_html=True)
    with st.expander('ℹ️ Additional Information'):
        st.markdown(
            '<div style="color:#888;font-size:0.85rem;">'
            'Segments were identified using behavioral clustering on transaction history. '
            'Each group shares similar purchasing patterns and responds differently to promotions.</div>',
            unsafe_allow_html=True,
        )
