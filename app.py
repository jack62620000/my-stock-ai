import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ===============================
# 1. 核心設定與 API Key 讀取
# ===============================
st.set_page_config(page_title="量化數據終端", layout="wide")

# 從 Secrets 讀取 Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 未在 Secrets 中找到 GEMINI_API_KEY，請檢查設定。")
    st.stop()

GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_KEY)

# ===============================
# 2. 數據抓取函式 (純數據)
# ===============================
@st.cache_data(ttl=3600)
def get_quant_data(stock_id: str):
    # 格式化代號 (支援 2330 直接輸入)
    ticker_id = f"{stock_id.replace('.TW', '')}.TW"
    try:
        ticker = yf.Ticker(ticker_id)
        df = ticker.history(period="1y")
        if df.empty: return None, None
        
        # 計算量化指標
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
            "乖離率%": ((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100
        }
        return metrics, df.tail(10)
    except:
        return None, None

# ===============================
# 3. UI 介面佈局
# ===============================
st.title("🛡️ 量化價值決策終端")

with st.sidebar:
    st.header("參數設定")
    stock_input = st.text_input("輸入台股代號", value="2330")
    # 提供模型備案
    target_model = st.selectbox("首選 AI 模型", ["gemini-2.0-flash", "gemini-1.5-flash"])
    run_btn = st.button("開始量化分析", type="primary")

if run_btn:
    data, history = get_quant_data(stock_input)
    
    if data:
        # 第一層：即時數據看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前股價", f"{data['現價']:.2f}")
        c2.metric("本益比 PE", f"{data['PE']:.2f}")
        c3.metric("淨值比 PB", f"{data['PB']:.2f}")
        c4.metric("殖利率", f"{data['殖利率']:.2f}%")

        st.divider()

        # 第二層：AI 決策總結 (核心重點)
        st.subheader("🤖 AI 首席決策總結")
        
        prompt = f"""
        請以華倫巴菲特的價值投資視角分析：
        股票：{data['名稱']} ({stock_input})
        數據：PE={data['PE']}, PB={data['PB']}, 殖利率={data['殖利率']:.2f}%, RSI={data['RSI14']:.2f}。
        請直接給出「投資建議（買進/觀望/賣出）」並分點說明理由。
        """

        try:
            # 嘗試使用首選模型
            response = client.models.generate_content(model=target_model, contents=prompt)
            st.success(response.text)
        except Exception as e:
            if "429" in str(e):
                st.warning(f"⚠️ {target_model} 額度耗盡，嘗試自動備案...")
                # 自動嘗試另一個模型
                fallback_model = "gemini-1.5-flash" if target_model == "gemini-2.0-flash" else "gemini-2.0-flash"
                try:
                    response = client.models.generate_content(model=fallback_model, contents=prompt)
                    st.success(f"(由 {fallback_model} 生成):\n\n" + response.text)
                except:
                    st.error("❌ 所有模型額度皆已耗盡，請 1 分鐘後再試。")
            else:
                st.error(f"AI 生成出錯: {e}")

        st.divider()

        # 第三層：純數據表格
        col_list, col_table = st.columns([1, 2])
        with col_list:
            st.subheader("📋 量化指標清單")
            st.table(pd.DataFrame([data]).T.rename(columns={0: "數值"}))
        with col_table:
            st.subheader("📅 近 10 日交易數據")
            st.dataframe(history[['Open', 'High', 'Low', 'Close', 'Volume']].style.format("{:.2f}"))
            
    else:
        st.error("無法抓取數據，請確認代號是否正確。")
