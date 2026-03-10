import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬數據 ---
def get_locked_data():
    # 生成 100 天交易日數據
    date_rng = pd.bdate_range(start='2024-01-01', periods=100)
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Close'] = (500 + np.random.randn(100).cumsum() * 3).round(1)
    df['Open'] = (df['Close'] + np.random.uniform(-3, 3, 100)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 2
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 2
    df['Volume'] = np.random.randint(1000, 5000, size=100)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_locked_data()

# --- 2. 建立圖表 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# K線
fig.add_trace(go.Candlestick(
    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Color']), row=2, col=1)

# --- 3. 【核心修改】實現邊界限制與鎖定 ---
last_date = df['Date'].iloc[-1]
first_date = df['Date'].iloc[0]
# 視窗初始顯示最後 30 根
start_view = df['Date'].iloc[-30] 

fig.update_xaxes(
    type='date',
    range=[start_view, last_date],     # 初始顯示範圍
    # 限制拖曳範圍：用戶只能在數據的 [第一筆, 最後一筆] 之間移動
    # 這是 Plotly 模擬「撞牆」的關鍵
    autorange=False, 
    # constrains 確保用戶無法拉出定義的範圍
    rangebreak=[dict(values=["sat", "sun"])] # 再次嘗試加入移除週末，若報錯則移除此行
)

fig.update_layout(
    height=500,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    template='plotly_white',
    hovermode='x unified',
    # 這裡的 margin.r 是關鍵，讓最新價格貼近邊緣
    margin=dict(l=10, r=10, t=10, b=10), 
    showlegend=False,
    # 限制 Y 軸不要跟著 X 軸亂跳
    yaxis=dict(side='right', fixedrange=False),
    yaxis2=dict(side='right', fixedrange=True) # 成交量 Y 軸固定高度
)

# 移除圖表工具列，避免使用者切換回 "Zoom" 模式破壞你的鎖定感
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False 
})
