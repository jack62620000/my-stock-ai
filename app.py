import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
from google import genai
from datetime import datetime, timedelta

# ===============================
# 1. 基礎設定
# ===============================
st.set_page_config(
    page_title="AI 股市首席分析報告",
    layout="centered"
)

st.title("🤖 首席分析師：AI 投資決策報告")

# ===============================
# 2. Gemini API 初始化（新 SDK）
# ===============================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ===============================
# 3. 偵測可用模型（關鍵）
# ===============================
@st.cache_data
def get_available_model():
    """
    依優先順序選擇可用模型
    """
    preferred = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
        "models/gemini-1.0-pro",  # ✅ 幾乎 100% 可用
    ]

    available = [
        m.name for m in client.models.list()
        if "generateContent" in m.supported_generation_methods
    ]

    for p in preferred:
        if p in available:
            return p

    return None


MODEL_NAME = get_available_model()

if MODEL_NAME is None:
    st.error("❌ 此 API Key 沒有任何可用的 Gemini 模型")
    st.stop()

st.info(f"✅ 使用模型：{MODEL_NAME}")

# ===============================
# 4. 資料抓取
# ===============================
@st.cache_data(ttl=3600)
def get_stock_data(stock_id: str):
    pure_id = stock_id.replace(".TW", "").replace(".TWO", "")
    yf_id = f"{pure_id}.TW"

    df_price = pd.DataFrame()
    df_inst = pd.DataFrame()

    try:
        ticker = yf.Ticker(yf_id)
        df_price = ticker.history(period="6mo")
        if not df_price.empty:
            df_price["RSI"] = ta.rsi(df_price["Close"], length=14)
    except:
        pass

    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        df_inst = dl.taiwan_stock_institutional_investors(
            stock_id=pure_id,
            start_date=start_date
        )
    except:
        pass

    return df_price, df_inst


# ===============================
# 5. UI
# ===============================
with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    submit = st.button("🚀 生成深度分析報告", type="primary")


# ===============================
# 6. 主流程
# ===============================
if submit:
    with st.spinner("📡 收集資料並進行 AI 分析中..."):
        df_price, df_inst = get_stock_data(stock_code)

        price = df_price["Close"].iloc[-1] if not df_price.empty else "無資料"
        rsi = df_price["RSI"].iloc[-1] if not df_price.empty else "N/A"

        foreign_net = "無資料"
        if not df_inst.empty:
            foreign_net = int(
                df_inst["Foreign_Investor_Buy"].tail(5).sum()
                - df_inst["Foreign_Investor_Sell"].tail(5).sum()
            )

        prompt = f"""
你是一位台股首席分析師，請分析以下股票：

股票代號：{stock_code}
目前股價：{price}
RSI：{rsi}
近五日外資買賣超：{foreign_net}

請分段說明：
1. 產業與總體環境
2. 公司基本面
3. 技術面與動能
4. 法人合理目標價區間
5. 操作策略建議
"""

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 1200,
                }
            )

            st.markdown(f"## 📊 {stock_code} AI 投資分析報告")
            st.markdown(response.text)

        except Exception as e:
            st.error("❌ Gemini 呼叫失敗")
            st.exception(e)
