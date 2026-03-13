import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

# 初始化配置
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 強化版數據抓取 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_id):
    pure_id = ticker_id.replace(".TW", "").replace(".TWO", "")
    full_id = f"{pure_id}.TW"
    
    df, info = pd.DataFrame(), {}
    
    # (A) yfinance：即便受限也不要讓程式崩潰
    try:
        stock = yf.Ticker(full_id)
        df = stock.history(period="6mo")
        info = stock.info
        if not df.empty:
            df['RSI'] = ta.rsi(df['Close'], length=14)
    except:
        pass

    # (B) FinMind：強大的籌碼備案
    df_inst = pd.DataFrame()
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=pure_id, start_date=start_date)
    except:
        pass
    
    return df, df_inst, info

# --- 3. UI 佈局 ---
st.title("🤖 首席分析師：AI 投資決策報告")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    submit = st.button("生成深度報告", type="primary")

if submit:
    with st.spinner("🚀 正在收集數據並啟動 AI 模型切換系統..."):
        df_data, df_inst, stock_info = get_stock_data(stock_code)
        
        # 整理數據
        price = df_data['Close'].iloc[-1] if not df_data.empty else "Yahoo 數據暫時受限"
        rsi_val = df_data['RSI'].iloc[-1] if not df_data.empty and 'RSI' in df_data.columns else "N/A"
        
        f_net = "無數據"
        if not df_inst.empty and 'Foreign_Investor_Buy' in df_inst.columns:
            f_net = df_inst['Foreign_Investor_Buy'].tail(5).sum() - df_inst['Foreign_Investor_Sell'].tail(5).sum()

        prompt = f"""
        分析台股 {stock_code}。目前價: {price}, RSI: {rsi_val}, 五日外資買賣超: {f_net}。
        請針對全球局勢、內在價值、動能判斷、法人目標預估、策略建議進行分析。
        """

        # --- 核心修復：模型名稱自動切換 ---
        success = False
        # 按照優先權嘗試不同的模型路徑
        model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content(prompt)
                
                # 若成功執行到這，顯示結果
                st.markdown(f"## 📊 {stock_code} 綜合研究報告")
                st.markdown(response.text)
                success = True
                break # 成功就跳出迴圈
            except Exception as e:
                continue # 失敗則嘗試下一個模型
        
        if not success:
            st.error("❌ 所有 AI 模型皆呼叫失敗。")
            st.info("解決建議：\n1. 前往 Google AI Studio 重新生成一組新的 API Key。\n2. 確認您在 GitHub 的 requirements.txt 中有 google-generativeai>=0.4.0")
