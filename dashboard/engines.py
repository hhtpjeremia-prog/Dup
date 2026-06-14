"""
Business logic engines for the G Coffee Shop Dashboard.

FinancialEngine  — menu-level costing, margin, and bundling calculations.
ForecastEngine   — wraps forecast parquet files with business-friendly scenario labels.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import FC_HWR, FC_PROPHET, FC_SARIMA, BASE


# ══════════════════════════════════════════════════════════════════════════════
#  FINANCIAL ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class FinancialEngine:
    """
    Calculates key financial metrics per transaction and per bundle.
    Based on menu-level pricing with estimated cost structures.
    """

    # Typical coffee shop cost assumptions (as fraction of retail)
    COGS_RATIO = 0.32        # Cost of Goods Sold (raw materials ~32%)
    OPEX_PER_TRANSACTION = 2.50  # Fixed operating cost per transaction

    def __init__(self, menu_df: pd.DataFrame):
        self.menu = menu_df.set_index('item_name')['price'].to_dict()
        self.avg_price = menu_df['price'].mean()

    def get_cogs(self, item_name: str) -> float:
        """Estimate raw material cost for an item."""
        price = self.menu.get(item_name, self.avg_price)
        return price * self.COGS_RATIO

    @staticmethod
    def get_operating_cost() -> float:
        """Per-transaction operating cost (labour, rent, utilities)."""
        return FinancialEngine.OPEX_PER_TRANSACTION

    def get_net_margin(self, item_name: str, discount: float = 0.0) -> dict:
        """
        Net Profit Margin = Price - COGS - OpCost - Discount.
        Returns both absolute margin and margin ratio.
        """
        price = self.menu.get(item_name, self.avg_price)
        cogs = price * self.COGS_RATIO
        op_cost = self.OPEX_PER_TRANSACTION
        discount_abs = price * discount
        net = price - cogs - op_cost - discount_abs
        return {
            'item': item_name,
            'price': price,
            'cogs': cogs,
            'operating_cost': op_cost,
            'discount': discount_abs,
            'net_profit': net,
            'net_margin_pct': (net / price * 100) if price > 0 else 0,
        }

    def get_bundle_margin(self, items: list, discount: float = 0.0) -> dict:
        """Calculate combined margin for a bundle of items."""
        total = {'price': 0, 'cogs': 0, 'op_cost': 0, 'discount': 0, 'net': 0}
        for item in items:
            m = self.get_net_margin(item.strip(), discount)
            total['price'] += m['price']
            total['cogs'] += m['cogs']
            total['op_cost'] += m['operating_cost']
            total['discount'] += m['discount']
            total['net'] += m['net_profit']
        total['margin_pct'] = (total['net'] / total['price'] * 100) if total['price'] > 0 else 0
        return total

    def price_sensitivity(self, item_name: str, pct_change: float) -> dict:
        """Return new margin if price changes by pct_change (e.g., 0.10 = +10%)."""
        base = self.get_net_margin(item_name)
        new_price = base['price'] * (1 + pct_change)
        new_net = new_price - base['cogs'] - base['operating_cost'] - base['discount']
        return {
            'original_price': base['price'],
            'new_price': new_price,
            'original_net': base['net_profit'],
            'new_net': new_net,
            'margin_impact': new_net - base['net_profit'],
        }


# ══════════════════════════════════════════════════════════════════════════════
#  FORECAST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ForecastEngine:
    """
    Wraps both forecast models with business-friendly labels.
    HWR-XGB -> 'Conservative Growth' (stable, trend-following)
    Prophet-XGB -> 'Aggressive Growth' (captures more inflection, higher upside)
    """

    LABELS = {
        'HWR-XGB': 'Conservative Growth',
        'Prophet-XGB': 'Aggressive Growth',
        'SARIMA-XGB': 'Balanced Growth',
    }

    def __init__(self):
        from loaders import load_forecast  # late import to avoid circular dependency

        # Forecast files are optional in dev environments.
        # If a parquet is missing, the app should still run with the remaining model(s).
        models = []

        # Prefer model-specific forecasts but allow a generic 90-day forecast as fallback
        GENERIC_FC = BASE / 'df_forecast_90days.parquet'
        generic_fc = None
        if GENERIC_FC.exists():
            try:
                generic_fc = load_forecast(str(GENERIC_FC))
            except Exception:
                generic_fc = None

        try:
            conservative = load_forecast(str(FC_HWR))
            conservative['scenario'] = self.LABELS.get('HWR-XGB', 'Conservative Growth')
            models.append(conservative)
        except FileNotFoundError:
            if generic_fc is not None:
                c = generic_fc.copy()
                c['scenario'] = self.LABELS.get('HWR-XGB', 'Conservative Growth')
                models.append(c)
            else:
                st.warning(f"Forecast file missing: {FC_HWR.name}. Using only Prophet model.")
        except Exception as e:
            st.warning(f"Failed to load HWR forecast ({FC_HWR.name}): {e}. Using only Prophet model.")

        try:
            aggressive = load_forecast(str(FC_PROPHET))
            aggressive['scenario'] = self.LABELS.get('Prophet-XGB', 'Aggressive Growth')
            models.append(aggressive)
        except FileNotFoundError:
            if generic_fc is not None:
                a = generic_fc.copy()
                a['scenario'] = self.LABELS.get('Prophet-XGB', 'Aggressive Growth')
                models.append(a)
            else:
                st.warning(f"Forecast file missing: {FC_PROPHET.name}. Using only HWR model.")
        except Exception as e:
            st.warning(f"Failed to load Prophet forecast ({FC_PROPHET.name}): {e}. Using only HWR model.")

        if not models:
            # Hard fallback: allow app to render without forecast.
            self.full = pd.DataFrame(columns=['created_at', 'branch', 'total_transactions', 'scenario'])
            self.avg_transaction_value = 0.0
            return

        self.full = pd.concat(models, ignore_index=True)
        if 'created_at' in self.full.columns:
            self.full['created_at'] = pd.to_datetime(self.full['created_at'])

        # Derive average transaction value from metadata
        from loaders import load_avg_tx_value
        self.avg_transaction_value = float(load_avg_tx_value())

    def get_profit_forecast(self, margin_pct: float = 0.25) -> pd.DataFrame:
        """
        Convert transaction forecasts to profit forecasts.
        margin_pct: estimated net profit margin on each transaction.
        """
        df = self.full.copy()
        df['projected_revenue'] = df['total_transactions'] * self.avg_transaction_value
        df['projected_profit'] = df['projected_revenue'] * margin_pct
        return df

    def get_bundle_impact_forecast(
        self, bundle_name: str, margin_pct: float = 0.25, boost_factor: float = 0.08
    ) -> pd.DataFrame:
        """
        Simulate the projected profit increase if a specific bundle is launched.
        boost_factor: estimated % increase in transactions due to bundle promo.
        """
        df = self.get_profit_forecast(margin_pct)
        df['bundle_boost'] = df['total_transactions'] * boost_factor
        df['boosted_transactions'] = df['total_transactions'] + df['bundle_boost']
        df['boosted_profit'] = df['boosted_transactions'] * self.avg_transaction_value * margin_pct
        df['profit_increase'] = df['boosted_profit'] - df['projected_profit']
        df['bundle_name'] = bundle_name
        return df
