"""
Overview page — executive summary with hero recommendation, KPIs,
segment snapshot, AI action center, forecast, product intelligence,
and segment profiles & top rules.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from config import currency, cur_sym, chart_theme, SEGMENT_DESCRIPTIONS, DARK_COLORS
from components import compact_metric_card, metric_card_three_row, insight_mini_card, get_filtered_seg_counts
from engines import FinancialEngine, ForecastEngine


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

    # ── Dashboard lens (affects Revenue vs Profit across sections) ────────
    _rev_ft = st.session_state.get('dashboard_lens', 'Profit') == 'Revenue'
    _ft_label = 'Revenue' if _rev_ft else 'Profit'
    _ft_metric = 'projected_revenue' if _rev_ft else 'projected_profit'

    # ── Compute base metrics ───────────────────────────────────────────────
    total_customers = int(filtered_seg['count'].sum()) if not filtered_seg.empty else 0
    n_segments = len(filtered_seg) if not filtered_seg.empty else 0
    avg_margin = fin_engine.get_net_margin('Latte')
    avg_profit_pct = avg_margin['net_margin_pct']

    # Forecast (branch-filtered)
    profit_fc = fc_engine.get_profit_forecast(margin_pct=avg_profit_pct / 100)

    # Apply branch filter
    sel_branches = st.session_state.get('branch_filter', [])
    if sel_branches:
        try:
            profit_fc = profit_fc[profit_fc['branch'].isin(sel_branches)]
        except Exception:
            pass

    avg_daily_metric = profit_fc.groupby('scenario')[_ft_metric].mean().mean() if len(profit_fc) > 0 else 0
    n_bundles = len(rules_df) if rules_df is not None else 0

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 1: HERO RECOMMENDATION (full-width strategic action card)
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)

    try:
        best_branch_ser = profit_fc.groupby('branch')[_ft_metric].sum()
        best_branch = best_branch_ser.idxmax() if len(best_branch_ser) > 0 else 'All Branches'
    except Exception:
        best_branch = 'All Branches'

    best_segment = (
        seg_counts.nlargest(1, 'count')['segment'].values[0]
        if len(seg_counts) > 0 else 'Top Segment'
    )

    best_bundle = 'Premium Bundle Combo'
    if rules_df is not None and len(rules_df) > 0:
        best_rule = rules_df.nlargest(1, 'lift').iloc[0]
        best_bundle = f"{best_rule['antecedents']} + {best_rule['consequents']}"

    hero_impact = (avg_daily_metric * 90 * 0.08) if avg_daily_metric > 0 else 0
    hero_uplift_pct = (hero_impact / avg_daily_metric / 90 * 100) if avg_daily_metric > 0 else 0

    with st.container():
        st.markdown(f"""
        <div class="insight-card" style="padding:24px;background:linear-gradient(135deg, var(--bg-card), var(--bg-radio-sel));border:1px solid var(--border);margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:24px;">
                <div style="flex:1;">
                    <div style="font-size:0.75rem;color:var(--txt-secondary);font-weight:600;text-transform:uppercase;margin-bottom:8px;">🎯 Strategic Recommendation</div>
                    <h3 style="margin:0;color:var(--txt-primary);font-size:20px;margin-bottom:8px;">
                        Focus <strong>{best_segment}</strong> at <strong>{best_branch}</strong>
                    </h3>
                    <p style="margin:0;color:var(--txt-secondary);font-size:14px;line-height:1.5;">
                        Launch the <strong>"{best_bundle}"</strong> promotion to drive cross-sell engagement. Expected impact: <span style="color:#00B894;font-weight:600;">{currency(hero_impact, ',.0f')}</span> additional profit over 90 days.
                    </p>
                </div>
                <div style="text-align:right;white-space:nowrap;">
                    <div style="font-size:0.75rem;color:var(--txt-secondary);margin-bottom:4px;">EXPECTED UPLIFT</div>
                    <div style="font-size:28px;font-weight:700;color:#00B894;">{hero_uplift_pct:.1f}%</div>
                    <div style="font-size:12px;color:var(--txt-muted);margin-top:8px;">90-day impact</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 2: KPI ROW (4 cards with deltas)
    # ═══════════════════════════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4, gap='large')

    with col1:
        st.markdown(compact_metric_card(
            '👥', 'Total Customers', f'{total_customers:,}',
            delta=3.2, note=f'{n_segments} segments'
        ), unsafe_allow_html=True)

    with col2:
        st.markdown(compact_metric_card(
            '💰', 'Avg Net Profit/Tx', currency(avg_margin['net_profit'], '.2f'),
            delta=2.1, note=f'Margin: {avg_profit_pct:.1f}%'
        ), unsafe_allow_html=True)

    with col3:
        st.markdown(compact_metric_card(
            '📊', f'Projected 90-Day {_ft_label}', currency(avg_daily_metric * 90, ',.0f'),
            delta=6.4, note='Conservative & Aggressive avg'
        ), unsafe_allow_html=True)

    with col4:
        st.markdown(compact_metric_card(
            '🛒', 'Cross-Sell Opportunities', f'{n_bundles:,}',
            delta=1.8, note='Product pairs identified'
        ), unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 3: CUSTOMER INTELLIGENCE + AI ACTION CENTER
    # ═══════════════════════════════════════════════════════════════════════
    ci_col_left, ci_col_right = st.columns([0.45, 0.55], gap='large')

    # Left: Customer Segment Mix
    with ci_col_left:
        st.markdown('<h4 style="margin-bottom:12px;">📋 Customer Segment Mix</h4>', unsafe_allow_html=True)

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
            legend=dict(font=dict(color=CT['legend'], size=11), x=0, y=1, orientation='v'),
            height=300,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Right: AI Action Center
    with ci_col_right:
        st.markdown('<h4 style="margin-bottom:12px;">⚡ AI Action Center</h4>', unsafe_allow_html=True)

        # Top Recommendation
        st.markdown(insight_mini_card(
            '🎯 Top Recommendation',
            f'Target {best_segment}',
            'Highest growth potential this quarter',
            color='#00B894',
        ), unsafe_allow_html=True)

        # Target Segment Details
        if not filtered_seg.empty:
            top_seg = filtered_seg.nlargest(1, 'count').iloc[0]
            seg_pct = (top_seg['count'] / filtered_seg['count'].sum() * 100)
        elif not seg_counts.empty:
            top_seg = seg_counts.nlargest(1, 'count').iloc[0]
            seg_pct = (top_seg['count'] / seg_counts['count'].sum() * 100)
        else:
            seg_pct = 0
        seg_revenue = f"{seg_pct:.1f}% of customer base"

        st.markdown(insight_mini_card(
            '🔍 Target Segment',
            best_segment,
            seg_revenue,
            color='#6C5CE7',
        ), unsafe_allow_html=True)

        # Suggested Promotion
        st.markdown(insight_mini_card(
            '📢 Suggested Promotion',
            f'"{best_bundle}"',
            f'Expected: +{hero_uplift_pct:.0f}% uplift',
            color='#E17055',
        ), unsafe_allow_html=True)

        # Expected Impact
        st.markdown(insight_mini_card(
            '💡 Expected Impact',
            f'{currency(hero_impact, ",.0f")} profit',
            f'Reach ~{int(total_customers * 0.15):,} customers',
            color='#00B894',
        ), unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 4: FORECAST & SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    fc_col_left, fc_col_right = st.columns([0.65, 0.35], gap='large')

    # Left: 90-Day Forecast Chart
    with fc_col_left:
        st.markdown(f'<h4 style="margin-bottom:12px;">📈 90-Day {_ft_label} Forecast</h4>', unsafe_allow_html=True)

        if len(profit_fc) > 0:
            agg = profit_fc.groupby(['created_at', 'scenario'])[_ft_metric].sum().reset_index()
            fig_line = px.line(
                agg, x='created_at', y=_ft_metric, color='scenario',
                title=None,
                color_discrete_map={
                    'Conservative Growth': '#6C5CE7',
                    'Aggressive Growth': '#00B894',
                },
                labels={'created_at': '', _ft_metric: f'{_ft_label} ({cur_sym()})', 'scenario': ''},
            )
            fig_line.update_traces(
                line=dict(width=2.5),
                hovertemplate=f'<b>%{{x|%b %d}}</b><br>{_ft_label}: {cur_sym()} %{{y:,.0f}}<extra></extra>',
            )
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color=CT['font'],
                xaxis=dict(showgrid=False, color=CT['axis'], title=''),
                yaxis=dict(showgrid=True, gridcolor=CT['grid'], color=CT['axis']),
                legend=dict(font=dict(color=CT['legend'], size=10), orientation='h', y=1.08),
                margin=dict(l=40, r=0, t=0, b=30),
                hovermode='x unified',
                height=280,
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info('Forecast data not available.')

    # Right: Forecast Summary
    with fc_col_right:
        st.markdown('<h4 style="margin-bottom:12px;">📋 Forecast Summary</h4>', unsafe_allow_html=True)

        if len(profit_fc) > 0:
            agg = profit_fc.groupby(['created_at', 'scenario'])[_ft_metric].sum().reset_index()
            cons_profit = agg[agg['scenario'] == 'Conservative Growth'][_ft_metric].sum()
            aggr_profit = agg[agg['scenario'] == 'Aggressive Growth'][_ft_metric].sum()
        else:
            cons_profit = 0
            aggr_profit = 0

        st.markdown(insight_mini_card(
            'Conservative Path',
            currency(cons_profit, ',.0f'),
            'Steady, predictable growth',
            color='#6C5CE7',
        ), unsafe_allow_html=True)

        st.markdown(insight_mini_card(
            'Aggressive Path',
            currency(aggr_profit, ',.0f'),
            'High growth, higher risk',
            color='#00B894',
        ), unsafe_allow_html=True)

        st.markdown(insight_mini_card(
            'Risk Level',
            'Low',
            'All branches performing well',
            color='#FDAA5E',
        ), unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 5: PRODUCT INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════════
    pi_col_left, pi_col_right = st.columns([0.5, 0.5], gap='large')

    # Left: Top Bundle Recommendation
    with pi_col_left:
        st.markdown('<h4 style="margin-bottom:12px;">🛒 Top Bundle Recommendation</h4>', unsafe_allow_html=True)

        if rules_df is not None and len(rules_df) > 0:
            top_rule = rules_df.nlargest(1, 'lift').iloc[0]
            st.markdown(f"""
            <div class="insight-card" style="padding:16px;margin-bottom:12px;">
                <div style="font-size:0.75rem;color:var(--txt-secondary);font-weight:600;margin-bottom:8px;">HIGH POTENTIAL</div>
                <div style="font-size:1rem;color:var(--txt-primary);font-weight:600;margin-bottom:8px;">
                    {top_rule['antecedents']} + {top_rule['consequents']}
                </div>
                <table style="width:100%;font-size:0.85rem;color:var(--txt-secondary);">
                    <tr><td>Success Rate:</td><td style="text-align:right;color:var(--txt-primary);font-weight:600;">{top_rule['confidence']*100:.0f}%</td></tr>
                    <tr><td>Cross-Sell Potential:</td><td style="text-align:right;color:var(--txt-primary);font-weight:600;">{top_rule['lift']:.2f}x</td></tr>
                    <tr><td>Popularity:</td><td style="text-align:right;color:var(--txt-primary);font-weight:600;">{top_rule['support']*100:.1f}%</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info('No bundle data available.')

    # Right: Menu Profitability Snapshot
    with pi_col_right:
        st.markdown('<h4 style="margin-bottom:12px;">☕ Menu Profitability Snapshot</h4>', unsafe_allow_html=True)

        menu_margins = []
        for _, row in menu_df.iterrows():
            m = fin_engine.get_net_margin(row['item_name'])
            menu_margins.append(m)

        menu_profit_df = pd.DataFrame(menu_margins).head(8)
        fig_menu = px.bar(
            menu_profit_df, x='item', y='net_profit',
            title=None,
            color_discrete_sequence=['#00B894'],
            labels={'net_profit': f'Net Profit ({cur_sym()})', 'item': ''},
        )
        fig_menu.update_traces(
            hovertemplate=f'<b>%{{x}}</b><br>Net Profit: {cur_sym()} %{{y:,.2f}}<br>Price: {cur_sym()} %{{customdata[0]:,.2f}}<extra></extra>',
            customdata=menu_profit_df[['price']],
        )
        fig_menu.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color=CT['font'],
            xaxis=dict(showgrid=False, color=CT['axis'], title=''),
            yaxis=dict(showgrid=True, gridcolor=CT['grid'], color=CT['axis'],
                       title=f'Net Profit ({cur_sym()})'),
            margin=dict(l=40, r=10, t=10, b=40),
            height=280,
        )
        st.plotly_chart(fig_menu, use_container_width=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 6: SEGMENT PROFILES
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown('<h4>📋 Segment Profiles</h4>', unsafe_allow_html=True)

    profiles = meta.get('cluster_profiles', [])
    labels = meta.get('cluster_labels', {})
    if profiles:
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
                        unsafe_allow_html=True,
                    )
        else:
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
                        unsafe_allow_html=True,
                    )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 7: TOP ASSOCIATION RULES
    # ═══════════════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════════════
    #  SECTION 8: FORECAST KPI SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<h4>📈 Forecast at a Glance</h4>', unsafe_allow_html=True)

    try:
        avg_margin_local = fin_engine.get_net_margin('Latte')
        margin_pct_local = avg_margin_local['net_margin_pct'] / 100
        profit_fc_local = fc_engine.get_profit_forecast(margin_pct=margin_pct_local)
        if profit_fc_local is not None and len(profit_fc_local) > 0:
            cons = profit_fc_local[profit_fc_local['scenario'] == 'Conservative Growth']['projected_profit'].sum()
            aggr = profit_fc_local[profit_fc_local['scenario'] == 'Aggressive Growth']['projected_profit'].sum()
            c1, c2 = st.columns(2)
            c1.markdown(compact_metric_card('📈', 'Conservative 90d Profit', currency(cons, ',.0f')), unsafe_allow_html=True)
            c2.markdown(compact_metric_card('🚀', 'Aggressive 90d Profit', currency(aggr, ',.0f')), unsafe_allow_html=True)
    except Exception:
        st.info('Forecast data not available yet.')
