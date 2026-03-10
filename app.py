import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 模擬資料與均線計算 (延用之前邏輯) ---
def get_pro_data():
    date_rng = pd.date_range(start='2024-01-01', periods=200, freq='D')
    df = pd.DataFrame(date_rng, columns=['Date'])
    # 生成有起伏的股價
    df['Close'] = 500 + np.random.randn(200).cumsum() * 5
    df['Open'] = df['Close'] + np.random.uniform(-5, 5, 200)
    df['High'] = df[['Open', 'Close']].max(axis=1) + np.random.uniform(0, 3, 200)
    df['Low'] = df[['Open', 'Close']].min(axis=1) - np.random.uniform(0, 3, 200)
    df['Volume'] = np.random.randint(2000, 8000, size=200)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_pro_data()
df['MA5'] = df['Close'].rolling(5).mean()
df['MA20'] = df['Close'].rolling(20).mean()

# --- 圖表設定 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.02, row_heights=[0.75, 0.25])

# K線與均線 (略，同前一段代碼)
fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                             increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
                             decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A'), row=1, col=1)
fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], name='20MA', line=dict(color='#2196F3', width=1.2)), row=1, col=1)
fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Color']), row=2, col=1)

# --- 關鍵：視窗大小與邊界限制 ---
last_date = df['Date'].max()
first_date_in_data = df['Date'].min()
# 1. 視窗小一半：預設只顯示最後 30 天 (原為 60)
view_start_date = last_date - pd.Timedelta(days=30) 

fig.update_xaxes(
    range=[view_start_date, last_date],           # 初始視窗範圍
    # 2. 限制左側拖曳：設定最小與最大可移動範圍
    rangebreak=[dict(values=["sat", "sun"])],     # 移除週末空隙 (專業感提升)
    constrain="domain",
    # 限制使用者不能拉出數據範圍
    autorange=False, 
    fixedrange=False # 允許拖曳，但我們會透過自定義 UI 或 logic 限制，Plotly 原生限制較難
)

# 3. 視覺優化：鎖定視窗感覺
fig.update_layout(
    height=600,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    hovermode='x unified',
    template='plotly_white',
    margin=dict(l=10, r=50, t=10, b=10), # 右側留白 50px 像大戶投一樣
)

# 為了實現真正的「撞牆」效果，我們在 Plotly Config 關閉超出範圍的滾動
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False, # 隱藏工具列讓視覺更清爽
})
