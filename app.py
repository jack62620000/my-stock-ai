import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬專業數據 (增加數據量以測試拖曳) ---
def get_clean_data():
    # 生成 300 天數據，模擬足夠的歷史供拖曳
    date_rng = pd.bdate_range(start='2024-01-01', periods=250) # 使用 bdate 避開週末
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Close'] = (500 + np.random.randn(250).cumsum() * 3).round(1)
    df['Open'] = (df['Close'] + np.random.uniform(-3, 3, 250)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + np.random.uniform(0, 2, 250)
    df['Low'] = df[['Open', 'Close']].min(axis=1) - np.random.uniform(0, 2, 250)
    df['Volume'] = np.random.randint(1000, 9000, size=250)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    df['MA20'] = df['Close'].rolling(20).mean()
    return df

df = get_clean_data()

# --- 2. 建立專業圖表 ---
# 為了穩定性，我們移除 rangebreak，改用 bdate_range 預處理數據
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# 主圖：K線 (設定為台股配色)
fig.add_trace(go.Candlestick(
    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name='價格',
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A'
), row=1, col=1)

# 均線
fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], name='20MA', line=dict(color='#2196F3', width=1.5)), row=1, col=1)

# 副圖：成交量
fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 關鍵：鎖定右側與視窗縮小 ---
last_idx = len(df) - 1
start_idx = max(0, last_idx - 30) # 只顯示最後 30 個交易日，視窗小一半

# 取得對應日期
last_date = df['Date'].iloc[last_idx]
view_start_date = df['Date'].iloc[start_idx]

fig.update_xaxes(
    range=[view_start_date, last_date], # 鎖定初始視窗為最後 30 天
    showgrid=True, gridcolor='#F0F0F0',
    type='date' # 確保座標軸類型正確
)

# --- 4. 佈局優化 ---
fig.update_layout(
    height=600,
    dragmode='pan',              # 啟用拖曳
    xaxis_rangeslider_visible=False, 
    template='plotly_white',
    hovermode='x unified',
    margin=dict(l=10, r=50, t=10, b=10), # 右側留白 50px 鎖定感
    showlegend=False
)

fig.update_yaxes(showgrid=True, gridcolor='#F0F0F0', side='right') # 價格刻度放右邊，更大戶投

# 顯示圖表
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,          # 支援滾輪縮放
    'displayModeBar': False      # 隱藏工具列增加簡潔感
})
