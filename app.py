import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ===============================
# 1. 初始化與 API 設定
# ===============================
st.set_page_config(page_title="量化數據終端", layout="wide")

# 檢查 Secrets 或 Sidebar 中的 API Key
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None

# ===============================
# 2. 數據處理模組
# ===============================
@st.cache_data(ttl=3600)
def get_clean_data(stock_id: str):
    # 自動補齊台股後綴
    if not (stock_id.endswith(".TW") or stock_id.endswith(".TWO")):
        formatted_id = f"{stock_id}.TW"
    else:
        formatted_id = stock_id

    try:
        ticker = yf.Ticker(formatted_id)
        df = ticker.history(period="1y")
        if df.empty: return None, None
        
        # 技術指標
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        
        info = ticker.info
        metrics = {
            "名稱": info.get("shortName", "未知"),
            "現價": df['Close'].iloc[-1],
            "PE": info.get("trailingPE", 0),
            "PB": info.get("priceToBook", 0),
            "殖利率": (info.get("dividendYield", 0) or 0) * 100,
            "RSI14": df['RSI'].iloc[-1],
            "MA20位階": ((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100
        }
        return metrics, df.tail(10)
    except:
        return None, None

# ===============================
# 3. 介面佈局
# ===============================
st.title("🛡️ 量化價值決策核心")

with st.sidebar:
    st.header("輸入參數")
    stock_input = st.text_input("台股代號 (例: 2330)", value="2330")
    if not GEMINI_KEY:
        GEMINI_KEY = st.text_input("輸入 Gemini API Key", type="password")
    run_btn = st.button("啟動量化分析", type="primary")

if run_btn:
    if not GEMINI_KEY:
        st.error("❌ 缺少 API Key，無法生成 AI 總結。")
        st.stop()

    with st.spinner("正在提取量化指標..."):
        data, history = get_clean_data(stock_input)
        
        if data:
            # 第一層：數據看板
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("目前股價", f"{data['現價']:.2f}")
            col2.metric("本益比 PE", f"{data['PE']:.2f}")
            col3.metric("淨值比 PB", f"{data['PB']:.2f}")
            col4.metric("殖利率", f"{data['殖利率']:.2f}%")

            st.divider()

            # 第二層：AI 總結 (現在放在最前面)
            st.subheader("🤖 AI 首席決策總結")
            try:
                client = genai.Client(api_key=GEMINI_KEY)
                prompt = f"""
                你是華倫巴菲特的助手。請根據以下量化數據對 {data['名稱']}({stock_input}) 進行總結：
                1. 估值分析：PE {data['PE']}, PB {data['PB']}。
                2. 技術動能：RSI {data['RSI14']:.2f}, 偏離月線(MA20) {data['MA20位階']:.2f}%。
                3. 安全邊際：以此殖利率 {data['殖利率']:.2f}% 來看，是否具備防守性？
                請直接給出「買進、觀望、減持」的明確結論，並說明理由。
                """
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.success(response.text)
            except Exception as e:
                st.error(f"AI 總結生成失敗: {e}")

            st.divider()

            # 第三層：純數據列表
            st.subheader("📋 詳細量化指標")
            st.table(pd.DataFrame([data]).T.rename(columns={0: "數值"}))

            st.subheader("📅 近 10 日成交明細")
            st.dataframe(history[['Open', 'High', 'Low', 'Close', 'Volume']].style.format("{:.2f}"))
        else:
            st.error("查無數據，請確認代號是否正確。")
