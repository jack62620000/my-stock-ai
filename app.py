import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
from datetime import datetime

# ===============================
# 1. 核心量化計算模組
# ===============================
@st.cache_data(ttl=3600)
def get_quantitative_data(stock_id: str):
    try:
        yf_id = f"{stock_id.replace('.TW', '')}.TW"
        ticker = yf.Ticker(yf_id)
        
        # 1. 歷史價格數據 (用於計算技術指標)
        df = ticker.history(period="1y") # 抓一年份數據計算指標較準確
        if df.empty: return None
        
        # 技術指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 2. 基本面價值數據
        info = ticker.info
        metrics = {
            "公司名稱": info.get("shortName", "N/A"),
            "目前股價": df['Close'].iloc[-1],
            "昨收價": df['Close'].iloc[-2],
            "本益比 (PE)": info.get("trailingPE", 0),
            "股價淨值比 (PB)": info.get("priceToBook", 0),
            "現金股利殖利率": (info.get("dividendYield", 0) or 0) * 100,
            "EPS (過去四季)": info.get("trailingEps", 0),
            "52週最高": info.get("fiftyTwoWeekHigh", 0),
            "52週最低": info.get("fiftyTwoWeekLow", 0),
        }
        
        # 3. 整理技術指標最近值
        tech_status = {
            "RSI14": df['RSI'].iloc[-1],
            "5MA": df['MA5'].iloc[-1],
            "20MA": df['MA20'].iloc[-1],
            "60MA": df['MA60'].iloc[-1],
        }
        
        return metrics, tech_status, df.tail(10) # 回傳最近10筆原始數據
    except Exception as e:
        st.error(f"數據解析錯誤: {e}")
        return None

# ===============================
# 2. 價值投資判定邏輯
# ===============================
def analyze_value(m):
    # 巴菲特式安全邊際邏輯 (範例：PB < 1.5 且 殖利率 > 4% 為優)
    score = 0
    reasons = []
    
    if m["股價淨值比 (PB)"] < 1.5: 
        score += 1
        reasons.append("PB 低於 1.5 (估值偏低)")
    if m["現金股利殖利率"] > 4: 
        score += 1
        reasons.append("殖利率高於 4% (防守力強)")
    if m["目前股價"] < m["52週最高"] * 0.8: 
        score += 1
        reasons.append("股價已從高點回落超過 20% (具安全邊際)")
        
    status = "積極買進" if score >= 3 else "分批佈局" if score >= 1 else "觀望待變"
    return status, reasons

# ===============================
# 3. Streamlit UI 介面
# ===============================
st.set_page_config(page_title="量化數據決策終端", layout="wide")
st.title("📊 台股量化價值決策終端")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號", value="2330")
    api_key = st.text_input("Gemini API Key", type="password")
    submit = st.button("執行量化分析", type="primary")

if submit:
    res = get_quantitative_data(stock_code)
    if res:
        metrics, tech, raw_data = res
        
        # A. 核心指標區
        st.subheader(f"🔍 {metrics['公司名稱']} ({stock_code}) 核心數據")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("目前價格", f"{metrics['目前股價']:.2f}", f"{metrics['目前股價']-metrics['昨收價']:.2f}")
        col2.metric("本益比 (PE)", f"{metrics['本益比 (PE)']:.2f}")
        col3.metric("股價淨值比 (PB)", f"{metrics['股價淨值比 (PB)']:.2f}")
        col4.metric("殖利率 (%)", f"{metrics['現金股利殖利率']:.2f}%")

        # B. 決策判斷區
        st.divider()
        decision, reasons = analyze_value(metrics)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info(f"🛡️ **安全邊際評估：{decision}**")
        with c2:
            st.write(f"判定依據：{', '.join(reasons) if reasons else '目前無明顯價值特徵'}")

        # C. 數據表格區 (取代 K 線圖)
        st.subheader("📋 量化指標清單")
        tech_df = pd.DataFrame([tech]).T.rename(columns={0: "數值"})
        st.table(tech_df) # 使用 Table 呈現更穩定的格式

        st.subheader("📅 近 10 日歷史數據回測")
        st.dataframe(raw_data[['Close', 'Volume', 'MA5', 'MA20', 'RSI']].style.format("{:.2f}"))

        # D. AI 總結
        if api_key:
            client = genai.Client(api_key=api_key)
            prompt = f"請根據以下數據進行簡短專業的投資評論：{metrics} 以及技術指標 {tech}。請直接給出支撐位與壓力位建議。"
            ai_res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success("🤖 AI 專業投顧建議")
            st.write(ai_res.text)
    else:
        st.error("無法取得數據，請確認代號是否正確。")
