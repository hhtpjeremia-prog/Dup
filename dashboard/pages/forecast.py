"""
Forecast & Profit page — executive dashboard with fullscreen mode,
KPI row, combined historical + forecast chart, insight cards,
branch-level table, and bundle-impact overlay.
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
from components import (
    compact_metric_card, metric_card_three_row, insight_mini_card,
    get_filtered_profit_fc, aggregate_forecast_by_date,
)
from loaders import load_historical_daily
from engines import FinancialEngine, ForecastEngine


def render_forecast(context: dict) -> None:
    """📈 Forecast & Profit — Executive dashboard with smooth trends & confidence bands."""
    fin_engine: FinancialEngine = context['fin_engine']
    fc_engine: ForecastEngine = context['fc_engine']
    meta: dict = context['meta']
    seg_counts: pd.DataFrame = context['seg_counts']
    rules_df: pd.DataFrame = context['rules_df']
    menu_df: pd.DataFrame = context['menu_df']
    is_member: bool = context['is_member']

    CT = chart_theme()

    # ── Lens-aware metric ──────────────────────────────────────────────────
    _rev_ft = st.session_state.get('dashboard_lens', 'Profit') == 'Revenue'
    _ft_label = 'Revenue' if _rev_ft else 'Profit'
    _ft_metric = 'projected_revenue' if _rev_ft else 'projected_profit'

    # ── Fullscreen toggle ──────────────────────────────────────────────────
    fs = st.session_state.get('forecast_fullscreen', False)

    col_hdr, col_btn = st.columns([4, 1])
    with col_hdr:
        if fs:
            st.markdown(
                f'<h2>📈 Historical & {_ft_label} Forecast Overview</h2>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<h2>📈 {_ft_label} Forecast — Executive Dashboard</h2>',
                unsafe_allow_html=True,
            )
    with col_btn:
        btn_label = '⛶ Exit Fullscreen' if fs else '⛶ Fullscreen'
        if st.button(btn_label, key='fs_toggle_btn', use_container_width=True):
            st.session_state.forecast_fullscreen = not fs
            st.rerun()

    # ── Common: compute profit forecast ────────────────────────────────────
    avg_margin = fin_engine.get_net_margin('Latte')
    margin_pct = avg_margin['net_margin_pct'] / 100
    profit_fc = get_filtered_profit_fc(fc_engine, margin_pct=margin_pct)

    # ═══════════════════════════════════════════════════════════════════════
    #  FULLSCREEN MODE — Combined Historical + Forecast
    # ═══════════════════════════════════════════════════════════════════════
    if fs:
        _render_fullscreen(profit_fc, fc_engine, margin_pct, CT,
                           _ft_metric, _ft_label, _rev_ft)
        return

    # ═══════════════════════════════════════════════════════════════════════
    #  NORMAL VIEW — Executive Forecast Dashboard
    # ═══════════════════════════════════════════════════════════════════════

    # Aggregate forecast by date using shared component
    agg_forecast = aggregate_forecast_by_date(profit_fc, metric=_ft_metric)

    # ── KPI Row (4 cards) ─────────────────────────────────────────────────
    try:
        _render_kpi_row(profit_fc, agg_forecast, _ft_metric, _ft_label)
    except Exception:
        pass

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── 67/33 Layout: Chart (left) + Insight Cards (right) ────────────────
    col_chart, col_insight = st.columns([0.67, 0.33], gap='medium')

    with col_chart:
        _render_forecast_chart(profit_fc, agg_forecast, margin_pct, CT,
                               _ft_metric, _ft_label, _rev_ft)

    with col_insight:
        _render_insight_cards(agg_forecast, CT, _ft_label)

    # ── Branch-Level Forecast Table ───────────────────────────────────────
    st.markdown(
        '<hr style="margin:24px 0;border-color:var(--border);">',
        unsafe_allow_html=True,
    )
    st.markdown('<h4>📍 Branch-Level Forecast (90 Days)</h4>', unsafe_allow_html=True)

    branch_agg = profit_fc.groupby('branch')[_ft_metric].sum().reset_index() \
                           .sort_values(_ft_metric, ascending=False)

    _sym = cur_sym()
    branch_display = branch_agg[['branch', _ft_metric]].copy()
    branch_display.columns = ['Branch', f'{_ft_label} ({_sym})']
    branch_display[f'{_ft_label} ({_sym})'] = branch_display[f'{_ft_label} ({_sym})'] \
        .apply(lambda x: currency(x, ',.0f'))

    st.dataframe(branch_display, hide_index=True, use_container_width=True)

    # ── Selected bundle impact (if any) ────────────────────────────────────
    if st.session_state.get('selected_bundle'):
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(
            f'<h4>📦 Bundle Impact: {st.session_state.selected_bundle}</h4>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="color:#888;">Switch to <strong>Bundle Intelligence</strong> '
            'tab to explore bundle details, or click a different bundle below:</div>',
            unsafe_allow_html=True,
        )

        col_clear, _ = st.columns([1, 3])
        with col_clear:
            if st.button('🔄 Clear Bundle Selection', use_container_width=True):
                st.session_state.selected_bundle = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  SUB-COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════


def _render_fullscreen(
    profit_fc: pd.DataFrame,
    fc_engine: ForecastEngine,
    margin_pct: float,
    CT: dict,
    _ft_metric: str,
    _ft_label: str,
    _rev_ft: bool,
) -> None:
    """Fullscreen combined historical + forecast view."""
    hist = load_historical_daily()
    hist['projected_revenue'] = hist['total_transactions'] * fc_engine.avg_transaction_value
    hist['projected_profit'] = hist['projected_revenue'] * margin_pct

    # ── Controls row ──
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    branches = sorted(hist['city'].unique())
    date_min = hist['date'].min().date()
    date_max = max(
        hist['date'].max().date(),
        profit_fc['created_at'].max().date(),
    )

    with col_ctrl1:
        sel_branches = st.session_state.get('branch_filter', [])
        if not sel_branches:
            sel_branches = branches
        dr = st.date_input(
            'Time Period',
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max,
            key='fs_daterange',
        )
        if isinstance(dr, tuple) and len(dr) == 2:
            dr_start, dr_end = dr
        else:
            dr_start, dr_end = date_min, date_max

    with col_ctrl2:
        st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)

    with col_ctrl3:
        st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
        if st.button('🔄 Reset View', key='fs_reset', use_container_width=True):
            if 'fs_daterange' in st.session_state:
                del st.session_state['fs_daterange']
            st.rerun()

    # ── Filter data ──
    hist_f = hist[
        (hist['city'].isin(sel_branches))
        & (hist['date'] >= pd.Timestamp(dr_start))
        & (hist['date'] <= pd.Timestamp(dr_end))
    ].copy()

    fc_f = profit_fc[
        (profit_fc['branch'].isin(sel_branches))
        & (profit_fc['created_at'] >= pd.Timestamp(dr_start))
        & (profit_fc['created_at'] <= pd.Timestamp(dr_end))
    ].copy()

    # Aggregate across selected branches
    hist_agg = hist_f.groupby('date', as_index=False)[_ft_metric].sum()
    fc_agg = fc_f.groupby(['created_at', 'scenario'], as_index=False)[_ft_metric].sum()

    # ── Build combined chart ──
    fig_fs = go.Figure()

    # Historical trace
    fig_fs.add_trace(go.Scatter(
        x=hist_agg['date'],
        y=hist_agg[_ft_metric],
        mode='lines',
        name='Historical',
        line=dict(color='#888', width=1.5),
        hovertemplate=f'<b>%{{x|%b %Y}}</b><br>{_ft_label}: {cur_sym()} %{{y:,.0f}}<br>',
    ))

    # Forecast traces (with confidence bands)
    for scenario in ['Conservative Growth', 'Aggressive Growth']:
        sdata = fc_agg[fc_agg['scenario'] == scenario]
        color = '#6C5CE7' if scenario == 'Conservative Growth' else '#00B894'
        band_pct = 0.05 if 'Conservative' in scenario else 0.08

        fig_fs.add_trace(go.Scatter(
            x=sdata['created_at'],
            y=sdata[_ft_metric],
            mode='lines',
            name=scenario,
            line=dict(color=color, width=2.5),
            hovertemplate=f'<b>%{{x|%b %d}}</b><br>{_ft_label}: {cur_sym()} %{{y:,.0f}}<br>',
        ))

        # Confidence band
        upper = sdata[_ft_metric] * (1 + band_pct)
        lower = sdata[_ft_metric] * (1 - band_pct)
        fig_fs.add_trace(go.Scatter(
            x=pd.concat([sdata['created_at'], sdata['created_at'][::-1]]),
            y=pd.concat([upper, lower[::-1]]),
            fill='toself',
            fillcolor=hex_to_rgba(color, 0.12),
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip',
        ))

    # Forecast start marker
    fc_start = profit_fc['created_at'].min()
    fig_fs.add_shape(
        type='line',
        x0=fc_start, x1=fc_start,
        y0=0, y1=1, yref='paper',
        line=dict(dash='dash', color='#E17055', width=1.5),
    )
    fig_fs.add_annotation(
        x=fc_start, y=1, yref='paper',
        text='Forecast Start',
        showarrow=False,
        font=dict(color='#E17055', size=12),
        yshift=10,
    )

    fig_fs.update_layout(
        title=f'{_ft_label} Overview — {", ".join(sel_branches[:3])}'
              f'{" +" if len(sel_branches) > 3 else ""}',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=CT['font'],
        xaxis=dict(showgrid=False, color=CT['axis'], title=''),
        yaxis=dict(showgrid=True, gridcolor=CT['grid'], color=CT['axis'],
                  title=f'Daily {_ft_label} ({cur_sym()})'),
        legend=dict(
            font=dict(color=CT['legend']),
            orientation='h', y=-0.12, yanchor='top', x=0.5, xanchor='center',
        ),
        margin=dict(l=40, r=20, t=70, b=80),
        hovermode='x unified',
        height=600,
    )
    st.plotly_chart(fig_fs, use_container_width=True)

    # ── Summary metrics below chart ──
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        total_hist = hist_agg[_ft_metric].sum()
        st.markdown(
            f"""
            <div class="insight-card">
                <h4>Historical {_ft_label}</h4>
                <div class="value" style="color:#888;">{currency(total_hist, ',.0f')}</div>
                <div class="sub">{hist_f['date'].nunique():,} days · {len(sel_branches)} branch(es)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_s2:
        cons_fs = fc_agg[fc_agg['scenario'] == 'Conservative Growth'][_ft_metric].sum()
        st.markdown(
            f"""
            <div class="insight-card">
                <h4>Conservative Growth</h4>
                <div class="value" style="color:#6C5CE7;">{currency(cons_fs, ',.0f')}</div>
                <div class="sub">Stable 90-day projection</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_s3:
        aggr_fs = fc_agg[fc_agg['scenario'] == 'Aggressive Growth'][_ft_metric].sum()
        st.markdown(
            f"""
            <div class="insight-card">
                <h4>Aggressive Growth</h4>
                <div class="value" style="color:#00B894;">{currency(aggr_fs, ',.0f')}</div>
                <div class="sub">Higher upside 90-day projection</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="text-align:center;color:#555;margin-top:12px;">'
        f'Showing <strong>{hist_f["city"].nunique()}</strong> branch(es) — '
        f'{dr_start} to {dr_end} · '
        'Use filters above to narrow scope'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_kpi_row(
    profit_fc: pd.DataFrame,
    agg_forecast: pd.DataFrame,
    _ft_metric: str,
    _ft_label: str,
) -> None:
    """Render the 4-card KPI row for the normal view."""
    today = pd.Timestamp.now().normalize()
    horizon_end = today + pd.Timedelta(days=89)

    fc_daily = profit_fc.copy()
    fc_daily['created_at'] = pd.to_datetime(fc_daily['created_at']).dt.normalize()

    fc_90 = fc_daily[
        (fc_daily['created_at'] >= today) & (fc_daily['created_at'] <= horizon_end)
    ]
    total_90d_forecast = fc_90.groupby('created_at')[_ft_metric].sum().sum()
    if total_90d_forecast == 0 and not agg_forecast.empty:
        total_90d_forecast = agg_forecast['midpoint'].head(90).sum()

    if len(fc_90) > 0:
        daily_avg_forecast = fc_90.groupby('created_at')[_ft_metric].sum().mean()
    else:
        daily_avg_forecast = agg_forecast['midpoint'].head(90).mean() \
            if not agg_forecast.empty else 0

    branch_totals = profit_fc.groupby('branch')[_ft_metric].sum().sort_values(ascending=False)
    best_branch = branch_totals.index[0] if len(branch_totals) > 0 else 'N/A'
    best_branch_value = branch_totals.iloc[0] if len(branch_totals) > 0 else 0

    branch_totals_asc = profit_fc.groupby('branch')[_ft_metric].sum().sort_values(ascending=True)
    lowest_branch = branch_totals_asc.index[0] if len(branch_totals_asc) > 0 else 'N/A'
    lowest_branch_value = branch_totals_asc.iloc[0] if len(branch_totals_asc) > 0 else 0

    c1, c2, c3, c4 = st.columns(4, gap='small')
    c1.markdown(
        compact_metric_card(
            '💰', f'Forecast {_ft_label} (90 Days)', currency(total_90d_forecast, ',.0f'),
        ),
        unsafe_allow_html=True,
    )
    c2.markdown(
        compact_metric_card(
            '📈', f'Daily Average {_ft_label}', currency(daily_avg_forecast, ',.0f'),
            note='avg per day (next 90d)',
        ),
        unsafe_allow_html=True,
    )
    c3.markdown(
        compact_metric_card(
            '🏆', 'Best Performing Branch', best_branch,
            note=currency(best_branch_value, ',.0f'),
        ),
        unsafe_allow_html=True,
    )
    c4.markdown(
        compact_metric_card(
            '📉', 'Lowest Performing Branch', lowest_branch,
            note=currency(lowest_branch_value, ',.0f'),
        ),
        unsafe_allow_html=True,
    )


def _render_forecast_chart(
    profit_fc: pd.DataFrame,
    agg_forecast: pd.DataFrame,
    margin_pct: float,
    CT: dict,
    _ft_metric: str,
    _ft_label: str,
    _rev_ft: bool,
) -> None:
    """Combined historical + forecast chart for the normal view."""
    fig_fc = go.Figure()

    # Historical series
    try:
        hist = load_historical_daily()
        branch_sel = st.session_state.get('branch_filter', [])
        if branch_sel:
            hist = hist[hist['city'].isin(branch_sel)]

        hist_agg = hist.groupby('date', as_index=False)['total_revenue'].sum()

        if _rev_ft:
            hist_x = hist_agg['date']
            hist_y = hist_agg['total_revenue']
            hover_label = 'Historical Revenue'
        else:
            hist_agg['profit'] = hist_agg['total_revenue'] * margin_pct
            hist_x = hist_agg['date']
            hist_y = hist_agg['profit']
            hover_label = 'Historical Profit'

        fig_fc.add_trace(go.Scatter(
            x=hist_x,
            y=hist_y,
            mode='lines',
            name='Historical',
            line=dict(color='#888888', width=2),
            hovertemplate=(
                f'<b>%{{x|%b %d, %Y}}</b><br>{hover_label}: '
                f'{cur_sym()}%{{y:,.0f}}<extra></extra>'
            ),
        ))
    except Exception:
        pass

    # Forecast midpoint (smoothed)
    fig_fc.add_trace(go.Scatter(
        x=agg_forecast['date'],
        y=agg_forecast['midpoint_smooth'],
        mode='lines',
        name='Forecast',
        line=dict(color='#00B894', width=3, dash='dash'),
        hovertemplate=(
            f'<b>%{{x|%b %d, %Y}}</b><br>Forecast {_ft_label}: '
            f'{cur_sym()}%{{y:,.0f}}<extra></extra>'
        ),
    ))

    # Confidence interval band
    try:
        upper = agg_forecast['aggressive_smooth']
        lower = agg_forecast['conservative_smooth']
        fig_fc.add_trace(go.Scatter(
            x=pd.concat([agg_forecast['date'], agg_forecast['date'][::-1]]),
            y=pd.concat([upper, lower[::-1]]),
            fill='toself',
            fillcolor=hex_to_rgba('#00B894', 0.12),
            line=dict(width=0),
            hoverinfo='skip',
            showlegend=False,
        ))
    except Exception:
        pass

    fig_fc.update_layout(
        title=f'{_ft_label} — Historical vs Forecast (90 days)',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=CT['font'],
        xaxis=dict(showgrid=False, color=CT['axis'], title='Date'),
        yaxis=dict(showgrid=True, gridcolor=CT['grid'], color=CT['axis'],
                  title=f'Daily {_ft_label} ({cur_sym()})'),
        legend=dict(
            orientation='h', y=1.02, x=0.01, font=dict(color=CT['legend']),
        ),
        margin=dict(l=40, r=10, t=60, b=40),
        hovermode='x unified',
        height=560,
    )
    st.plotly_chart(fig_fc, use_container_width=True)


def _render_insight_cards(
    agg_forecast: pd.DataFrame,
    CT: dict,
    _ft_label: str,
) -> None:
    """Right-column insight cards: trend, peak, risk, recommended action."""
    # Trend outlook
    try:
        first_avg = agg_forecast['midpoint'].head(14).mean()
        last_avg = agg_forecast['midpoint'].tail(14).mean()
        growth_pct_14 = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
    except Exception:
        growth_pct_14 = 0

    if growth_pct_14 > 10:
        trend_label = 'Strong Growth'
        trend_color = '#00B894'
    elif growth_pct_14 > 2:
        trend_label = 'Moderate Growth'
        trend_color = '#6C5CE7'
    elif growth_pct_14 < -5:
        trend_label = 'Declining Trend'
        trend_color = '#E17055'
    else:
        trend_label = 'Stable Outlook'
        trend_color = '#FDAA5E'

    # Peak forecast period
    try:
        peak_row = agg_forecast.loc[agg_forecast['midpoint'].idxmax()]
        peak_date = pd.to_datetime(peak_row['date'])
        peak_week = ((peak_date - agg_forecast['date'].min()).days // 7) + 1
        peak_label = f'Week {peak_week} · {peak_date.strftime("%b %Y")}'
    except Exception:
        peak_label = 'N/A'

    # Risk alert
    try:
        avg_range = (agg_forecast['aggressive'] - agg_forecast['conservative']).mean()
        avg_val = agg_forecast['midpoint'].mean()
        conf_pct = 100 - min((avg_range / avg_val * 100) if avg_val > 0 else 0, 100)
    except Exception:
        conf_pct = 100

    risk_msg = ''
    if conf_pct < 60:
        risk_msg = 'Increased uncertainty in final forecast horizon'
    else:
        try:
            mid = len(agg_forecast) // 2
            prev_avg = agg_forecast['midpoint'].iloc[max(0, mid - 14):mid].mean()
            recent_avg = agg_forecast['midpoint'].iloc[mid:mid + 14].mean()
            risk_msg = 'Growth slows in the mid-horizon' if recent_avg < prev_avg else 'No immediate volatility detected'
        except Exception:
            risk_msg = 'No immediate volatility detected'

    # Recommended action
    if 'Strong' in trend_label:
        action = 'Increase marketing & inventory to capture upside'
    elif 'Moderate' in trend_label:
        action = 'Scale inventory; monitor campaigns closely'
    elif 'Declining' in trend_label:
        action = 'Launch targeted promotions and cost controls'
    else:
        action = 'Focus on margin optimization and retention'

    # Render insight cards
    st.markdown(
        insight_mini_card('Trend Outlook', trend_label,
                         f'{growth_pct_14:.1f}% vs start', color=trend_color),
        unsafe_allow_html=True,
    )
    st.markdown(
        insight_mini_card('Peak Forecast Period', peak_label,
                         'Highest projected daily profit', color='#6C5CE7'),
        unsafe_allow_html=True,
    )
    st.markdown(
        insight_mini_card('Risk Alert', risk_msg,
                         f'Confidence: {conf_pct:.0f}%',
                         color='#E17055' if conf_pct < 60 else '#FDAA5E'),
        unsafe_allow_html=True,
    )
    st.markdown(
        insight_mini_card('Recommended Action', action,
                         'Decision-support suggestion', color='#00B894'),
        unsafe_allow_html=True,
    )
