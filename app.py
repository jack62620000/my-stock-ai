import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ===============================
# 1. 初始化與 Secrets 檢查
# ===============================
st.set_page_config(page_title="量化數據終端", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ===============================
# 2. 自動取得可用模型清單
# ===============================
@st.cache_resource
def get_available_models():
    try:
        # 獲取所有支援 generateContent 的模型
        models = client.models.list()
        # 過濾出 flash 系列（速度快、適合量化分析）
        valid_models = [m.name for m in models if "generateContent" in m.supported_methods]
        return valid_models
    except Exception as e:
        st.error(f"無法獲取模型清單: {e}")
        return []

# ===============================
# 3. 數據處理
# ===============================
@st.cache_data(ttl=3600)
def get_quant_data(stock_id: str):
    ticker_id = f"{stock_id.replace('.TW', '').replace('.TWO', '')}.TW"
    try:
        ticker = yf.Ticker(ticker_id)
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
            "乖離率%": ((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100 if not df['MA20'].empty else 0
        }
        return metrics, df.tail(10)
    except:
        return None, None

# ===============================
# 4. UI 介面
# ===============================
st.title("🛡️ 量化價值決策核心 (自動修復版)")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("啟動量化分析", type="primary")
    
    available_models = get_available_models()
    if available_models:
        st.success(f"偵測到 {len(available_models)} 個可用模型")
    else:
        st.error("此 API Key 目前無可用模型")

if run_btn:
    data, history = get_quant_data(stock_input)
    
    if data:
        # 第一層：數據看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前股價", f"{data['現價']:.2f}")
        c2.metric("本益比 PE", f"{data['PE']:.2f}")
        c3.metric("淨值比 PB", f"{data['PB']:.2f}")
        c4.metric("殖利率", f"{data['殖利率']:.2f}%")

        st.divider()

        # 第二層：AI 總結 (具備自動輪詢重試機制)
        st.subheader("🤖 AI 首席決策總結")
        
        prompt = f"分析台股 {data['名稱']}({stock_input}): PE={data['PE']}, PB={data['PB']}, RSI={data['RSI14']:.2f}。請給出投資建議與理由。"
        
        summary_placeholder = st.empty()
        summary_placeholder.info("⏳ 正在嘗試最適合的模型...")
        
        success = False
        # 這裡會按照模型清單一個一個試，直到成功
        for model_name in available_models:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                summary_placeholder.success(f"推薦建議 (由 {model_name} 生成):\n\n{response.text}")
                success = True
                break # 成功就跳出迴圈
            except Exception as e:
                continue # 失敗就試下一個
        
        if not success:
            summary_placeholder.error("❌ 所有可用模型皆暫時無法回應（額度耗盡或區域限制），請稍後再試。")

        st.divider()

        # 第三層：純數據展示
        col_list, col_table = st.columns([1, 2])
        with col_list:
            st.subheader("📋 量化指標清單")
            st.table(pd.DataFrame([data]).T.rename(columns={0: "數值"}))
        with col_table:
            st.subheader("📅 近 10 日交易數據")
            st.dataframe(history[['Open', 'High', 'Low', 'Close', 'Volume']].style.format("{:.2f}"))
            
    else:
        st.error("查無數據。")
