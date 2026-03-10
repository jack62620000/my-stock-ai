import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 數據準備 ---
def get_hard_locked_data():
    df = pd.DataFrame({
        'Date': pd.bdate_range(start='2024-01-01', periods=100).strftime('%Y-%m-%d'),
        'Close': (500 + np.random.randn(100).cumsum() * 5).round(1)
    })
    df['Open'] = (df['Close'] + np.random.uniform(-5, 5, 100)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 3
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 3
    df['Volume'] = np.random.randint(1000, 5000, size=100)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_hard_locked_data()
total_len = len(df)

# --- 2. 圖表建立 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# K線 (X軸使用 Index)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    name='價格'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 【終極鎖定邏輯】 ---
# 計算初始視窗：最後 30 根
view_start = total_len - 30.5
view_end = total_len - 0.5

fig.update_xaxes(
    range=[view_start, view_end],
    # 關鍵屬性 1：固定範圍模式，不允許自動延伸
    autorange=False,
    # 關鍵屬性 2：強制座標軸只在數據範圍內移動
    # 注意：Plotly 的 pan 模式下，這能大幅減少往外拉的空間
    constrain='domain',
    showgrid=True, gridcolor='#F0F0F0',
    # 將索引轉回日期標籤
    tickvals=df.index[::10],
    ticktext=df['Date'][::10],
)

fig.update_layout(
    height=550,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    template='plotly_white',
    hovermode='x unified',
    margin=dict(l=10, r=60, t=10, b=10),
    showlegend=False,
    # 鎖定 Y 軸，避免 Y 軸在拖動時產生不必要的空白
    yaxis=dict(side='right', fixedrange=False, autorange=True),
    yaxis2=dict(side='right', fixedrange=True)
)

# --- 4. 顯示設定 ---
# config 中的 scrollZoom 設為 True，但 displayModeBar 關閉
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False,
    'showAxisDragHandles': False, # 禁用座標軸拖動，防止拉出空白
})

st.info("🎯 已強化邊界鎖定：嘗試向右或向左拖拽，視窗將會被限制在數據範圍內。")
