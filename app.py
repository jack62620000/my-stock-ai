import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import pandas as pd
import numpy as np

# --- 1. 數據模擬 (TradingView 格式) ---
def get_tv_data():
    dates = pd.bdate_range(start='2024-01-01', periods=100)
    df = pd.DataFrame(index=dates)
    df['close'] = (500 + np.random.randn(100).cumsum() * 5).round(1)
    df['open'] = (df['close'] + np.random.uniform(-5, 5, 100)).round(1)
    df['high'] = df[['open', 'close']].max(axis=1) + 3
    df['low'] = df[['open', 'close']].min(axis=1) - 3
    
    # 格式化為前端要求的 JSON 格式
    candles = []
    for i in range(len(df)):
        candles.append({
            "time": df.index[i].strftime('%Y-%m-%d'),
            "open": float(df['open'].iloc[i]),
            "high": float(df['high'].iloc[i]),
            "low": float(df['low'].iloc[i]),
            "close": float(df['close'].iloc[i]),
        })
    return candles

candles = get_tv_data()

# --- 2. 配置圖表參數 (這就是鎖定邊界的關鍵) ---
chartOptions = {
    "layout": {
        "textColor": 'black',
        "background": { "type": 'solid', "color": 'white' },
    },
    "rightPriceScale": {
        "scaleMargins": { "top": 0.3, "bottom": 0.25 },
        "borderColor": 'rgba(197, 203, 206, 0.8)',
    },
    "timeScale": {
        "borderColor": 'rgba(197, 203, 206, 0.8)',
        "fixLeftEdge": True,   # 鎖定左側邊緣！
        "fixRightEdge": True,  # 鎖定右側邊緣！不准拉出空白
        "rightOffset": 5,      # 右側只留 5 根 K 線的緩衝
    },
    "handleScroll": { "mouseWheel": True, "pressedMouseMove": True },
    "handleScale": { "axisPressedMouseMove": True, "mouseWheel": True },
}

seriesCandlestickChart = [
    {
        "type": 'Candlestick',
        "data": candles,
        "options": {
            "upColor": '#EB3B3B', "downColor": '#26A69A', 
            "borderUpColor": '#EB3B3B', "borderDownColor": '#26A69A',
            "wickUpColor": '#EB3B3B', "wickDownColor": '#26A69A',
        }
    }
]

# --- 3. 渲染 ---
st.title("🛡️ 終極鎖定：TradingView 原生引擎版")
st.info("這不是 Plotly。這是 TradingView 的核心引擎，邊界已強制鎖定 (fixRightEdge: True)。")

renderLightweightCharts([
    {
        "chart": chartOptions,
        "series": seriesCandlestickChart
    }
], 'main')
