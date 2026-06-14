"""
Reusable UI components — metric cards, sidebar sections, and forecast helpers.

All functions are designed to be called from ``app.py`` or page modules;
they receive their dependencies explicitly (no hidden globals).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import NAV_TABS, FC_HWR, cur_sym, _c, _fmt_idr
from engines import FinancialEngine, ForecastEngine


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def inject_sidebar_css() -> None:
    """Inject the full sidebar + card stylesheet into the page."""
    st.markdown("""
<style>
/* ── Sidebar Container Tweaks ── */
section[data-testid="stSidebar"] {
    width: 280px !important;
}

/* ── Section Headers (Filters, Settings) ── */
.sidebar-section-header {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--txt-secondary);
    margin-top: 20px;
    margin-bottom: 12px;
    padding-left: 4px;
    display: block;
}

/* ── Navigation Items (Modern SaaS Active State) ── */
.sidebar-nav-item {
    display: block;
    padding: 10px 12px;
    margin: 4px 0;
    border-radius: 8px;
    font-size: 14px;
    color: var(--txt-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
    position: relative;
}
.sidebar-nav-item:hover {
    background-color: var(--bg-radio-sel);
    color: var(--txt-primary);
    border-left-color: #888;
}
.sidebar-nav-item.active {
    background-color: var(--bg-radio-sel);
    color: var(--txt-primary);
    border-left-color: #00B894;
    font-weight: 600;
}

/* ── Filter Section Container ── */
.sidebar-filters {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    margin: 8px 0;
}
.sidebar-filter-item {
    margin-bottom: 12px;
}
.sidebar-filter-item:last-child {
    margin-bottom: 0;
}
.sidebar-filter-label {
    font-size: 0.8rem;
    color: var(--txt-secondary);
    font-weight: 600;
    margin-bottom: 6px;
    display: block;
}

/* ── Branding Compact ── */
.sidebar-branding {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
}
.sidebar-branding-icon {
    font-size: 28px;
    line-height: 1;
}
.sidebar-branding-text {
    flex: 1;
}
.sidebar-branding-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--txt-primary);
    margin: 0;
    line-height: 1.2;
}
.sidebar-branding-tagline {
    font-size: 0.7rem;
    color: var(--txt-secondary);
    margin: 2px 0 0 0;
}

/* ── Divider (minimal) ── */
.sidebar-divider {
    border: none;
    height: 1px;
    background-color: var(--border);
    margin: 16px 0;
}

/* ── Settings Section (bottom) ── */
.sidebar-settings {
    margin-top: auto;
    padding-top: 16px;
    border-top: 1px solid var(--border);
}
.sidebar-footer-text {
    font-size: 0.65rem;
    color: var(--txt-muted);
    text-align: center;
    margin-top: 16px;
    padding-top: 8px;
}

/* ── Insight / Metric Cards ── */
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  METRIC CARDS
# ══════════════════════════════════════════════════════════════════════════════

def compact_metric_card(icon: str, label: str, value: str,
                        delta: float | None = None, note: str = '') -> str:
    """Render a compact KPI card with icon, main value, delta trend, and note."""
    delta_html = ''
    if delta is not None:
        color = '#00B894' if delta > 0 else '#E17055'
        arrow = '↑' if delta > 0 else '↓'
        delta_html = f'<span style="color:{color};font-size:12px;margin-left:4px;">{arrow} {abs(delta):.1f}%</span>'
    label_html = f'<div style="font-size:0.8rem;color:var(--txt-metric-lbl);font-weight:500;max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</div>'
    value_html = f'<div style="font-size:20px;font-weight:700;color:var(--txt-metric);max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{value}</div>'

    html = (
        '<div class="insight-card" style="padding:14px;min-height:110px;display:flex;flex-direction:column;justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="font-size:24px;line-height:1;">{icon}</span>'
        f'{label_html}'
        '</div>'
        f'<div style="display:flex;align-items:baseline;gap:8px;">'
        f'{value_html}'
        f'{delta_html}'
        '</div>'
        f"{('<div style=\"font-size:0.75rem;color:var(--txt-muted);margin-top:6px;max-width:260px;overflow:hidden;text-overflow:ellipsis;\">' + note + '</div>') if note else ''}"
        '</div>'
    )
    return html


def metric_card_three_row(icon: str, title: str, subtitle: str, value: str,
                          delta: float | None = None, note: str = '') -> str:
    """Render a three-row KPI card: title, subtitle, and numeric value."""
    delta_html = ''
    if delta is not None:
        color = '#00B894' if delta > 0 else '#E17055'
        arrow = '↑' if delta > 0 else '↓'
        delta_html = f'<span style="color:{color};font-size:12px;margin-left:6px;">{arrow} {abs(delta):.1f}%</span>'

    title_html = f'<div style="font-size:0.8rem;color:var(--txt-metric-lbl);font-weight:600;">{title}</div>'
    subtitle_html = f'<div style="font-size:0.95rem;color:var(--txt-primary);font-weight:700;margin-top:6px;white-space:normal;word-break:break-word;">{subtitle}</div>'
    value_html = f'<div style="font-size:22px;font-weight:800;color:var(--txt-metric);margin-top:8px;">{value}</div>'
    note_html = f"<div style=\"font-size:0.75rem;color:var(--txt-muted);margin-top:8px;\">{note}</div>" if note else ''

    html = (
        '<div class="insight-card" style="padding:14px;min-height:110px;display:flex;flex-direction:column;justify-content:flex-start;">'
        f'{title_html}'
        f'{subtitle_html}'
        f'<div style="display:flex;align-items:baseline;gap:8px;">{value_html}{delta_html}</div>'
        f'{note_html}'
        '</div>'
    )
    return html


def insight_mini_card(title: str, main_text: str, sub_text: str,
                      color: str = '#6C5CE7') -> str:
    """Compact insight card for stacking (3 per column)."""
    return f"""
    <div class="insight-card" style="padding:12px;border-left:3px solid {color};margin-bottom:12px;">
        <div style="font-size:0.75rem;color:var(--txt-secondary);font-weight:600;text-transform:uppercase;margin-bottom:4px;">{title}</div>
        <div style="font-size:0.95rem;color:var(--txt-primary);font-weight:600;">{main_text}</div>
        <div style="font-size:0.8rem;color:var(--txt-muted);margin-top:2px;">{sub_text}</div>
    </div>
    """


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def render_branding() -> None:
    """Compact branding section at top of sidebar."""
    st.sidebar.markdown("""
    <div class="sidebar-branding">
        <div class="sidebar-branding-icon">☕</div>
        <div class="sidebar-branding-text">
            <div class="sidebar-branding-name">G Coffee Shop</div>
            <div class="sidebar-branding-tagline">Strategic Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_navigation() -> str:
    """Primary navigation menu — returns the selected tab label."""
    st.sidebar.markdown(
        '<h3 style="font-size:0.8rem;color:var(--txt-muted);text-transform:uppercase;margin:0 0 8px 0;font-weight:600;">Navigation</h3>',
        unsafe_allow_html=True,
    )
    selected_tab = st.sidebar.radio(
        'nav_menu', NAV_TABS, index=0,
        label_visibility='collapsed', key='nav_selection',
    )
    return selected_tab


def render_filters() -> tuple[str, str]:
    """Grouped filters section — returns (audience, currency_choice)."""
    st.sidebar.markdown('<div class="sidebar-section-header">🔍 Filters</div>', unsafe_allow_html=True)

    with st.sidebar:
        # ── Branch filter ──────────────────────────────────────────────
        _branches = []
        try:
            if FC_HWR.exists():
                _tmp = pd.read_parquet(FC_HWR)
                if 'branch' in _tmp.columns:
                    _branches = sorted(_tmp['branch'].dropna().unique().tolist())
        except Exception:
            _branches = []

        if 'branch_filter' not in st.session_state:
            st.session_state['branch_filter'] = _branches

        st.markdown(
            '<label style="font-size:0.8rem;color:var(--txt-secondary);font-weight:600;display:block;margin-bottom:6px;">Branch</label>',
            unsafe_allow_html=True,
        )
        _ = st.multiselect(
            'branch_label', options=_branches,
            default=st.session_state.get('branch_filter', _branches),
            key='branch_filter', label_visibility='collapsed',
        )
        st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

        # ── Customer Group ─────────────────────────────────────────────
        st.markdown(
            '<label style="font-size:0.8rem;color:var(--txt-secondary);font-weight:600;display:block;margin-bottom:6px;">Customer Group</label>',
            unsafe_allow_html=True,
        )
        audience = st.radio(
            'audience_label', ['Members', 'Guests (Non-Members)'],
            help='Toggle between member loyalty segments and guest behavioral clusters',
            key='audience_filter', label_visibility='collapsed',
        )
        st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

        # ── Dashboard Focus ────────────────────────────────────────────
        st.markdown(
            '<label style="font-size:0.8rem;color:var(--txt-secondary);font-weight:600;display:block;margin-bottom:6px;">Dashboard Focus</label>',
            unsafe_allow_html=True,
        )
        _ = st.radio(
            'focus_label', ['Profit', 'Revenue'],
            help='Toggle between profit and revenue analytics',
            key='dashboard_lens', label_visibility='collapsed',
        )
        st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)

        # ── Currency ───────────────────────────────────────────────────
        st.markdown(
            '<label style="font-size:0.8rem;color:var(--txt-secondary);font-weight:600;display:block;margin-bottom:6px;">Currency</label>',
            unsafe_allow_html=True,
        )
        currency_choice = st.selectbox(
            'currency_label', ['RM', 'IDR'],
            format_func=lambda x: f'{x} (Rp)' if x == 'IDR' else x,
            help='Display values in Ringgit Malaysia or Indonesian Rupiah',
            key='currency', label_visibility='collapsed',
        )

    return audience, currency_choice


def render_settings() -> str:
    """Settings section at bottom of sidebar — returns theme choice."""
    st.sidebar.markdown('<div class="sidebar-section-header">⚙️ Settings</div>', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            '<label style="font-size:0.8rem;color:var(--txt-secondary);font-weight:600;display:block;margin-bottom:6px;">Theme</label>',
            unsafe_allow_html=True,
        )
        theme_choice = st.radio(
            'theme_label', ['Dark', 'Light'],
            index=0 if st.session_state.get('theme_toggle', 'Dark') == 'Dark' else 1,
            key='theme_toggle', label_visibility='collapsed',
        )
    return theme_choice


# ══════════════════════════════════════════════════════════════════════════════
#  FORECAST HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_margin_pct(fin_engine: FinancialEngine) -> float:
    """Return the site's default net margin as a ratio (e.g. 0.25)."""
    try:
        m = fin_engine.get_net_margin('Latte')
        return float(m.get('net_margin_pct', 0)) / 100.0
    except Exception:
        return 0.25


def get_filtered_profit_fc(fc_engine: ForecastEngine,
                           margin_pct: float | None = None) -> pd.DataFrame:
    """Return ``profit_fc`` from ``fc_engine``, filtered by global ``branch_filter``.

    Ensures callers get a consistent, branch-filtered forecast dataframe.
    """
    if margin_pct is None:
        margin_pct = 0.25
    profit_fc = fc_engine.get_profit_forecast(margin_pct=margin_pct)
    sel_branches = st.session_state.get('branch_filter', [])
    if sel_branches:
        try:
            profit_fc = profit_fc[profit_fc['branch'].isin(sel_branches)]
        except Exception:
            pass
    return profit_fc


def aggregate_forecast_by_date(profit_fc: pd.DataFrame,
                               metric: str = 'projected_profit') -> pd.DataFrame:
    """Aggregate branch-level forecast into a date × scenario pivot with smoothed series.

    Returns columns: ``date``, ``conservative``, ``aggressive``, ``midpoint``,
    ``midpoint_smooth``, ``conservative_smooth``, ``aggressive_smooth``.
    """
    if profit_fc is None or profit_fc.empty:
        return pd.DataFrame(
            columns=['date', 'conservative', 'aggressive', 'midpoint',
                     'midpoint_smooth', 'conservative_smooth', 'aggressive_smooth']
        )

    fc_sum = profit_fc.groupby(['created_at', 'scenario'], as_index=False)[metric].sum()
    pivot = fc_sum.pivot(index='created_at', columns='scenario', values=metric).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={
        'Conservative Growth': 'conservative',
        'Aggressive Growth': 'aggressive',
    })
    for col in ('conservative', 'aggressive'):
        if col not in pivot.columns:
            pivot[col] = 0.0

    pivot['midpoint'] = (pivot['conservative'] + pivot['aggressive']) / 2.0
    pivot = pivot.rename(columns={'created_at': 'date'})

    agg = pivot[['date', 'conservative', 'aggressive', 'midpoint']].copy()
    agg['midpoint_smooth'] = agg['midpoint'].rolling(7, center=True, min_periods=1).mean()
    agg['conservative_smooth'] = agg['conservative'].rolling(7, center=True, min_periods=1).mean()
    agg['aggressive_smooth'] = agg['aggressive'].rolling(7, center=True, min_periods=1).mean()
    return agg
