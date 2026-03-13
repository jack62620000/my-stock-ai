import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

# 從 Secrets 讀取 Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Streamlit Cloud Settings 裡的 Secrets 設定 GEMINI_API_KEY")
    st.stop()

# 修正：使用最基礎的配置方式
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 數據獲取 (增加緩存與備案) ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_id):
    pure_id = ticker_id.replace(".TW", "").replace(".TWO", "")
    full_id = f"{pure_id}.TW"
    
    df = pd.DataFrame()
    info = {}
    
    # (A) yfinance：嘗試抓取股價
    try:
        stock = yf.Ticker(full_id)
        df = stock.history(period="6mo")
        info = stock.info
        if not df.empty:
            df['RSI'] = ta.rsi(df['Close'], length=14)
    except Exception:
        # yfinance 失敗時不報錯，交給 AI 處理缺失值
        pass

    # (B) FinMind：抓取籌碼 (這是備案，通常不會被封鎖)
    df_inst = pd.DataFrame()
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=pure_id, start_date=start_date)
    except:
        pass
    
    return df, df_inst, info

# --- 3. UI 佈局 ---
st.title("🤖 首席分析師：AI 投資報告")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    submit = st.button("生成深度報告", type="primary")

if submit:
    with st.spinner("🚀 正在收集數據並同步 AI 模型..."):
        df_data, df_inst, stock_info = get_stock_data(stock_code)
        
        # 整理基礎數據
        current_price = df_data['Close'].iloc[-1] if not df_data.empty else "數據受限"
        rsi_val = df_data['RSI'].iloc[-1] if not df_data.empty and 'RSI' in df_data.columns else "未知"
        
        f_net = "無數據"
        if not df_inst.empty and 'Foreign_Investor_Buy' in df_inst.columns:
            last_5 = df_inst.tail(5)
            f_net = last_5['Foreign_Investor_Buy'].sum() - last_5['Foreign_Investor_Sell'].sum()

        # 建立專門針對 404 錯誤修正的 Prompt
        prompt = f"分析台股 {stock_code}。目前股價: {current_price}, RSI: {rsi_val}, 五日外資買賣超: {f_net}。請針對全球局勢、內在價值、動能判斷、法人目標預估、策略建議進行分析。"

        try:
            # 【關鍵修復】: 嘗試多種模型名稱以避開 404
            try:
                model = genai.GenerativeModel('gemini-1.5-flash-latest') # 優先嘗試最新標籤
            except:
                model = genai.GenerativeModel('gemini-1.5-flash') # 退而求其次
            
            response = model.generate_content(prompt)
            
            st.markdown(f"## 📊 {stock_code} 綜合研究報告")
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"❌ AI 呼叫失敗。這通常是 API Key 權限或模型名稱變更。")
            st.write(f"系統錯誤資訊: {e}")
