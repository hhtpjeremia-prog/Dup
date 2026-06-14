"""
Bundle Intelligence page — data-driven bundle recommendations with margin
calculator, profit impact forecast, and performance indicators.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from config import (
    currency, cur_sym, _c, _fmt_idr, _chart_cv, hex_to_rgba, chart_theme,
    BUSINESS_COLUMNS, SEGMENT_DESCRIPTIONS, DARK_COLORS,
)
from components import compact_metric_card, metric_card_three_row, insight_mini_card
from loaders import load_historical_daily
from engines import FinancialEngine, ForecastEngine


def render_bundles(context: dict) -> None:
    """🛒 Bundle Intelligence — clickable rules with business terms, updates forecast."""
    fin_engine: FinancialEngine = context['fin_engine']
    fc_engine: ForecastEngine = context['fc_engine']
    meta: dict = context['meta']
    seg_counts: pd.DataFrame = context['seg_counts']
    rules_df: pd.DataFrame = context['rules_df']
    menu_df: pd.DataFrame = context['menu_df']
    is_member: bool = context['is_member']

    CT = chart_theme()

    # ── Heading ────────────────────────────────────────────────────────────
    st.markdown('<h2>🛒 Bundle Intelligence</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#888;margin-bottom:16px;">'
        'Discover data-driven product bundle recommendations based on '
        'customer purchase patterns. <strong>Click any bundle</strong> to '
        'see its margin breakdown, projected profit impact, and performance '
        'indicators.</div>',
        unsafe_allow_html=True,
    )

    if rules_df is None or len(rules_df) == 0:
        st.warning('No bundle rules available for this customer group.')
        return

    # ── Sort rules by lift descending ─────────────────────────────────────
    sorted_rules = rules_df.sort_values('lift', ascending=False).reset_index(drop=True)

    # ── Filters (product name dropdown) ────────────────────────────────────
    all_products = sorted(
        set(sorted_rules['antecedents'].unique())
        | set(sorted_rules['consequents'].unique())
    )
    col_filt1, col_filt2 = st.columns([1, 3])
    with col_filt1:
        selected_product = st.selectbox(
            'Filter by Product',
            ['All Products'] + all_products,
            help='Narrow bundles to those involving a specific product',
        )

    # Apply product filter
    if selected_product != 'All Products':
        filtered = sorted_rules[
            (sorted_rules['antecedents'] == selected_product)
            | (sorted_rules['consequents'] == selected_product)
        ].copy()
    else:
        filtered = sorted_rules.copy()

    # ── Two-column layout: rules table (left) + bundle detail (right) ─────
    col_table, col_detail = st.columns([0.55, 0.45], gap='large')

    # ──────────────────────────────────────────────────────────────────────
    #  LEFT COLUMN: Rules table
    # ──────────────────────────────────────────────────────────────────────
    with col_table:
        st.markdown('<h4>📋 Available Product Bundles</h4>', unsafe_allow_html=True)

        display_df = filtered[[
            'antecedents', 'consequents', 'support', 'confidence', 'lift'
        ]].copy()
        display_df.columns = [
            'Product A', 'Product B',
            'Popularity', 'Success Rate', 'Cross-Sell',
        ]

        styled = display_df.style.format({
            'Popularity': '{:.1%}',
            'Success Rate': '{:.1%}',
            'Cross-Sell': '{:.3f}',
        })

        # Clickable data table — store selection via session_state
        selection = st.dataframe(
            styled,
            hide_index=True,
            use_container_width=True,
            height=420,
            on_select='rerun',
            selection_mode='single-row',
            key='bundle_table',
        )

        # Extract selected row — only update if bundle actually changed
        # (prevents infinite loop: on_select='rerun' already triggers re-run)
        if selection and len(selection.selection.rows) > 0:
            row_idx = selection.selection.rows[0]
            if row_idx < len(filtered):
                sel_row = filtered.iloc[row_idx]
                bundle_label = f"{sel_row['antecedents']} + {sel_row['consequents']}"
                if st.session_state.get('selected_bundle') != bundle_label:
                    st.session_state.selected_bundle = bundle_label
                    st.session_state.bundle_source = 'Members' if is_member else 'Guests (Non-Members)'
        else:
            # Also support quick-select buttons as an alternative
            st.markdown(
                '<div style="color:#B0B0C0;font-size:0.85rem;margin-top:12px;">'
                'Or quick-select a popular bundle:</div>',
                unsafe_allow_html=True,
            )
            top_n = filtered.head(12)
            cols_per_row = 2
            for i in range(0, min(len(top_n), 10), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(top_n):
                        row = top_n.iloc[idx]
                        bundle_label = f"{row['antecedents']} + {row['consequents']}"
                        with cols[j]:
                            if st.button(
                                f"☕ {bundle_label}",
                                key=f"bundle_quick_{idx}",
                                help=f"Success Rate: {row['confidence']*100:.0f}% | Lift: {row['lift']:.2f}",
                                use_container_width=True,
                            ):
                                st.session_state.selected_bundle = bundle_label
                                st.session_state.bundle_source = 'Members' if is_member else 'Guests (Non-Members)'

        st.caption(f'Showing {len(filtered)} of {len(sorted_rules)} bundle opportunities')

    # ──────────────────────────────────────────────────────────────────────
    #  RIGHT COLUMN: Bundle detail (when selected)
    # ──────────────────────────────────────────────────────────────────────
    with col_detail:
        if st.session_state.get('selected_bundle'):
            bundle_name = st.session_state.selected_bundle
            source_seg = st.session_state.bundle_source

            st.markdown(
                f'<h4>📦 {bundle_name}</h4>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="color:#888;font-size:0.85rem;margin-bottom:12px;">'
                f'Segment: <strong>{source_seg}</strong></div>',
                unsafe_allow_html=True,
            )

            # Find the matching rule
            match = filtered[
                (filtered['antecedents'] + ' + ' + filtered['consequents'] == bundle_name)
            ]
            if len(match) == 0:
                match = filtered[
                    (filtered['consequents'] + ' + ' + filtered['antecedents'] == bundle_name)
                ]

            if len(match) > 0:
                detail = match.iloc[0]
                confidence = float(detail['confidence'])
                lift_val = float(detail['lift'])
                support_val = float(detail['support'])
            else:
                confidence = 0.20
                lift_val = 0.70
                support_val = 0.01

            # ── Margin Calculator ─────────────────────────────────────────
            items_a = str(detail['antecedents']) if len(match) > 0 else bundle_name.split(' + ')[0]
            items_b = str(detail['consequents']) if len(match) > 0 else bundle_name.split(' + ')[1]
            bundle_items = [items_a, items_b]

            margin = fin_engine.get_bundle_margin(bundle_items, discount=0.0)

            st.markdown(
                f"""
                <div class="insight-card" style="padding:14px;margin-bottom:12px;">
                    <div style="color:var(--txt-secondary);font-size:0.75rem;font-weight:600;text-transform:uppercase;margin-bottom:8px;">
                        💰 Margin Calculator
                    </div>
                    <table style="width:100%;font-size:0.85rem;color:var(--txt-secondary);">
                        <tr>
                            <td>Bundle Price</td>
                            <td style="text-align:right;color:var(--txt-primary);font-weight:600;">
                                {currency(margin['price'], ',.2f')}
                            </td>
                        </tr>
                        <tr>
                            <td>COGS (Raw Materials)</td>
                            <td style="text-align:right;color:#E17055;">
                                −{currency(margin['cogs'], ',.2f')}
                            </td>
                        </tr>
                        <tr>
                            <td>Operating Cost</td>
                            <td style="text-align:right;color:#E17055;">
                                −{currency(margin['op_cost'], ',.2f')}
                            </td>
                        </tr>
                        <tr style="border-top:1px solid var(--border);">
                            <td style="font-weight:600;color:var(--txt-primary);">Net Profit</td>
                            <td style="text-align:right;font-weight:700;color:#00B894;">
                                {currency(margin['net'], ',.2f')}
                            </td>
                        </tr>
                        <tr>
                            <td>Margin Ratio</td>
                            <td style="text-align:right;font-weight:600;color:#6C5CE7;">
                                {margin['margin_pct']:.1f}%
                            </td>
                        </tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ── Projected Profit Impact Chart ─────────────────────────────
            avg_margin = fin_engine.get_net_margin('Latte')
            margin_pct = avg_margin['net_margin_pct'] / 100
            boost_factor = confidence * lift_val * 0.15

            impact_df = fc_engine.get_bundle_impact_forecast(
                bundle_name, margin_pct=margin_pct, boost_factor=boost_factor
            )

            sel_branches = st.session_state.get('branch_filter', [])
            if sel_branches:
                try:
                    impact_df = impact_df[impact_df['branch'].isin(sel_branches)]
                except Exception:
                    pass

            agg_impact = impact_df.groupby(
                ['created_at', 'scenario']
            )[['projected_profit', 'profit_increase']].sum().reset_index()

            total_increase = agg_impact.groupby('scenario')['profit_increase'].sum()
            total_profit = agg_impact.groupby('scenario')['projected_profit'].sum()

            fig_impact = go.Figure()
            for scenario in agg_impact['scenario'].unique():
                sdata = agg_impact[agg_impact['scenario'] == scenario]
                color = '#6C5CE7' if 'Conservative' in scenario else '#00B894'
                fig_impact.add_trace(go.Scatter(
                    x=sdata['created_at'],
                    y=sdata['projected_profit'],
                    mode='lines',
                    name=f'{scenario} (Baseline)',
                    line=dict(color=color, width=1.5, dash='dot'),
                ))
                fig_impact.add_trace(go.Scatter(
                    x=sdata['created_at'],
                    y=sdata['projected_profit'] + sdata['profit_increase'],
                    mode='lines',
                    name=f'{scenario} (With Bundle)',
                    line=dict(color=color, width=2.5),
                ))

            fig_impact.update_layout(
                title=f'Profit Impact: "{bundle_name}"',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color=CT['font'],
                xaxis=dict(showgrid=False, color=CT['axis']),
                yaxis=dict(showgrid=True, gridcolor=CT['grid'], color=CT['axis'],
                          title=f'Profit ({cur_sym()})'),
                legend=dict(
                    font=dict(color=CT['legend']), orientation='h',
                    y=-0.12, yanchor='top', x=0.5, xanchor='center',
                ),
                margin=dict(l=40, r=20, t=60, b=80),
                hovermode='x unified',
                height=300,
            )
            st.plotly_chart(fig_impact, use_container_width=True)

            # ── Bundle Performance Indicators ─────────────────────────────
            if len(match) > 0:
                st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown(
                    '<h4 style="font-size:0.95rem;">📊 Performance Indicators</h4>',
                    unsafe_allow_html=True,
                )

                det1, det2, det3 = st.columns(3)
                det1.markdown(
                    f"""
                    <div class="insight-card" style="padding:12px;text-align:center;">
                        <div style="color:#B0B0C0;font-size:0.7rem;text-transform:uppercase;margin-bottom:4px;">
                            Popularity Score
                        </div>
                        <div style="font-size:1.4rem;font-weight:700;color:var(--txt-primary);">
                            {support_val*100:.1f}%
                        </div>
                        <div style="font-size:0.7rem;color:#888;">How common this pair is</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                det2.markdown(
                    f"""
                    <div class="insight-card" style="padding:12px;text-align:center;">
                        <div style="color:#B0B0C0;font-size:0.7rem;text-transform:uppercase;margin-bottom:4px;">
                            Projected Success Rate
                        </div>
                        <div style="font-size:1.4rem;font-weight:700;color:#00B894;">
                            {confidence*100:.1f}%
                        </div>
                        <div style="font-size:0.7rem;color:#888;">A → B likelihood</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                det3.markdown(
                    f"""
                    <div class="insight-card" style="padding:12px;text-align:center;">
                        <div style="color:#B0B0C0;font-size:0.7rem;text-transform:uppercase;margin-bottom:4px;">
                            Cross-Sell Potential
                        </div>
                        <div style="font-size:1.4rem;font-weight:700;color:#6C5CE7;">
                            {lift_val:.2f}
                        </div>
                        <div style="font-size:0.7rem;color:#888;">>1 = strong pairing</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ── Clear selection button ────────────────────────────────────
            st.markdown('<br>', unsafe_allow_html=True)
            if st.button('🔄 Clear Bundle Selection', key='clear_bundle_detail', use_container_width=True):
                st.session_state.selected_bundle = None
                st.session_state.bundle_source = None

        else:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;color:#666;">'
                '👆 Select a bundle from the left table<br>'
                'to see margin, profit impact, and KPIs</div>',
                unsafe_allow_html=True,
            )
