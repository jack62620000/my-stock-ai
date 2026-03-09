import pandas as pd
import numpy as np


def calc_fair_price(d: dict):
    eps = d.get("eps", np.nan)
    pe = d.get("pe", np.nan)
    growth = d.get("eps_growth", np.nan)

    if pd.isna(eps) or eps <= 0:
        return np.nan

    if pd.notna(pe) and pe > 0:
        fair_pe = min(max(pe, 8), 20)
    elif pd.notna(growth):
        fair_pe = min(max(10 + growth * 20, 8), 20)
    else:
        fair_pe = 15

    return eps * fair_pe


def calc_margin_of_safety(d: dict):
    price = d.get("price", np.nan)
    fair_price = calc_fair_price(d)

    if pd.isna(price) or price == 0 or pd.isna(fair_price):
        return np.nan

    return (fair_price - price) / fair_price
