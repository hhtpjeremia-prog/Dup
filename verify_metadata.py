"""Verify all metadata files are correct for app.py consumption."""
import pandas as pd
import json
import sys

errors = []

# ── 1. df_avg_tx_value.json ───────────────────────────────────
try:
    with open("data/df_avg_tx_value.json") as f:
        d = json.load(f)
    val = d["avg_transaction_value"]
    print(f"[OK] df_avg_tx_value.json -> avg_transaction_value = {val}")
except Exception as e:
    errors.append(f"df_avg_tx_value.json: {e}")
    print(f"[FAIL] df_avg_tx_value.json: {e}")

# ── 2. df_cities.json ──────────────────────────────────────────
try:
    with open("data/df_cities.json") as f:
        cities = json.load(f)
    assert isinstance(cities, list), "not a list"
    assert len(cities) > 0, "empty list"
    print(f"[OK] df_cities.json -> {len(cities)} cities: {cities[:3]}...")
except Exception as e:
    errors.append(f"df_cities.json: {e}")
    print(f"[FAIL] df_cities.json: {e}")

# ── 3. df_guest_seg_counts.parquet ─────────────────────────────
try:
    df = pd.read_parquet("data/df_guest_seg_counts.parquet")
    assert "segment" in df.columns, "missing 'segment' column"
    assert "count" in df.columns, "missing 'count' column"
    assert "pct" in df.columns, "missing 'pct' column"
    print(f"[OK] df_guest_seg_counts.parquet -> {len(df)} segments, cols={list(df.columns)}")
except Exception as e:
    errors.append(f"df_guest_seg_counts.parquet: {e}")
    print(f"[FAIL] df_guest_seg_counts.parquet: {e}")

# ── 4. df_member_seg_counts.parquet ────────────────────────────
try:
    df = pd.read_parquet("data/df_member_seg_counts.parquet")
    assert "segment" in df.columns, "missing 'segment' column"
    assert "count" in df.columns, "missing 'count' column"
    assert "pct" in df.columns, "missing 'pct' column"
    print(f"[OK] df_member_seg_counts.parquet -> {len(df)} segments, cols={list(df.columns)}")
except Exception as e:
    errors.append(f"df_member_seg_counts.parquet: {e}")
    print(f"[FAIL] df_member_seg_counts.parquet: {e}")

# ── 5. df_daily_historical.parquet ─────────────────────────────
try:
    df = pd.read_parquet("data/df_daily_historical.parquet")
    expected_cols = {"date", "city", "total_transactions", "total_revenue"}
    assert expected_cols.issubset(set(df.columns)), f"missing cols, got {list(df.columns)}"
    print(f"[OK] df_daily_historical.parquet -> {len(df)} rows, cols={list(df.columns)}")
except Exception as e:
    errors.append(f"df_daily_historical.parquet: {e}")
    print(f"[FAIL] df_daily_historical.parquet: {e}")

# ── 6. Forecast parquet files ──────────────────────────────────
for fname in ["df_forecast_90days_HWR-XGB.parquet",
              "df_forecast_90days_Prophet-XGB.parquet",
              "df_forecast_90days_SARIMA-XGB.parquet"]:
    try:
        df = pd.read_parquet(f"data/{fname}")
        assert "total_transactions" in df.columns, f"missing 'total_transactions' in {fname}"
        assert "created_at" in df.columns, f"missing 'created_at' in {fname}"
        print(f"[OK] data/{fname} -> {len(df)} rows, cols={list(df.columns)}")
    except Exception as e:
        errors.append(f"{fname}: {e}")
        print(f"[FAIL] data/{fname}: {e}")

# ── 7. Menu ────────────────────────────────────────────────────
try:
    df = pd.read_parquet("data/menu_cleaned.parquet")
    assert "item_name" in df.columns or "item" in df.columns, "missing item name col"
    assert "price" in df.columns, "missing 'price' column"
    print(f"[OK] data/menu_cleaned.parquet -> {len(df)} items, cols={list(df.columns)}")
except Exception as e:
    errors.append(f"menu_cleaned.parquet: {e}")
    print(f"[FAIL] menu_cleaned.parquet: {e}")

# ── 8. Models JSON ─────────────────────────────────────────────
for fname in ["member_cluster_metadata.json", "guest_cluster_metadata.json"]:
    try:
        with open(f"models/{fname}") as f:
            d = json.load(f)
        print(f"[OK] models/{fname} -> keys={list(d.keys())}")
    except Exception as e:
        errors.append(f"models/{fname}: {e}")
        print(f"[FAIL] models/{fname}: {e}")

# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 50)
if errors:
    print(f"FAILED: {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED ✅")
