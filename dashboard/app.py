"""
G Coffee Shop — Strategic Intelligence Dashboard
================================================

Entry point.  Sets up session state, loads data & engines, renders the
sidebar, and routes to the correct page module.
"""

from __future__ import annotations

import streamlit as st

from config import (
    currency, cur_sym, _c, _fmt_idr, _chart_cv, hex_to_rgba, chart_theme,
    NAV_TABS, DARK_COLORS,
)
from components import (
    inject_sidebar_css, render_branding, render_navigation,
    render_filters, render_settings,
)
from loaders import load_all_data
from engines import FinancialEngine, ForecastEngine
from Groq_analyst import GroqAnalyst

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title='G Coffee Shop — Strategic Intelligence Dashboard',
    page_icon='☕',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    'theme_toggle': 'Dark',
    'selected_bundle': None,
    'bundle_source': None,
    'scenario_params': {'price_adj': 0.0, 'stock_level': 0.0, 'discount_intensity': 0.0},
    'forecast_fullscreen': False,
    'theme': 'dark',
    'dashboard_lens': 'Profit',
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA & ENGINES
# ══════════════════════════════════════════════════════════════════════════════
data = load_all_data()
menu_df = data['menu_df']
member_meta = data['member_meta']
guest_meta = data['guest_meta']
member_rules = data['member_rules']
guest_rules = data['guest_rules']
member_seg_counts = data['member_seg_counts']
guest_seg_counts = data['guest_seg_counts']

fin_engine = FinancialEngine(menu_df)
fc_engine = ForecastEngine()
groq_analyst = GroqAnalyst()

# ══════════════════════════════════════════════════════════════════════════════
#  INJECT GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
inject_sidebar_css()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
render_branding()
selected_tab = render_navigation()

st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
audience, _ = render_filters()

st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
render_settings()

st.sidebar.markdown("""
<div style="text-align:center;color:var(--txt-muted);font-size:0.65rem;margin-top:24px;padding-top:8px;border-top:1px solid var(--border);">
G Coffee Shop · Prescriptive Analytics v2.0
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  AUDIENCE ROUTING
# ══════════════════════════════════════════════════════════════════════════════
if audience == 'Members':
    rules_df = member_rules
    meta = member_meta
    seg_counts = member_seg_counts
    is_member = True
    if 'cluster_profiles' in meta:
        meta['k'] = len(meta['cluster_profiles'])
else:
    rules_df = guest_rules
    meta = guest_meta
    seg_counts = guest_seg_counts
    is_member = False
    if 'optimal_k' in meta:
        meta['k'] = meta['optimal_k']

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════

_context = {
    'fin_engine': fin_engine,
    'fc_engine': fc_engine,
    'meta': meta,
    'seg_counts': seg_counts,
    'rules_df': rules_df,
    'menu_df': menu_df,
    'is_member': is_member,
    'data': data,
    'groq_analyst': groq_analyst,
}

# Lazy-import page modules so only the active page is loaded
if selected_tab == NAV_TABS[0]:
    from pages.overview import render_overview
    render_overview(_context)
elif selected_tab == NAV_TABS[1]:
    from pages.segments import render_segments
    render_segments(_context)
elif selected_tab == NAV_TABS[2]:
    from pages.bundles import render_bundles
    render_bundles(_context)
elif selected_tab == NAV_TABS[3]:
    from pages.forecast import render_forecast
    render_forecast(_context)
elif selected_tab == NAV_TABS[4]:
    from pages.explorer import render_explorer
    render_explorer(_context)
elif selected_tab == NAV_TABS[5]:
    from pages.ai_analyst import render_ai_analyst
    render_ai_analyst(_context)

# ══════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr style="border-color:#2D3142;">', unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#555;font-size:0.75rem;padding:8px;">'
    'G Coffee Shop · Strategic Intelligence Dashboard · Prescriptive Analytics v2.0</div>',
    unsafe_allow_html=True,
)
