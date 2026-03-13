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
# 2. Gemini API 初始化（新 SDK，關鍵）
# ===============================
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

# ⭐ 一定要在最上層定義（不能放進 if / try / function）
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ===============================
# 3. 資料抓取（含備援）
# ===============================
@st.cache_data(ttl=3600)
def get_stock_data(stock_id: str):
    pure_id = stock_id.replace(".TW", "").replace(".TWO", "")
    yf_id = f"{pure_id}.TW"

    df_price = pd.DataFrame()
    stock_info = {}
    df_inst = pd.DataFrame()

    # --- Yahoo Finance（價格 & 技術指標）---
    try:
        ticker = yf.Ticker(yf_id)
        df_price = ticker.history(period="6mo")

        if not df_price.empty:
            df_price["RSI"] = ta.rsi(df_price["Close"], length=14)
            stock_info = ticker.info
    except Exception:
        pass

    # --- FinMind（法人籌碼）---
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        df_inst = dl.taiwan_stock_institutional_investors(
            stock_id=pure_id,
            start_date=start_date
        )
    except Exception:
        pass

    return df_price, df_inst, stock_info


# ===============================
# 4. 側邊欄
# ===============================
with st.sidebar:
    stock_code = st.text_input("輸入台股代號（例如 2330）", value="2330")
    submit = st.button("🚀 生成深度分析報告", type="primary")


# ===============================
# 5. 主流程
# ===============================
if submit:
    with st.spinner("📡 收集市場資料並啟動 AI 分析中..."):
        df_price, df_inst, stock_info = get_stock_data(stock_code)

        # --- 價格 ---
        if not df_price.empty:
            current_price = round(df_price["Close"].iloc[-1], 2)
            rsi_val = round(df_price["RSI"].iloc[-1], 2)
        else:
            current_price = "無法取得"
            rsi_val = "N/A"

        # --- 外資五日買賣超 ---
        foreign_net = "無資料"
        if not df_inst.empty:
            try:
                foreign_net = (
                    df_inst["Foreign_Investor_Buy"].tail(5).sum()
                    - df_inst["Foreign_Investor_Sell"].tail(5).sum()
                )
                foreign_net = int(foreign_net)
            except Exception:
                pass

        # ===============================
        # 6. Prompt
        # ===============================
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

        # ===============================
        # 7. Gemini AI 分析（v1 API，穩定）
        # ===============================
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 1200,
                }
            )

            st.markdown(f"## 📊 {stock_code} AI 綜合研究報告")
            st.markdown(response.text)

        except Exception as e:
            st.error("❌ Gemini v1 API 呼叫失敗")
            st.exception(e)
