import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬數據 (使用較大範圍以利測試) ---
def get_pro_locked_data():
    date_rng = pd.bdate_range(start='2024-01-01', periods=250)
    df = pd.DataFrame(date_rng, columns=['Date'])
    # 產生更有波動感的股價
    df['Close'] = (500 + np.random.randn(250).cumsum() * 7).round(1)
    df['Open'] = (df['Close'] + np.random.uniform(-8, 8, 250)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 5
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 5
    df['Volume'] = np.random.randint(1000, 8000, size=250)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_pro_locked_data()
total_len = len(df)

# --- 2. 建立圖表 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.75, 0.25])

# K線
fig.add_trace(go.Candlestick(
    x=list(range(total_len)),
    open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    name='價格'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=list(range(total_len)), y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 【鎖定與自動平分邏輯】 ---
view_start = total_len - 40  # 初始看 40 根
view_end = total_len - 0.5

fig.update_xaxes(
    range=[view_start, view_end],
    autorange=False,
    constrain='domain',
    # 自動平分 X 軸線：讓標籤根據範圍自動計算，避免重疊或太稀疏
    nticks=10, 
    tickvals=list(range(0, total_len, 10)),
    ticktext=df['Date'].dt.strftime('%m/%d')[::10],
    gridcolor='#F0F0F0',
    rangeslider_visible=False # 移除下方滑桿，改用滑鼠直接拖曳與滾輪縮放
)

fig.update_yaxes(
    side='right',
    gridcolor='#F0F0F0',
    # 【關鍵：解決數據移到視窗外】
    # fixedrange=False 表示 Y 軸可以動，但 autorange 會確保它始終包覆數據
    fixedrange=False, 
    autorange=True, 
)

# --- 4. 佈局細節優化 ---
fig.update_layout(
    height=600,
    dragmode='pan',
    template='plotly_white',
    hovermode='x unified',
    margin=dict(l=10, r=50, t=10, b=10),
    showlegend=False,
)

# --- 5. 顯示 ---
st.title("📈 大戶投專業版：動態錨定縮放")
st.info("💡 手感測試：\n1. 用「滾輪」放大縮小，Y 軸會自動調整高度讓 K 線永遠在畫面中。\n2. 往右拉到底會自動鎖定，絕不產生空白區。")

st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,           # 開啟滾輪縮放
    'displayModeBar': False,      # 隱藏工具列
    'doubleClick': 'reset',       # 雙擊回歸初始狀態
    'showAxisDragHandles': False  # 防止拉動座標軸產生空白
})
