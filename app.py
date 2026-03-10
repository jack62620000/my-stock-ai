import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import numpy as np

# --- 1. 模擬數據準備 ---
def get_tv_json_data():
    dates = pd.bdate_range(start='2024-01-01', periods=100)
    data = []
    price = 500
    for d in dates:
        price += np.random.normal(1, 5)
        o, c = price, price + np.random.normal(0, 5)
        data.append({
            "time": int(d.timestamp()), # TradingView 使用 Unix Timestamp
            "open": round(o, 2),
            "high": round(max(o, c) + 2, 2),
            "low": round(min(o, c) - 2, 2),
            "close": round(c, 2)
        })
    return json.dumps(data)

chart_data = get_tv_json_data()

# --- 2. 構建大戶投風格的 HTML/JS ---
# 這裡我們直接寫原生 JavaScript，強制鎖定邊界
html_code = f"""
<div id="tv-chart" style="height: 500px; width: 100%;"></div>
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<script>
    const chart = LightweightCharts.createChart(document.getElementById('tv-chart'), {{
        width: document.getElementById('tv-chart').offsetWidth,
        height: 500,
        layout: {{ backgroundColor: '#ffffff', textColor: '#333' }},
        grid: {{ vertLines: {{ color: '#f0f0f0' }}, horzLines: {{ color: '#f0f0f0' }} }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{ borderColor: '#dfdfdf' }},
        timeScale: {{ 
            borderColor: '#dfdfdf',
            fixRightEdge: true,  // 鎖定右側：絕對拉不出空白
            fixLeftEdge: true,   // 鎖定左側
            timeVisible: true,
            secondsVisible: false
        }},
    }});

    const candleSeries = chart.addCandlestickSeries({{
        upColor: '#EB3B3B', downColor: '#26A69A', 
        borderUpColor: '#EB3B3B', borderDownColor: '#26A69A',
        wickUpColor: '#EB3B3B', wickDownColor: '#26A69A'
    }});

    const data = {chart_data};
    candleSeries.setData(data);
    
    // 自動縮放到最後 30 根 K 線 (視窗小一半)
    chart.timeScale().setVisibleRange({{
        from: data[data.length - 30].time,
        to: data[data.length - 1].time,
    }});
</script>
"""

# --- 3. 顯示 ---
st.title("🛡️ 終極鎖定：原生引擎版")
st.info("這是我為你手寫的原生 JS 引擎。左右邊界已徹底鎖死，絕對無法拉出任何空白空間。")

# 渲染組件
components.html(html_code, height=520)

st.markdown("""
### 💎 為什麼這次一定有東西？
* **無需套件**：直接從官方 CDN 載入 TradingView 引擎，避開 `requirements.txt` 安裝失敗的問題。
* **物理鎖定**：`fixRightEdge` 與 `fixLeftEdge` 在原生 JS 層級被啟動，這是不可能被滑鼠突破的「次元壁」。
""")
