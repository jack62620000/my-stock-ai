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
    company_name = "未知公司"

    # Yahoo Finance：價格 + RSI + 公司名稱
    try:
        ticker = yf.Ticker(yf_id)
        df_price = ticker.history(period="6mo")
        company_name = ticker.info.get("shortName", company_name)
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

    return df_price, df_inst, company_name

# ===============================
# 4. 側邊欄
# ===============================
with st.sidebar:
    stock_code = st.text_input("輸入台股代號（例如 2330）", value="2356")
    submit = st.button("🚀 生成 AI 分析報告", type="primary")

# ===============================
# 5. 主流程
# ===============================
if submit:
    with st.spinner("📡 收集資料並進行 AI 分析中..."):
        df_price, df_inst, company_name = get_stock_data(stock_code)

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

        st.write(f"股票名稱確認：**{company_name}**")
        st.write(f"目前股價：{current_price}，RSI：{rsi_val}，近五日外資買賣超：{foreign_net}")

        # 分段生成分析報告
        sections = [
            "🌍 【全球局勢與宏觀風險分析】",
            "💎 【內在價值審查分析】",
            "📉 【股價走勢與動能判斷】",
            "🎯 【法人目標價與時間預估】",
            "📈 【終極投資策略建議】"
        ]

        for sec in sections:
            # 取得短標題：只抓 【】裡面的文字
            short_title = sec.split("】")[1] if "】" in sec else sec

            sec_prompt = f"""
請針對股票 {stock_code}（{company_name}）撰寫專業分析，只分析這一部分，用條列方式、專業語氣：
分析主題：{sec}
目前股價：{current_price}
RSI 指標：{rsi_val}
近五日外資買賣超：{foreign_net}
"""

            st.markdown(f"### {short_title}")  # 顯示短標題

            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=sec_prompt,
                    config={"temperature": 0.7, "max_output_tokens": 1800}  # 每段分開生成
                )
                text = response.text if hasattr(response, "text") else response.candidates[0].content
                st.markdown(text)
            except Exception as e:
                st.markdown(f"❌ 生成失敗：{e}")
