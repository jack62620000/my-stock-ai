import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股 AI 雲端決策系統", layout="wide")

# 套件自定義樣式
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stExpander"] { background-color: #f8f9fa; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 雲端資料同步設定 ---
# ⚠️ 請在此處替換成你的 Google Sheets 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/1WVDOUvbfBK59WPeXoV41FmvvwOsCmzMJ87HpqWtg6vk/edit?gid=0#gid=0"

@st.cache_data(ttl=600)  # 每 10 分鐘自動更新一次數據
def load_data_from_sheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=SHEET_URL)
        return data
    except Exception as e:
        st.error(f"雲端資料讀取失敗，請檢查網址與權限。錯誤: {e}")
        return pd.DataFrame(columns=["Ticker", "Cost", "Note"])

# --- 3. 核心運算函數 ---
def get_stock_analysis(symbol, cost_price=None):
    try:
        # 下載數據
        df = yf.download(symbol, period="1y", interval="1d")
        if df.empty: return None
        
        # 技術指標計算 (使用 pandas_ta)
        df.ta.stoch(high='High', low='Low', close='Close', k=9, d=3, append=True)
        df.ta.macd(close='Close', fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(close='Close', length=14, append=True)
        df.ta.atr(high='High', low='Low', close='Close', length=14, append=True)
        
        # 取得最新一筆數據
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 價值估算 (簡易 AI 模型)
        ticker_obj = yf.Ticker(symbol)
        info = ticker_obj.info
        
        # 自動判定估值模型 (P/E or P/B)
        industry = info.get('industry', '')
        is_pb_model = any(x in industry for x in ['Bank', 'Insurance', 'Shipping', 'Steel', 'Basic Materials'])
        
        if is_pb_model:
            intrinsic_v = info.get('bookValue', 0) * 1.3 # 假設合理 P/B 為 1.3
            model_type = "P/B"
        else:
            intrinsic_v = info.get('trailingEps', 0) * info.get('trailingPE', 15)
            model_type = "P/E"

        # 止損價計算 (ATR 2倍)
        stop_loss = curr['Close'] - (curr['ATRr_14'] * 2)
        
        # 趨勢診斷
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        trend = "🔥 多頭強勢" if curr['Close'] > ma20 else "⚠️ 趨勢轉弱"

        return {
            "df": df,
            "info": info,
            "price": curr['Close'],
            "intrinsic": intrinsic_v,
            "model_type": model_type,
            "k": curr['STOCHk_9_3_3'],
            "rsi": curr['RSI_14'],
            "macd_h": curr['MACDH_12_26_9'],
            "stop_loss": stop_loss,
            "trend": trend,
            "roi": ((curr['Close'] - cost_price) / cost_price * 100) if cost_price else None
        }
    except:
        return None

# --- 4. 主網頁介面 ---
st.title("📈 台股 AI 雲端全方位決策系統")

# 讀取雲端清單
df_cloud = load_data_from_sheets()

if df_cloud.empty:
    st.warning("目前雲端清單為空，請在 Google Sheets 加入股票代號（例如 2330.TW）。")
else:
    # 建立側邊欄摘要
    st.sidebar.subheader("☁️ 雲端同步狀態")
    st.sidebar.write(f"已載入 {len(df_cloud)} 檔追蹤個股")
    
    # 遍歷所有個股進行分析
    for index, row in df_cloud.iterrows():
        symbol = str(row['Ticker']).strip()
        cost = row['Cost'] if 'Cost' in df_cloud.columns and not pd.isna(row['Cost']) else 0
        
        res = get_stock_analysis(symbol, cost if cost > 0 else None)
        
        if res:
            with st.container():
                # 第一行：股票標題與狀態標籤
                c_title, c_tag = st.columns([3, 1])
                status_color = "green" if "強勢" in res['trend'] else "orange"
                c_title.markdown(f"### {symbol} - {res['info'].get('shortName', '')}")
                c_tag.markdown(f":{status_color}[**{res['trend']}**]")
                
                # 第二行：核心數據指標
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("當前股價", f"{res['price']:.2f}")
                m2.metric(f"AI 內在價值 ({res['model_type']})", f"{res['intrinsic']:.2f}")
                
                if res['roi'] is not None:
                    m3.metric("我的報酬率", f"{res['roi']:.2f}%", delta=f"{res['roi']:.2f}%")
                    m4.metric("建議止損位", f"{res['stop_loss']:.2f}")
                else:
                    m3.metric("KD (K值)", f"{res['k']:.1f}")
                    m4.metric("RSI (14)", f"{res['rsi']:.1f}")

                # 警示訊息
                if res['roi'] is not None and res['price'] < res['stop_loss']:
                    st.error(f"🚨 停損警告：股價已低於 ATR 動態止損位 {res['stop_loss']:.2f}，請嚴守紀律！")

                # 第三行：圖表與評論
                with st.expander("📊 查看技術圖表與 AI 綜合評論"):
                    # Plotly K線圖
                    fig = go.Figure(data=[go.Candlestick(
                        x=res['df'].index, 
                        open=res['df']['Open'], 
                        high=res['df']['High'], 
                        low=res['df']['Low'], 
                        close=res['df']['Close'],
                        name="K線"
                    )])
                    # 加入月線 (MA20)
                    ma20_line = res['df']['Close'].rolling(20).mean()
                    fig.add_trace(go.Scatter(x=res['df'].index, y=ma20_line, name="月線", line=dict(color='orange', width=1.5)))
                    
                    fig.update_layout(height=400, margin=dict(l=0, r=0, b=0, t=30), xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # AI 評論
                    buy_signal = "具備安全邊際" if res['price'] < res['intrinsic'] else "股價偏高"
                    tech_signal = "動能轉強" if res['macd_h'] > 0 else "動能疲弱"
                    st.info(f"🤖 **AI 診斷報告**：目前價值面 **{buy_signal}**，技術面指標顯示 **{tech_signal}**。建議：{'偏多操作' if res['macd_h'] > 0 and res['price'] < res['intrinsic'] else '暫時觀望'}。")

                st.markdown("---")