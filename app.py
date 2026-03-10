import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 模擬 FinMind 高密度數據 ---
def get_pro_locked_data():
    date_rng = pd.bdate_range(start='2024-01-01', periods=200)
    df = pd.DataFrame(date_rng, columns=['Date'])
    df['Close'] = (500 + np.random.randn(200).cumsum() * 5).round(1)
    df['Open'] = (df['Close'] + np.random.uniform(-5, 5, 200)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 2
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 2
    df['Volume'] = np.random.randint(1000, 5000, size=200)
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    return df

df = get_pro_locked_data()
total_len = len(df)

# --- 2. 建立圖表 ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.75, 0.25])

# K線 - 這裡 X 軸改用數字索引，是為了讓邊界計算精準到像素級
fig.add_trace(go.Candlestick(
    x=list(range(total_len)), # 數字索引
    open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B',
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A',
    name='價格'
), row=1, col=1)

# 成交量
fig.add_trace(go.Bar(x=list(range(total_len)), y=df['Volume'], marker_color=df['Color'], name='成交量'), row=2, col=1)

# --- 3. 【硬性邊界鎖定代碼】 ---
# 設定視窗範圍：只顯示最後 30 根
# 關鍵：range 必須精確對齊數據索引的邊界
view_start = total_len - 30.5
view_end = total_len - 0.5 

fig.update_xaxes(
    range=[view_start, view_end],
    # 限制拖曳區間：禁止顯示索引 0 以下或總長度以上的區域
    # 這是 Plotly 中最接近「硬性撞牆」的參數組合
    autorange=False,
    fixedrange=False,
    constrain='domain', 
    tickvals=list(range(0, total_len, 20)),
    ticktext=df['Date'].dt.strftime('%m/%d')[::20],
    gridcolor='#F5F5F5'
)

fig.update_layout(
    height=550,
    dragmode='pan',
    template='plotly_white',
    hovermode='x unified',
    # 右側 margin 設為 0 是為了讓最新股價與 y 軸標籤「死鎖」在一起
    margin=dict(l=5, r=5, t=10, b=10),
    showlegend=False,
    yaxis=dict(side='right', gridcolor='#F5F5F5', autorange=True, fixedrange=False),
    yaxis2=dict(side='right', showgrid=False, fixedrange=True)
)

# --- 4. 配置顯示 ---
st.title("🛡️ 完勝版：大戶投「硬邊界」引擎")
st.info("💡 手感測試：現在往右拉，最新一根 K 線會死死卡在右側邊緣，絕不產生空白空間。")

st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': False,
    'showAxisDragHandles': False, # 禁止拖動軸來產生空白
})
