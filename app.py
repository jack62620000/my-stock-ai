import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬數據 ---
def get_final_hard_locked_data():
    # 生成 100 天數據
    dates = pd.bdate_range(start='2024-01-01', periods=100).strftime('%Y-%m-%d').tolist()
    df = pd.DataFrame({
        'Date': dates,
        'Close': (500 + np.random.randn(100).cumsum() * 5).round(1)
    })
    df['Open'] = (df['Close'] + np.random.uniform(-5, 5, 100)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 3
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 3
    df['Volume'] = np.random.randint(1000, 5000, size=100)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_final_hard_locked_data()
total_len = len(df)

# --- 2. 建立圖表 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# K線 (X軸直接給字串日期，強制觸發 Category 模式)
fig.add_trace(go.Candlestick(
    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    name='價格'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 【硬鎖定邏輯】 ---
# 在 Category 模式下，我們設定 X 軸的顯示範圍
fig.update_xaxes(
    type='category',  # 這是關鍵：改為類別型
    range=[total_len - 30.5, total_len - 0.5], # 鎖定顯示最後 30 筆
    tickangle=0,
    nticks=10,
    showgrid=True,
    gridcolor='#F5F5F5',
    # 禁用縮放與拖曳到邊界外的行為 (在某些 Plotly 版本中有效)
    fixedrange=False, 
)

fig.update_layout(
    height=550,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    template='plotly_white',
    hovermode='x unified',
    margin=dict(l=10, r=60, t=10, b=10),
    showlegend=False,
    yaxis=dict(side='right', fixedrange=False, autorange=True),
    yaxis2=dict(side='right', fixedrange=True)
)

# --- 4. 終極配置：移除座標軸拖動把手 ---
# 這樣使用者就不能透過拉座標軸來製造空白
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False,
    'showAxisDragHandles': False, # 禁止拉扯座標軸
    'doubleClick': 'reset'        # 雙擊回歸初始鎖定視圖
})

st.warning("🛡️ 邊界警報：目前已使用 Category Axis 強制鎖定。若拖曳超出數據，Plotly 會因無索引可對應而停止產生空白刻度。")
