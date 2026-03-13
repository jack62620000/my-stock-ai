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

請嚴格按照以下條列式回答：
    🌍 【全球局勢與宏觀風險分析】：分析2026年當前全球重大時事（如關稅新制、區域地緣衝突、主要國家通膨指標）對該公司的具體衝擊。請判斷該公司屬於「受災戶」還是「受惠者」，並評估其供應鏈的韌性。
    💎 【內在價值審查分析】：根據提供的毛利與 ROE 數據，評估其「護城河」類型（無形資產、轉換成本、網絡效應或成本優勢）。在2026年的環境下，該公司是否具備轉嫁成本給消費者的「定價權」？
    📉 【股價走勢與動能判斷】：綜合解讀 KD（超買/超賣）、MACD（趨勢轉折）、RSI（動能強弱）訊號。特別注意： 對比「法人買賣超數據」與「股價漲跌」，判斷目前是法人大戶有計畫的佈局，還是散戶情緒帶動的非理性波動。
    🎯 【法人目標價與時間預估】：請參考 2026 年最新投顧報告摘要，列出市場對該股的平均目標價。若當前股價高於/低於目標價，請分析其合理性，並預估股價回歸合理價值所需的具體時間（如：1 個季度、半年內）。
    📈 【終極投資策略建議】：請給出具體的「長線持有」或「短線避險」建議。請提供明確的：長線進場價位（基於價值估算）、短線支撐價位（基於技術指標）、停損價位（若跌破則基本面轉弱）。

請用條列清楚、語氣專業、不誇大。
"""

        # 呼叫 Gemini AI
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 1200}
            )

            # --- 修正這裡，確保抓到完整文字 ---
            if hasattr(response, "text"):
                ai_text = response.text
            elif hasattr(response, "candidates"):
                # 選第一個候選
                ai_text = response.candidates[0].content
            else:
                ai_text = str(response)
        
            st.markdown(f"## 📊 {stock_code} AI 投資分析報告")
            st.markdown(ai_text)

        except Exception as e:
            st.error("❌ Gemini 呼叫失敗")
            st.exception(e)
