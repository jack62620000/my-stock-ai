import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 模擬資料 (生成更具趨勢性的數據) ---
def get_pro_data():
    np.random.seed(42)
    date_rng = pd.date_range(start='2024-01-01', periods=120, freq='D')
    df = pd.DataFrame(date_rng, columns=['Date'])
    price = 500
    prices = []
    for _ in range(120):
        price += np.random.normal(1, 5)
        prices.append(price)
    df['Open'] = prices + np.random.normal(0, 2, 120)
    df['Close'] = df['Open'] + np.random.normal(0, 5, 120)
    df['High'] = df[['Open', 'Close']].max(axis=1) + np.random.uniform(0, 5, 120)
    df['Low'] = df[['Open', 'Close']].min(axis=1) - np.random.uniform(0, 5, 120)
    df['Volume'] = np.random.randint(2000, 8000, size=120)
    # 判斷漲跌顏色
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A') # 台股紅漲綠跌
    return df

df = get_pro_data()

# --- 計算均線 ---
df['MA5'] = df['Close'].rolling(5).mean()
df['MA20'] = df['Close'].rolling(20).mean()
df['MA60'] = df['Close'].rolling(60).mean()

st.set_page_config(layout="wide")
st.title("📈 Raymond 專業交易終端 (大戶投風格)")

# --- 建立專業圖表 ---
# rows=2, shared_xaxes=True 確保上下圖表拖曳同步
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.02, 
                    row_heights=[0.75, 0.25])

# 1. 主圖：K線
fig.add_trace(go.Candlestick(
    x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name='股價',
    increasing_line_color='#EB3B3B', increasing_fillcolor='#EB3B3B', # 漲：紅
    decreasing_line_color='#26A69A', decreasing_fillcolor='#26A69A', # 跌：綠
), row=1, col=1)

# 2. 疊加均線
fig.add_trace(go.Scatter(x=df['Date'], y=df['MA5'], name='5MA', line=dict(color='#FF9800', width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], name='20MA', line=dict(color='#2196F3', width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], name='60MA', line=dict(color='#9C27B0', width=1.5)), row=1, col=1)

# 3. 副圖：成交量 (顏色與漲跌連動)
fig.add_trace(go.Bar(
    x=df['Date'], y=df['Volume'], 
    marker_color=df['Color'], 
    name='成交量',
    opacity=0.8
), row=2, col=1)

# --- 4. 視覺細節優化 (這是關鍵) ---
fig.update_layout(
    height=700,
    template='plotly_white', # 乾淨白底
    dragmode='pan',          # 預設拖曳
    showlegend=False,
    xaxis_rangeslider_visible=False, # 隱藏滑桿
    # 設定十字準心
    hovermode='x unified',
    margin=dict(l=50, r=50, t=20, b=20),
)

# 優化座標軸格線 (淡化處理，像大戶投一樣)
fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0', zeroline=False)
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0', zeroline=False)

# 預設顯示最後 60 天數據
last_date = df['Date'].max()
first_date = last_date - pd.Timedelta(days=60)
fig.update_xaxes(range=[first_date, last_date])

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

st.markdown("""
### 💡 視覺化特色說明
* **台股配色**：紅色代表上漲，藍綠色代表下跌。
* **成交量對應**：下方量能柱顏色與上方 K 線同步，一眼看出是「帶量上漲」還是「帶量下跌」。
* **極簡網格**：模仿大戶投與 TradingView 的輕量化網格，不干擾視覺判斷。
* **縮放功能**：支援滑鼠滾輪縮放（Scroll Zoom），拖曳感非常順滑。
""")
