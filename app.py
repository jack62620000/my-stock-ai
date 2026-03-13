import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
import time

# ===============================
# 1. 初始化
# ===============================
st.set_page_config(page_title="量化數據終端", layout="wide")

# ===============================
# 2. 數據處理
# ===============================
@st.cache_data(ttl=3600)
def get_clean_data(stock_id: str):
    # 自動補齊台股後綴
    formatted_id = f"{stock_id.replace('.TW', '').replace('.TWO', '')}.TW"
    try:
        ticker = yf.Ticker(formatted_id)
        df = ticker.history(period="1y")
        if df.empty: return None, None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA20'] = ta.sma(df['Close'], length=20)
        
        info = ticker.info
        metrics = {
            "名稱": info.get("shortName", "未知"),
            "現價": df['Close'].iloc[-1],
            "PE": info.get("trailingPE", 0),
            "PB": info.get("priceToBook", 0),
            "殖利率": (info.get("dividendYield", 0) or 0) * 100,
            "RSI14": df['RSI'].iloc[-1],
            "MA20位階": ((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100 if not df['MA20'].empty else 0
        }
        return metrics, df.tail(10)
    except:
        return None, None

# ===============================
# 3. UI 介面
# ===============================
st.title("🛡️ 量化價值決策核心")

with st.sidebar:
    st.header("輸入參數")
    stock_input = st.text_input("台股代號", value="2330")
    api_key = st.text_input("Gemini API Key", type="password")
    # 讓使用者可以切換模型，防止單一模型額度用完
    model_choice = st.selectbox("選擇 AI 模型", ["gemini-1.5-flash", "gemini-2.0-flash"], index=0)
    run_btn = st.button("啟動量化分析", type="primary")

if run_btn:
    if not api_key:
        st.error("❌ 請輸入 API Key")
        st.stop()

    data, history = get_clean_data(stock_input)
    
    if data:
        # A. 數據看板
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("目前股價", f"{data['現價']:.2f}")
        col2.metric("本益比 PE", f"{data['PE']:.2f}")
        col3.metric("淨值比 PB", f"{data['PB']:.2f}")
        col4.metric("殖利率", f"{data['殖利率']:.2f}%")

        st.divider()

        # B. AI 總結（增加錯誤處理與重試邏輯）
        st.subheader("🤖 AI 首席決策總結")
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"分析台股 {data['名稱']}({stock_input}): PE {data['PE']}, PB {data['PB']}, 殖利率 {data['殖利率']:.2f}%, RSI {data['RSI14']:.2f}。請給出買賣建議與理由。"
            
            # 執行生成
            response = client.models.generate_content(model=model_choice, contents=prompt)
            st.success(response.text)
            
        except Exception as e:
            if "429" in str(e):
                st.warning("⚠️ AI 服務目前太忙碌（額度已滿）。請稍等 10 秒後再試，或嘗試切換至 gemini-1.5-flash 模型。")
                st.info("💡 小撇步：免費版 API 有每分鐘請求次數限制，請避免連續快速點擊按鈕。")
            else:
                st.error(f"AI 生成發生其他錯誤: {e}")

        st.divider()

        # C. 詳細數據
        st.subheader("📋 詳細量化指標")
        st.table(pd.DataFrame([data]).T.rename(columns={0: "數值"}))
    else:
        st.error("查無數據，請確認代號。")
