import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
from datetime import datetime

# ===============================
# 1. 核心設定與 API 初始化
# ===============================
st.set_page_config(page_title="2026 AI 量化投資決策端", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_available_models():
    try:
        models = client.models.list()
        gemini_models = [m.name for m in models if "gemini" in m.name.lower()]
        gemini_models.sort(key=lambda x: ("flash" not in x.lower()))
        return gemini_models
    except:
        return ["gemini-2.0-flash", "gemini-1.5-flash"]

AVAILABLE_MODELS = get_available_models()

# ===============================
# 2. 進階數據抓取模組 (包含 KD/MACD/基本面)
# ===============================
@st.cache_data(ttl=3600)
def get_advanced_quant_data(stock_id: str):
    ticker_id = f"{stock_id.replace('.TW', '').replace('.TWO', '')}.TW"
    try:
        ticker = yf.Ticker(ticker_id)
        df = ticker.history(period="1y")
        if df.empty: return None, None
        
        # 技術指標計算 (KD, MACD, RSI)
        df.ta.stoch(high='High', low='Low', k=9, d=3, append=True) # STOCHk_9_3_3, STOCHd_9_3_3
        df.ta.macd(fast=12, slow=26, signal=9, append=True)        # MACD_12_26_9
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA20'] = ta.sma(df['Close'], length=20)
        
        info = ticker.info
        
        # 抓取基本面
        dy = info.get("dividendYield", 0) or 0
        metrics = {
            "名稱": info.get("shortName", "未知"),
            "現價": round(df['Close'].iloc[-1], 2),
            "PE": round(info.get("trailingPE", 0) or 0, 2),
            "PB": round(info.get("priceToBook", 0) or 0, 2),
            "ROE": round((info.get("returnOnEquity", 0) or 0) * 100, 2),
            "毛利率": round((info.get("grossMargins", 0) or 0) * 100, 2),
            "殖利率": round(dy if dy > 1 else dy * 100, 2),
            "K值": round(df['STOCHk_9_3_3'].iloc[-1], 2),
            "D值": round(df['STOCHd_9_3_3'].iloc[-1], 2),
            "MACD": round(df['MACD_12_26_9'].iloc[-1], 2),
            "RSI14": round(df['RSI'].iloc[-1], 2),
            "乖離率%": round(((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100, 2)
        }
        
        recent_history = df.tail(10).copy()
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        recent_history = recent_history[['Open', 'High', 'Low', 'Close', 'Volume']].round(2)
        
        return metrics, recent_history
    except Exception as e:
        st.error(f"數據解析出錯: {e}")
        return None, None

# ===============================
# 3. UI 介面
# ===============================
st.title("🤖 2026 AI 股市首席分析報告")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="2330")
    if AVAILABLE_MODELS:
        default_model = st.selectbox("首選分析模型", AVAILABLE_MODELS)
    run_btn = st.button("生成五大核心報告", type="primary")

if run_btn:
    data, history = get_advanced_quant_data(stock_input)
    
    if data:
        # A. 數據看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前價格", data["現價"])
        c2.metric("ROE / 毛利", f"{data['ROE']}% / {data['毛利率']}%")
        c3.metric("KD / RSI", f"{data['K值']} / {data['RSI14']}")
        c4.metric("PE / PB", f"{data['PE']} / {data['PB']}")

        st.divider()

        # B. 核心深度分析報告
        st.subheader("📝 首席投資決策報告 (2026 版)")
        
        # 強化後的深度 Prompt
        prompt = f"""
        你是一位精通 Python 數據分析與價值投資的量化投資工程師。請針對台股 {data['名稱']}({stock_input}) 撰寫 2026 年深度分析報告。
        數據參考：
        - 財務：ROE {data['ROE']}%, 毛利 {data['毛利率']}%, PE {data['PE']}, PB {data['PB']}, 殖利率 {data['殖利率']}%
        - 技術：K/D {data['K值']}/{data['D值']}, MACD {data['MACD']}, RSI {data['RSI14']}, 乖離率 {data['乖離率%']}%
        
        請嚴格依照下列五大模組撰寫，口氣需專業、理性、具備前瞻性：

        🌍 【全球局勢與宏觀風險分析】：分析2026年當前全球環境局勢（如關稅新制、地緣衝突）對該公司的衝擊。判斷其為「受災戶」或「受惠者」，並評估供應鏈韌性。
        💎 【內在價值審查分析】：根據毛利與 ROE 數據評估其「護城河」類型。判斷在 2026 年通膨環境下是否具備轉嫁成本的「定價權」。
        📉 【股價走勢與動能判斷】：結合K/D值、MACD值、RSI值的數據判斷目前股價走勢是「法人佈局」還是「散戶非理性波動」。
        🎯 【法人目標價與時間預估】：預估市場平均目標價，分析其合理性，並給出明確股價與回歸價值的具體預估時間（如：1個季度、半年內）。
        📈 【終極投資策略建議】：給出具體明確的價位及建議，長線進場價位（價值面）、短線支撐價位（技術面）、停損價位（基本面轉弱點）的分析。
        """

        summary_placeholder = st.empty()
        summary_placeholder.info("📡 正在分析 2026 全球趨勢與量化數據...")

        success = False
        try_models = [default_model] + [m for m in AVAILABLE_MODELS if m != default_model]
        
        for m_name in try_models:
            try:
                response = client.models.generate_content(model=m_name, contents=prompt)
                summary_placeholder.markdown(response.text) # 使用 markdown 渲染結構化文字
                success = True
                break
            except:
                continue
        
        if not success:
            summary_placeholder.error("❌ 所有模型皆無法回應，請檢查 API 額度。")

        st.divider()

        # C. 底層數據表格
        col_m, col_h = st.columns([1, 2])
        with col_m:
            st.table(pd.DataFrame([data]).T.rename(columns={0: "量化數值"}))
        with col_h:
            st.dataframe(history.style.format("{:.2f}"), use_container_width=True)
            
    else:
        st.error("無法抓取數據，請確認代號。")


