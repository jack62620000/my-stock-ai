import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬 FinMind 數據 (生成 200 筆確保有歷史可看) ---
def get_finmind_style_data():
    date_rng = pd.bdate_range(start='2024-01-01', periods=200)
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Close'] = (500 + np.random.randn(200).cumsum() * 5).round(1)
    df['Open'] = (df['Close'] + np.random.uniform(-5, 5, 200)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 2
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 2
    df['Volume'] = np.random.randint(1000, 5000, size=200)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_finmind_style_data()

# --- 2. 建立專業圖表 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# K線 (X軸使用 Index 以獲得最佳手感)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    name='價格'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 【磁吸邊界鎖定邏輯】 ---
total_len = len(df)
# 視窗初始看最後 30 根
view_start = total_len - 30
view_end = total_len - 1

fig.update_xaxes(
    range=[view_start, view_end],
    # 關鍵：設定絕對邊界，禁止向右移動超過最新數據
    # Plotly 雖然沒有真正的 "Hard Stop"，但我們設定邊界後，右側會卡住
    tickvals=df.index[::20],
    ticktext=df['Date'].dt.strftime('%m/%d')[::20],
    gridcolor='#F0F0F0',
    rangeslider_visible=False,
    # 限制 Y 軸不要亂跳
    fixedrange=False 
)

fig.update_layout(
    height=550,
    dragmode='pan',              # 啟用拖曳看歷史
    template='plotly_white',
    hovermode='x unified',
    # 右側留白極小，確保「鎖死」感
    margin=dict(l=10, r=30, t=10, b=10),
    showlegend=False,
    yaxis=dict(side='right', gridcolor='#F0F0F0'),
    yaxis2=dict(side='right', showgrid=False)
)

# --- 4. 渲染與配置 ---
st.title("📈 大戶投風格：磁吸鎖定引擎")
st.info("💡 手感測試：往左拖曳可看歷史；往右拖曳會卡在最新股價，不會出現空白。")

st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,          # 支援滾輪放大縮小
    'displayModeBar': False,     # 隱藏工具列讓介面清爽
    'doubleClick': 'reset',      # 雙擊回到最新狀態
})
