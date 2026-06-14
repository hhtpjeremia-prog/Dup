"""
Strategic Explorer page — scenario planning with interactive sliders.
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


def render_explorer(context: dict) -> None:
    """🔬 Strategic Explorer — scenario planning with interactive sliders."""
    fin_engine: FinancialEngine = context['fin_engine']
    fc_engine: ForecastEngine = context['fc_engine']
    meta: dict = context['meta']
    seg_counts: pd.DataFrame = context['seg_counts']
    rules_df: pd.DataFrame = context['rules_df']
    menu_df: pd.DataFrame = context['menu_df']
    is_member: bool = context['is_member']

    CT = chart_theme()

    # ── Title ────────────────────────────────────────────────────────────────
    st.markdown('<h2>🔬 Strategic Explorer</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#888;margin-bottom:16px;">'
        'Adjust strategy levers and see how your profit and inventory turnover '
        'would change. This is a <strong>cause-and-effect simulator</strong> — '
        'not a crystal ball.</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 1: STRATEGY LEVERS (3 sliders)
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<h4>🎛️ Strategy Levers</h4>', unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        price_adj = st.slider(
            'Price Adjustment',
            -20, 20, 0, 1,
            format='%d%%',
            help='Increase or decrease menu prices across the board',
        ) / 100.0

    with col_s2:
        stock_adj = st.slider(
            'Stock Levels',
            -50, 50, 0, 5,
            format='%d%%',
            help='Adjust inventory availability (affects stock turnover)',
        ) / 100.0

    with col_s3:
        discount_intensity = st.slider(
            'Discount Intensity',
            0, 40, 0, 5,
            format='%d%%',
            help='How aggressively to offer discounts and promotions',
        ) / 100.0

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 2: SCENARIO IMPACT ANALYSIS (4 metric cards)
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<h4>📊 Scenario Impact Analysis</h4>', unsafe_allow_html=True)

    # ── Base values from financial engine ──────────────────────────────────
    base_margin = fin_engine.get_net_margin('Latte')
    base_price = base_margin['price']
    base_net = base_margin['net_profit']

    # ── Hardcoded assumptions ──────────────────────────────────────────────
    ELASTICITY = -0.5
    base_transactions = 2000  # Approximate daily avg per branch

    # Volume impact from price elasticity
    volume_impact = 1 + (price_adj * ELASTICITY)

    # New price & net margin per transaction
    new_price = base_price * (1 + price_adj)
    new_cogs = base_margin['cogs']
    new_op_cost = base_margin['operating_cost']
    new_discount = base_price * discount_intensity
    new_net = new_price - new_cogs - new_op_cost - new_discount

    # Stock & discount volume boosts
    stock_sales_boost = stock_adj * 0.3          # 30% pass-through
    discount_volume_boost = discount_intensity * 1.2  # 120% pass-through

    # Net volume factor combining all three levers
    total_volume_factor = volume_impact * (1 + stock_sales_boost) * (1 + discount_volume_boost)

    # ── Render 4 metric cards ──────────────────────────────────────────────
    res1, res2, res3, res4 = st.columns(4)

    price_change_pct = price_adj * 100

    with res1:
        st.markdown(
            compact_metric_card(
                '💰', 'Price Change',
                f'{price_change_pct:+.0f}%',
                note=f'Base: {currency(base_price, ",.0f")} → {currency(new_price, ",.0f")}',
            ),
            unsafe_allow_html=True,
        )

    with res2:
        net_change = new_net - base_net
        net_change_pct = (net_change / base_net * 100) if base_net > 0 else 0
        st.markdown(
            compact_metric_card(
                '📊', 'Profit per Transaction',
                currency(new_net, ',.2f'),
                delta=net_change_pct,
            ),
            unsafe_allow_html=True,
        )

    with res3:
        vol_change_pct = (total_volume_factor - 1) * 100
        st.markdown(
            compact_metric_card(
                '📈', 'Transaction Volume',
                f'{vol_change_pct:+.1f}%',
                note='Estimated change in daily transactions',
            ),
            unsafe_allow_html=True,
        )

    with res4:
        new_total_per_unit = new_net
        base_total_per_unit = base_net
        total_profit_change = (
            (new_total_per_unit * total_volume_factor - base_total_per_unit)
            / base_total_per_unit * 100
            if base_total_per_unit > 0 else 0
        )
        st.markdown(
            compact_metric_card(
                '🎯', 'Overall Profit Impact',
                f'{total_profit_change:+.1f}%',
                note='Net effect of all strategy changes',
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 3: CAUSE & EFFECT WATERFALL CHART
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<h4>🔄 Cause & Effect Breakdown</h4>', unsafe_allow_html=True)

    base_total = 100.0  # Indexed baseline
    price_effect = price_adj * 100 * 0.6                     # ~60% pass-through
    volume_effect_elasticity = (volume_impact - 1) * 100      # pure elasticity
    stock_effect = stock_sales_boost * 100                    # stock contribution
    discount_margin_effect = -discount_intensity * 100 * 0.8  # discount erodes margin

    waterfall = go.Figure(go.Waterfall(
        name='Impact',
        orientation='v',
        measure=['relative', 'relative', 'relative', 'relative', 'total'],
        x=[
            'Price Change',
            'Volume Elasticity',
            'Stock Availability',
            'Discount Strategy',
            'Net Impact',
        ],
        y=[
            price_effect,
            volume_effect_elasticity,
            stock_effect,
            discount_margin_effect,
            base_total + price_effect + volume_effect_elasticity
            + stock_effect + discount_margin_effect,
        ],
        text=[
            f'{price_effect:+.1f}%',
            f'{volume_effect_elasticity:+.1f}%',
            f'{stock_effect:+.1f}%',
            f'{discount_margin_effect:+.1f}%',
            f'{base_total + price_effect + volume_effect_elasticity + stock_effect + discount_margin_effect:.1f}%',
        ],
        textposition='outside',
        connector={'line': {'color': CT['grid'], 'width': 1}},
        decreasing={'marker': {'color': '#E17055'}},
        increasing={'marker': {'color': '#00B894'}},
        totals={'marker': {'color': '#6C5CE7'}},
    ))
    waterfall.update_layout(
        title='How Each Lever Affects Overall Profit (Indexed to 100%)',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=CT['font'],
        xaxis=dict(showgrid=False, color=CT['axis']),
        yaxis=dict(
            showgrid=True, gridcolor=CT['grid'], color=CT['axis'],
            title='Profit Impact (%)',
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        height=450,
        showlegend=False,
    )
    st.plotly_chart(waterfall, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 4: PRICE-DISCOUNT SENSITIVITY MATRIX (heatmap)
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<h4>📈 Price-Discount Sensitivity Matrix</h4>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#888;margin-bottom:12px;">'
        'See how different price & discount combinations affect total profit. '
        'Darker green = higher profit.</div>',
        unsafe_allow_html=True,
    )

    price_range = np.arange(-0.20, 0.21, 0.05)
    discount_range = np.arange(0, 0.41, 0.05)

    sensitivity = np.zeros((len(discount_range), len(price_range)))

    for i, d in enumerate(discount_range):
        for j, p in enumerate(price_range):
            vol = 1 + (p * ELASTICITY) * (1 + d * 1.2)
            np_ = base_price * (1 + p)
            nd = base_price * d
            np_net = np_ - base_margin['cogs'] - base_margin['operating_cost'] - nd
            total_idx = (np_net * vol) / base_net * 100 if base_net > 0 else 0
            sensitivity[i, j] = total_idx

    fig_heat = px.imshow(
        sensitivity,
        x=[f'{p*100:.0f}%' for p in price_range],
        y=[f'{d*100:.0f}%' for d in discount_range],
        color_continuous_scale='RdYlGn',
        labels={
            'x': 'Price Adjustment',
            'y': 'Discount Intensity',
            'color': 'Profit Index',
        },
        title='Total Profit Index (100 = baseline)',
        aspect='auto',
        text_auto='.0f',
    )
    fig_heat.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=CT['font'],
        xaxis=dict(color=CT['axis']),
        yaxis=dict(color=CT['axis']),
        coloraxis_colorbar=dict(
            tickfont=dict(color=CT['font']),
            title_font=dict(color=CT['font']),
        ),
        margin=dict(l=40, r=40, t=50, b=40),
        height=400,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 5: STRATEGY INSIGHT
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<h4>💡 Strategy Insight</h4>', unsafe_allow_html=True)

    if total_profit_change > 10:
        verdict = '🟢 Strong positive impact'
        detail = (
            'Your current strategy settings show significant profit potential. '
            'Consider piloting these changes in high-traffic branches first.'
        )
    elif total_profit_change > 2:
        verdict = '🔵 Moderate improvement'
        detail = (
            'These adjustments show modest profit gains. '
            'Fine-tune individual levers to optimize further.'
        )
    elif total_profit_change > -2:
        verdict = '⚪ Neutral impact'
        detail = (
            'The combined effect is near baseline. '
            'Try more aggressive adjustments or focus on specific bundles.'
        )
    elif total_profit_change > -10:
        verdict = '🟡 Caution — negative impact'
        detail = (
            'Current settings reduce profitability. '
            'Consider reducing discounts or adjusting prices more conservatively.'
        )
    else:
        verdict = '🔴 Significant risk'
        detail = (
            'These settings would substantially reduce profit. '
            'Revisit your assumptions and try more moderate adjustments.'
        )

    st.markdown(f"""
    <div class="insight-card">
        <h4>{verdict}</h4>
        <div style="color:#E0E0E0;font-size:1rem;">{detail}</div>
        <div class="sub" style="margin-top:8px;">
            Price: {price_adj*100:+.0f}% · Stock: {stock_adj*100:+.0f}% ·
            Discount: {discount_intensity*100:.0f}% ·
            Est. profit impact: {total_profit_change:+.1f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 6: SAVE SCENARIO
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<br>', unsafe_allow_html=True)
    if st.button('💾 Save This Scenario'):
        st.session_state.scenario_params = {
            'price_adj': price_adj,
            'stock_level': stock_adj,
            'discount_intensity': discount_intensity,
        }
        st.success('Scenario saved! Switch between tabs to compare.')
