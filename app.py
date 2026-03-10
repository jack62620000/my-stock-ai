import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import altair as alt
from datetime import datetime, timedelta

# --- 模擬 FinMind 數據生成 ---
def get_mock_data():
    date_rng = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Open'] = np.random.uniform(500, 600, size=(len(date_rng)))
    df['High'] = df['Open'] + np.random.uniform(0, 20, size=(len(date_rng)))
    df['Low'] = df['Open'] - np.random.uniform(0, 20, size=(len(date_rng)))
    df['Close'] = df['Open'] + np.random.uniform(-15, 15, size=(len(date_rng)))
    df['Volume'] = np.random.randint(1000, 5000, size=(len(date_rng)))
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    return df

df = get_mock_data()
st.title("🧪 Raymond 的 K 線圖操作樣式實驗室")
st.caption("這 6 種樣式代表了不同的量化分析邏輯，請點擊圖表右上角工具列進行縮放、平移操作。")

# --- 樣式 1：經典專業互動式 (Standard Professional) ---
# 特點：上下子圖連動，成交量獨立，支援十字準心與區間縮放。
st.header("1. 經典專業連動型 (Plotly Multi-Subplot)")
fig1 = go.Figure()
fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
fig1.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))
fig1.update_layout(height=400, margin=dict(t=30, b=10), xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig1, use_container_width=True)

# --- 樣式 2：極簡趨勢流 (Clean Trend Focus) ---
# 特點：去除格線，著重於價格走勢與區間著色（雲層圖概念）。
st.header("2. 極簡趨勢流 (Clean Visuals)")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df['Date'], y=df['High'], fill=None, mode='lines', line_color='rgba(0,176,246,0.2)'))
fig2.add_trace(go.Scatter(x=df['Date'], y=df['Low'], fill='tonexty', mode='lines', line_color='rgba(0,176,246,0.2)', name='波動區間'))
fig2.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
fig2.update_layout(height=350, plot_bgcolor='white', xaxis_showgrid=False, yaxis_showgrid=False)
st.plotly_chart(fig2, use_container_width=True)

# --- 樣式 3：區間選擇器 (Range Selector Control) ---
# 特點：下方帶有導航滑桿，適合查看「長期歷史」中的「短波段」。
st.header("3. 歷史長廊模式 (Range Slider Navigation)")
fig3 = go.Figure(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
fig3.update_layout(xaxis_rangeslider_visible=True, height=450)
st.plotly_chart(fig3, use_container_width=True)

# --- 樣式 4：數據洞察模式 (Data Insight Layer) ---
# 特點：將成交量「重疊」在價格背景，並標註最高/最低點。
st.header("4. 數據重疊模式 (Overlaid Volume & Annotations)")
fig4 = go.Figure()
fig4.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='成交量', marker_color='rgba(100,100,100,0.3)', yaxis='y2'))
fig4.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='價格'))
fig4.update_layout(yaxis2=dict(title='成交量', overlaying='y', side='right', showgrid=False), height=400)
st.plotly_chart(fig4, use_container_width=True)

# --- 樣式 5：輕量化統計模式 (Altair Declarative) ---
# 特點：非 Plotly，採用 Vega-Lite 引擎。操作感更像網頁組件，點擊圖例可隱藏線條。
st.header("5. 輕量化交互模式 (Altair Tooltip Focus)")
base = alt.Chart(df).encode(x='Date:T', color=alt.condition("datum.Open <= datum.Close", alt.value("#06982d"), alt.value("#ae1325")))
rule = base.mark_rule().encode(y='Low:Q', y2='High:Q')
bar = base.mark_bar().encode(y='Open:Q', y2='Close:Q')
chart5 = (rule + bar).properties(width='auto', height=300).interactive()
st.altair_chart(chart5, use_container_width=True)

# --- 樣式 6：多維指標監控 (Indicator Dashboard) ---
# 特點：將 K 線與 技術指標（如 RSI/MACD）水平或垂直切割，適合複式分析。
st.header("6. 多指標儀表板 (Indicator Dashboard Layout)")
from plotly.subplots import make_subplots
fig6 = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
fig6.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
fig6.add_trace(go.Scatter(x=df['Date'], y=df['MA5'], name='RSI 模擬', line=dict(color='purple')), row=2, col=1)
fig6.update_layout(height=500, showlegend=False, xaxis_rangeslider_visible=False)
st.plotly_chart(fig6, use_container_width=True)
