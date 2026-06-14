"""
Cached data loaders for the G Coffee Shop Dashboard.

Every public function uses ``@st.cache_data(ttl=3600)`` so repeated calls
across pages / re-runs avoid redundant I/O.

Strategy for Parquet files
--------------------------
:func:`read_parquet_safe` tries ``pd.read_parquet`` first and falls
back to PyArrow when a ``TypeError`` (categorical-dtype issue) is raised.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st

from config import (
    MENU_DATA, AVG_TX_VALUE, DAILY_HIST,
    MEMBER_META, GUEST_META, MEMBER_RULES, GUEST_RULES,
    MEMBER_SEG, GUEST_SEG,
)


# ── Unified Parquet reader ───────────────────────────────────────────────────

def read_parquet_safe(path: str | Path) -> pd.DataFrame:
    """Read a parquet file, handling categorical-dtype issues gracefully.

    Falls back from pandas → PyArrow when ``pd.read_parquet`` raises
    ``TypeError`` (caused by some categorical columns in this dataset).
    """
    path = str(path)
    try:
        return pd.read_parquet(path)
    except TypeError:
        tbl = pq.read_table(path)
        return tbl.to_pandas()


# ── Cached loaders ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_json(path: str | Path) -> dict:
    """Load a JSON file — return ``{}`` if missing or broken."""
    path = Path(path)
    if not path.exists():
        st.warning(f"File '{path.name}' not found; using empty defaults.")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Failed to parse {path.name}: {e}")
        return {}


@st.cache_data(ttl=3600)
def load_parquet(path: str | Path) -> pd.DataFrame:
    """Read a parquet file (cached, handles categorical dtypes)."""
    return read_parquet_safe(path)


@st.cache_data(ttl=3600)
def load_forecast(path: str | Path) -> pd.DataFrame:
    """Load a forecast parquet file (PyArrow)."""
    path = str(path)
    tbl = pq.read_table(path)
    return tbl.to_pandas()


@st.cache_data(ttl=3600)
def load_segment_counts(path: str | Path, col: str = 'segment_name') -> pd.DataFrame:
    """Read *only* the segment-name column from a large parquet and return counts.

    Memory-efficient — never loads the whole file into RAM.
    """
    path = str(path)
    tbl = pq.read_table(path, columns=[col])
    counts = Counter(tbl.column(col).to_pylist())
    total = len(tbl)
    return pd.DataFrame([
        {'segment': k, 'count': v, 'pct': round(v / total * 100, 1)}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    ])


@st.cache_data(ttl=3600)
def load_menu() -> pd.DataFrame:
    """Load the menu — fallback from cleaned to raw if needed."""
    ALT_MENU = MENU_DATA.parent / 'menu_items.parquet'
    if MENU_DATA.exists():
        return pd.read_parquet(MENU_DATA)
    if ALT_MENU.exists():
        st.warning(f"'{MENU_DATA.name}' not found; using '{ALT_MENU.name}' as fallback.")
        return pd.read_parquet(ALT_MENU)
    raise FileNotFoundError(
        f"Menu file not found. Tried '{MENU_DATA.name}' and '{ALT_MENU.name}'."
    )


@st.cache_data(ttl=3600)
def load_avg_tx_value() -> float:
    """Load pre-computed average transaction value from metadata JSON."""
    with open(AVG_TX_VALUE, 'r', encoding='utf-8') as f:
        return float(json.load(f)['avg_transaction_value'])


@st.cache_data(ttl=3600)
def load_seg_by_branch(path: str | Path) -> pd.DataFrame:
    """Load pre-computed per-branch segment counts."""
    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_historical_daily() -> pd.DataFrame:
    """Load pre-computed daily historical data from metadata parquet."""
    return pd.read_parquet(DAILY_HIST)


# ── Convenience helpers ──────────────────────────────────────────────────────

def load_all_data():
    """Load **all** data that the dashboard needs and return as a dict.

    Calling this once at startup is simpler than importing each loader
    individually in every page module.
    """
    data = {
        'menu_df': load_menu(),
        'member_meta': load_json(MEMBER_META),
        'guest_meta': load_json(GUEST_META),
        'member_rules': load_parquet(MEMBER_RULES),
        'guest_rules': load_parquet(GUEST_RULES),
        'member_seg_counts': pd.read_parquet(MEMBER_SEG),
        'guest_seg_counts': pd.read_parquet(GUEST_SEG),
    }
    return data
