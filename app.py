import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta
import requests

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

# 從 Secrets 讀取 Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# 初始化 Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 繞過封鎖與修正模型報錯 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_id):
    pure_id = ticker_id.replace(".TW", "").replace(".TWO", "")
    full_id = f"{pure_id}.TW"
    
    # 模擬瀏覽器標頭
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    
    df = pd.DataFrame()
    info = {}
    
    # (A) yfinance 抓取 (加上錯誤處理)
    try:
        stock = yf.Ticker(full_id)
        # 嘗試抓取 6 個月的數據以減少被封鎖機率
        df = stock.history(period="6mo")
        info = stock.info
        
        if not df.empty:
            df['RSI'] = ta.rsi(df['Close'], length=14)
            # 簡化指標計算，避免呼叫過多導致報錯
            macd = ta.macd(df['Close'])
            if macd is not None:
                df = pd.concat([df, macd], axis=1)
    except Exception as e:
        st.warning(f"⚠️ yfinance 存取受限。")

    # (B) FinMind 抓取 (法人籌碼)
    df_inst = pd.DataFrame()
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=pure_id, start_date=start_date)
    except Exception as e:
        pass
    
    return df, df_inst, info

# --- 3. 生成 Prompt ---
def generate_cio_report(ticker, df, df_inst, info):
    # 提取數據，若缺失則給予預設值
    price = df['Close'].iloc[-1] if not df.empty else "無法取得即時價"
    rsi_val = df['RSI'].iloc[-1] if not df.empty and 'RSI' in df.columns else "N/A"
    
    f_net, t_net = "無數據", "無數據"
    if not df_inst.empty:
        last_5 = df_inst.tail(5)
        if 'Foreign_Investor_Buy' in last_5.columns:
            f_net = last_5['Foreign_Investor_Buy'].sum() - last_5['Foreign_Investor_Sell'].sum()
            t_net = last_5['Investment_Trust_Buy'].sum() - last_5['Investment_Trust_Sell'].sum()

    prompt = f"""
    你是一位精通台股的量化投資分析師。
    股票代號：{ticker}，目前參考股價：{price}
    技術指標：RSI={rsi_val}
    籌碼面：近五日外資買賣超 {f_net}，投信買賣超 {t_net}
    
    請針對以下五點進行深度分析（若數據不足，請以 2026 年最新市場趨勢進行推理）：
    1. 🌍【全球局勢與宏觀風險分析】
    2. 💎【內在價值審查分析】
    3. 📉【股價走勢與動能判斷】
    4. 🎯【法人目標價與時間預估】
    5. 📈【終極投資策略建議】
    """
    return prompt

# --- 4. Streamlit UI ---
st.title("🤖 首席分析師：AI 投資決策報告")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號 (如: 2330)", value="2330")
    submit = st.button("生成深度報告", type="primary")

if submit:
    with st.spinner("🚀 正在收集數據並啟動 AI 推理..."):
        df_data, df_inst, stock_info = get_stock_data(stock_code)
        
        final_prompt = generate_cio_report(stock_code, df_data, df_inst, stock_info)
        
        try:
            # 修正模型名稱呼叫方式
            model = genai.GenerativeModel('gemini-1.5-flash')
            # 這裡不使用 v1beta 標籤，直接用最標準的 generate_content
            response = model.generate_content(final_prompt)
            
            st.markdown(f"## 📊 {stock_code} 綜合研究報告")
            st.markdown(response.text)
            st.divider()
        except Exception as e:
            st.error(f"❌ AI 服務目前無法回應。錯誤訊息: {e}")
            st.info("建議：請檢查 API Key 是否正確，或是稍後再試。")
