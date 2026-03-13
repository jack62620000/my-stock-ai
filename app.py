import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ===============================
# 1. 基礎設定與模型初始化
# ===============================
st.set_page_config(page_title="量化數據終端", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 改良版的模型偵測邏輯
@st.cache_resource
def get_best_models():
    try:
        # 獲取所有模型名稱
        all_models = [m.name for m in client.models.list()]
        # 過濾出 gemini 系列並排序（優先讓 flash 排前面，因為速度快且額度高）
        gemini_models = [m for m in all_models if "gemini" in m.lower()]
        
        # 排序邏輯：將 2.0-flash 或 1.5-flash 排在最前面
        gemini_models.sort(key=lambda x: ("flash" not in x, "2.0" not in x))
        
        return gemini_models
    except Exception as e:
        st.error(f"❌ 無法取得可用模型清單：{e}")
        return []

AVAILABLE_MODELS = get_best_models()

# ===============================
# 2. 數據處理 (純數據)
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
            "RSI14": df['RSI'].iloc[-1] if not df['RSI'].empty else 0,
            "乖離率%": ((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100 if not df['MA20'].empty else 0
        }
        return metrics, df.tail(10)
    except:
        return None, None

# ===============================
# 3. UI 介面
# ===============================
st.title("📊 量化數據終端 (自動模型匹配版)")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if AVAILABLE_MODELS:
        st.success(f"✅ 偵測到 {len(AVAILABLE_MODELS)} 個可用模型")
        # 讓使用者知道目前預設用哪一個，也可以手動選
        selected_model = st.selectbox("偏好模型", AVAILABLE_MODELS)
    else:
        st.error("⚠️ 無可用模型，請檢查 API Key")
    run_btn = st.button("執行分析", type="primary")

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

        # 第二層：AI 決策總結 (核心)
        st.subheader("🤖 AI 首席決策總結")
        prompt = f"分析台股 {data['名稱']}({stock_input}): PE={data['PE']}, PB={data['PB']}, RSI={data['RSI14']:.2f}。請給出投資評等與理由。"
        
        status_box = st.empty()
        status_box.info("📡 正在調用模型進行分析...")

        # 這裡加入你的自動模型匹配邏輯
        success = False
        # 優先用選定的模型，如果失敗則輪詢清單中其他模型
        try_list = [selected_model] + [m for m in AVAILABLE_MODELS if m != selected_model]
        
        for m_name in try_list:
            try:
                response = client.models.generate_content(model=m_name, contents=prompt)
                status_box.success(f"【推薦建議 - 由 {m_name} 生成】\n\n{response.text}")
                success = True
                break
            except Exception as e:
                if "429" in str(e):
                    status_box.warning(f"⚠️ {m_name} 額度滿了，正在嘗試下一個...")
                continue
        
        if not success:
            status_box.error("❌ 所有模型皆無法回應，可能是 API 額度已達每日上限。")

        st.divider()

        # 第三層：純數據表格
        st.subheader("📋 詳細量化指標與數據")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.table(pd.DataFrame([data]).T.rename(columns={0: "數據值"}))
        with col_b:
            st.dataframe(history[['Open', 'High', 'Low', 'Close', 'Volume']].style.format("{:.2f}"))
    else:
        st.error("查無數據。")
