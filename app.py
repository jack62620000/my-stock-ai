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

st.title("🤖 AI 股市首席分析報告")

# ===============================
# 2. Gemini API 初始化
# ===============================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 自動取得可用 Gemini 模型
try:
    available_models = client.models.list()
    gemini_models = [m.name for m in available_models if "gemini" in m.name]

    if not gemini_models:
        st.error("❌ 此 API Key 沒有任何可用的 Gemini 模型")
        st.stop()

    MODEL_NAME = gemini_models[0]  # 選第一個可用模型
    st.info(f"✅ 使用模型：{MODEL_NAME}")

except Exception as e:
    st.error("❌ 無法取得可用模型")
    st.exception(e)
    st.stop()

# ===============================
# 3. 抓取股票數據函式
# ===============================
@st.cache_data(ttl=3600)
def get_stock_data(stock_id: str):
    pure_id = stock_id.replace(".TW", "").replace(".TWO", "")
    yf_id = f"{pure_id}.TW"

    df_price = pd.DataFrame()
    df_inst = pd.DataFrame()

    # Yahoo Finance：價格 + RSI
    try:
        ticker = yf.Ticker(yf_id)
        df_price = ticker.history(period="6mo")
        if not df_price.empty:
            df_price["RSI"] = ta.rsi(df_price["Close"], length=14)
    except:
        pass

    # FinMind：法人籌碼
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
# 4. 側邊欄
# ===============================
with st.sidebar:
    stock_code = st.text_input("輸入台股代號（例如 2330）", value="2330")
    submit = st.button("🚀 生成 AI 分析報告", type="primary")

# ===============================
# 5. 主流程
# ===============================
if submit:
    with st.spinner("📡 收集資料並進行 AI 分析中..."):
        df_price, df_inst = get_stock_data(stock_code)

        # 股價與 RSI
        current_price = round(df_price["Close"].iloc[-1], 2) if not df_price.empty else "無資料"
        rsi_val = round(df_price["RSI"].iloc[-1], 2) if not df_price.empty else "N/A"

        # 外資五日買賣超
        foreign_net = "無資料"
        if not df_inst.empty:
            try:
                foreign_net = int(
                    df_inst["Foreign_Investor_Buy"].tail(5).sum() -
                    df_inst["Foreign_Investor_Sell"].tail(5).sum()
                )
            except:
                pass

        # AI 分析 prompt
        prompt = f"""
你是一位台股首席分析師，請針對以下股票進行專業投資分析：

股票代號：{stock_code}
目前股價：{current_price}
RSI 指標：{rsi_val}
近五日外資買賣超：{foreign_net}

請分段說明：
1. 全球與產業趨勢影響
2. 公司基本面與護城河
3. 技術面與動能判斷
4. 法人可能目標價區間（保守 / 中性 / 樂觀）
5. 操作策略建議（短線 / 中長線）

請用條列清楚、語氣專業、不誇大。
"""

        # 呼叫 Gemini AI
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 1200}
            )

            # 確保抓到完整文字
            if hasattr(response, "text"):
                ai_text = response.text
            elif hasattr(response, "candidates") and len(response.candidates) > 0:
                ai_text = response.candidates[0].content
            else:
                ai_text = str(response)

            st.markdown(f"## 📊 {stock_code} AI 投資分析報告")
            st.markdown(ai_text)

        except Exception as e:
            st.error("❌ Gemini 呼叫失敗")
            st.exception(e)
