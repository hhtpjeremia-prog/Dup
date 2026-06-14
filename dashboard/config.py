"""
Configuration & Constants for G Coffee Shop Dashboard.

Centralises paths, theme tokens, currency helpers, business language maps,
and colour palettes so they can be imported by any module.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
#  FILE PATHS
# ══════════════════════════════════════════════════════════════════════════════

BASE  = Path(__file__).resolve().parent
DATA  = BASE / '..' / 'data'
MODELS = BASE / '..' / 'models'

MEMBER_META   = MODELS / 'member_cluster_metadata.json'
GUEST_META    = MODELS / 'guest_cluster_metadata.json'
MEMBER_RULES  = DATA / 'df_rules_member.parquet'
GUEST_RULES   = DATA / 'df_rules_guest.parquet'
MEMBER_SEG    = DATA / 'df_member_seg_counts.parquet'
GUEST_SEG     = DATA / 'df_guest_seg_counts.parquet'
MENU_DATA     = DATA / 'menu_cleaned.parquet'
FC_HWR        = DATA / 'df_forecast_90days_HWR-XGB.parquet'
FC_PROPHET    = DATA / 'df_forecast_90days_Prophet-XGB.parquet'
FC_SARIMA     = DATA / 'df_forecast_90days_SARIMA-XGB.parquet'
AVG_TX_VALUE  = DATA / 'df_avg_tx_value.json'
DAILY_HIST    = DATA / 'df_daily_historical.parquet'
CITIES_FILE   = DATA / 'df_cities.json'

# ══════════════════════════════════════════════════════════════════════════════
#  CURRENCY CONFIGURATION & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

IDR_RATE = 3500  # 1 RM = Rp 3,500 (historical conversion rate)


def _c(val: float) -> float:
    """Convert RM to IDR if IDR mode is selected in session state."""
    if st.session_state.get('currency', 'RM') == 'IDR':
        return val * IDR_RATE
    return val


def _fmt_idr(n: float, fmt: str = ",.0f") -> str:
    """Format number in Indonesian style: . = thousand sep, , = decimal sep."""
    s = format(n, fmt)
    s = s.replace(",", "X")
    s = s.replace(".", ",")
    s = s.replace("X", ".")
    return s


def currency(val: float, fmt: str = ",.0f") -> str:
    """Format a monetary value: converts RM→IDR if toggle is on, adds correct prefix."""
    prefix = "Rp" if st.session_state.get('currency', 'RM') == 'IDR' else "RM"
    return f"{prefix} {_fmt_idr(_c(val), fmt)}"


def cur_sym() -> str:
    """Return currency symbol ('Rp' or 'RM') based on current toggle."""
    return "Rp" if st.session_state.get('currency', 'RM') == 'IDR' else "RM"


def _chart_cv(df, *cols):
    """Convert chart data RM→IDR in-place if IDR mode is on (data asli dalam RM)."""
    if st.session_state.get('currency', 'RM') == 'IDR':
        for col in cols:
            df[col] = df[col] * IDR_RATE


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Convert hex color to rgba string for plotly."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


# ══════════════════════════════════════════════════════════════════════════════
#  THEME TOKEN SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

_DARK_TOKENS = {
    'bg': '#1A1A2E',
    'bg_card': '#16213E',
    'bg_radio_sel': '#1F2B47',
    'border': '#2D3142',
    'font': '#E0E0E0',
    'font_secondary': '#A0A0B0',
    'axis': '#888',
    'grid': '#2D3142',
    'legend': '#AAA',
    'metric': '#FFFFFF',
    'metric_lbl': '#9CA3AF',
    'muted': '#555',
}

_LIGHT_TOKENS = {
    'bg': '#F8F9FA',
    'bg_card': '#FFFFFF',
    'bg_radio_sel': '#E8ECF1',
    'border': '#E0E0E0',
    'font': '#333333',
    'font_secondary': '#666',
    'axis': '#555',
    'grid': '#DDD',
    'legend': '#666',
    'metric': '#1A1A2E',
    'metric_lbl': '#6B7280',
    'muted': '#999',
}


def _build_tokens(theme: str) -> dict:
    """Return the full token dict for the requested theme ('dark' | 'light')."""
    base = _DARK_TOKENS if theme == 'dark' else _LIGHT_TOKENS
    return base.copy()


def chart_theme() -> dict:
    """Return a dict of Plotly layout overrides that match the active theme.

    This is called inside render functions so it always reflects the latest
    session-state toggle (no one-run delay).
    """
    _toggle_val = st.session_state.get('theme_toggle')
    if _toggle_val is not None:
        _effective_theme = 'dark' if 'Dark' in _toggle_val else 'light'
    else:
        _effective_theme = st.session_state.get('theme', 'dark')

    T = _build_tokens(_effective_theme)

    return {
        'font': T['font'],
        'axis': T['axis'],
        'grid': T['grid'],
        'legend': T['legend'],
        'metric': T['metric'],
        'metric_lbl': T['metric_lbl'],
        'bg': T['bg'],
        'bg_card': T['bg_card'],
        'border': T['border'],
        'muted': T['muted'],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BUSINESS LANGUAGE MAPS
# ══════════════════════════════════════════════════════════════════════════════

BUSINESS_COLUMNS = {
    'support': 'Popularity Score',
    'confidence': 'Projected Success Rate',
    'lift': 'Cross-Sell Potential',
    'antecedents': 'Product A',
    'consequents': 'Product B',
    'leverage': 'Upsell Opportunity',
    'conviction': 'Dependency Strength',
}

SEGMENT_DESCRIPTIONS = {
    'At Risk Regulars': 'Loyal customers who haven\'t visited recently — reactivation opportunity',
    'New Occasional': 'New customers with low visit frequency — nurture into regulars',
    'Hibernating': 'Long-absent customers — re-engagement campaign target',
    'Champions': 'Best customers — highest frequency & spending — VIP treatment',
    'Big Spender': 'High-value guests with large basket sizes',
    'Weekend Visitor': 'Weekend-only traffic — target with weekday promotions',
    'Deal Hunter': 'Discount-sensitive — coupon & voucher-driven purchases',
    'Quick Buy': 'Single-item, fast transactions — impulse buy opportunities',
}

# ══════════════════════════════════════════════════════════════════════════════
#  NAVIGATION & COLOUR PALETTE
# ══════════════════════════════════════════════════════════════════════════════

NAV_TABS = [
    '📊 Overview',
    '👥 Customer Segments',
    '🛒 Bundle Intelligence',
    '📈 Forecast & Profit',
    '🔬 Strategic Explorer',
    '🤖 AI Analyst',
]

DARK_COLORS = [
    '#6C5CE7', '#00B894', '#FDAA5E', '#E17055',
    '#0984E3', '#A29BFE', '#55EFC4', '#FAB1A0',
    '#74B9FF', '#81ECEC', '#FDCB6E', '#E17055',
]
