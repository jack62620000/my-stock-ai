import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import altair as alt
from plotly.subplots import make_subplots

# --- 模擬數據 (與之前相同) ---
def get_mock_data():
    date_rng = pd.date_range(start='2024-01-01', end='2025-01-01', freq='D')
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Open'] = np.random.uniform(500, 600, size=(len(date_rng))).cumsum() * 0.1 + 500
    df['High'] = df['Open'] + np.random.uniform(0, 20, size=(len(date_rng)))
    df['Low'] = df['Open'] - np.random.uniform(0, 20, size=(len(date_rng)))
    df['Close'] = df['Open'] + np.random.uniform(-15, 15, size=(len(date_rng)))
    df['Volume'] = np.random.randint(1000, 5000, size=(len(date_rng)))
    df['MA20'] = df['Close'].rolling(20).mean()
    return df

df = get_mock_data()

st.title("🖱️ Raymond 的 K 線圖：全拖曳操作模式")
st.info("💡 操作提示：直接用滑鼠「按住左鍵」左右拖曳即可查看歷史。使用「滾輪」可放大縮小。")

# --- 樣式 1：TradingView 專業拖曳感 (最推薦) ---
st.header("1. 專業交易員模式 (Pan & Zoom)")
fig1 = go.Figure()
fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
fig1.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'))

fig1.update_layout(
    height=500,
    dragmode='pan', # 預設開啟拖曳模式
    xaxis_rangeslider_visible=False, # 隱藏滑桿，改用拖曳
    hovermode='x unified',
    template="plotly_dark",
    margin=dict(l=10, r=10, t=30, b=10)
)
st.plotly_chart(fig1, use_container_width=True)

# --- 樣式 2：雙圖連動拖曳 (K線 + 成交量) ---
st.header("2. 雙圖同步拖曳 (Price + Volume)")
fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
fig2.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
fig2.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color='gray', name='成交量'), row=2, col=1)

fig2.update_layout(
    height=600,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    showlegend=False,
    template="plotly_white"
)
st.plotly_chart(fig2, use_container_width=True)

# --- 樣式 3：高對比數據探索 (Altair 輕量版) ---
st.header("3. 輕量化網頁拖曳 (Altair - 修正版)")
# 修正 width='container' 避免報錯
base = alt.Chart(df).encode(x='Date:T').properties(width='container', height=350)
rule = base.mark_rule().encode(y='Low:Q', y2='High:Q', color=alt.condition("datum.Open <= datum.Close", alt.value("#06982d"), alt.value("#ae1325")))
bar = base.mark_bar().encode(y='Open:Q', y2='Close:Q', color=alt.condition("datum.Open <= datum.Close", alt.value("#06982d"), alt.value("#ae1325")))

# Altair 的拖曳是透過 .interactive() 達成
chart3 = (rule + bar).interactive()
st.altair_chart(chart3, use_container_width=True)

# --- 樣式 4：專注短期波動 (Auto-Scale Focus) ---
st.header("4. 短期波動觀察 (Fixed Window)")
fig4 = go.Figure(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
# 設定初始顯示範圍（例如最後 30 天），但仍可拖曳看歷史
last_month = df['Date'].max() - pd.Timedelta(days=30)
fig4.update_layout(
    xaxis_range=[last_month, df['Date'].max()],
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    height=400
)
st.plotly_chart(fig4, use_container_width=True)

# --- 樣式 5：暗黑籌碼風格 (Dark Theme + Volume Overlay) ---
st.header("5. 暗黑籌碼模式 (Overlay)")
fig5 = go.Figure()
fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], yaxis='y2', marker_color='rgba(200,200,200,0.2)'))
fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
fig5.update_layout(
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    yaxis2=dict(overlaying='y', side='right', showgrid=False),
    template="none", # 潔淨風格
    height=400
)
st.plotly_chart(fig5, use_container_width=True)

# --- 樣式 6：多指標十字準心 ---
st.header("6. 全功能分析儀表板 (Crosshair + Pan)")
fig6 = go.Figure(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
fig6.update_xaxes(showspikes=True, spikecolor="gray", spikemode="across", spikesnap="cursor", showline=True)
fig6.update_yaxes(showspikes=True, spikecolor="gray", spikemode="across", spikesnap="cursor", showline=True)
fig6.update_layout(dragmode='pan', xaxis_rangeslider_visible=False, height=500, hovermode=False)
st.plotly_chart(fig6, use_container_width=True)
