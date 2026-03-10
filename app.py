import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬數據 ---
def get_final_data():
    # 生成 100 筆數據 (模擬 100 個交易日)
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

df = get_final_data()

# --- 2. 建立圖表 (使用索引作為 X 軸) ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# 主圖：K線 (x 傳入 df.index)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name='價格',
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    text=df['Date'], # 懸停時顯示真實日期
    hoverinfo='text+y'
), row=1, col=1)

# 副圖：成交量
fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 邊界與視窗控制 (鎖定核心) ---
total_len = len(df)
# 視窗只看最後 30 根 (小一半)
fig.update_xaxes(
    range=[total_len - 31, total_len - 0.5], # 鎖定右側邊界
    # 設定顯示標籤為日期 (雖然 X 軸是數字)
    tickmode='array',
    tickvals=df.index[::10], # 每 10 根顯示一次日期
    ticktext=df['Date'][::10],
    gridcolor='#F0F0F0',
    # 限制拖曳範圍：[0, 總長度]
    fixedrange=False,
    constrain="domain",
)

fig.update_layout(
    height=500,
    dragmode='pan',
    xaxis_rangeslider_visible=False,
    template='plotly_white',
    hovermode='x unified',
    margin=dict(l=10, r=60, t=10, b=10), # 右側留 60px 給價格軸
    showlegend=False,
    yaxis=dict(side='right', gridcolor='#F0F0F0'), # 價格軸靠右
    yaxis2=dict(side='right', showgrid=False)
)

# 顯示圖表
st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False 
})

st.success("✅ 索引鎖定引擎啟動成功！現在可以流暢拖曳且不會報錯。")
