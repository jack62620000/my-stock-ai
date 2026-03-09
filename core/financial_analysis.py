import pandas as pd
import numpy as np


def safe_pct(value):
    if pd.isna(value):
        return np.nan
    return value * 100


def safe_yi(value):
    if pd.isna(value):
        return np.nan
    return value / 1e8


def safe_billion(value):
    if pd.isna(value):
        return np.nan
    return value / 1e9
