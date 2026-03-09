import pandas as pd
import numpy as np


def get_volume_trend(df: pd.DataFrame, price_change_pct: float):
    if df.empty or "Volume" not in df.columns:
        return "量價資訊不足"

    volume = df["Volume"].iloc[-1]
    avg_volume = df["Volume"][-30:].mean() if len(df) >= 30 else np.nan

    if pd.isna(avg_volume) or avg_volume == 0:
        return "量價資訊不足"

    if price_change_pct > 0 and volume > avg_volume * 1.2:
        return "🟢 價漲量增 - 多頭強，但偏高風險（高檔追高要小心）"
    if price_change_pct < 0 and volume > avg_volume * 1.2:
        return "🔴 價跌量增 - 多頭出場、拋售，偏壞"
    if price_change_pct > 0 and volume < avg_volume * 0.8:
        return "🔴 價漲量縮 - 動能不足，偏高風險"
    if price_change_pct < 0 and volume < avg_volume * 0.8:
        return "🟡 價跌量縮 - 市場觀望，偏中性"
    return "⚪ 價量正常 - 偏中性"
