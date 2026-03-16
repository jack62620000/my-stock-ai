import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from FinMind.data import DataLoader
from google import genai
from datetime import datetime, timedelta

# ===============================
# 1. 核心設定與 API 初始化
# ===============================
st.set_page_config(page_title="AI分析投資 - 專業冗餘版", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 初始化 FinMind (若有 Token 可在 Secrets 設定，沒設定則使用公共額度)
FM_DATA_LOADER = DataLoader()
if "FINMIND_TOKEN" in st.secrets:
    FM_DATA_LOADER.login_auth(st.secrets["FINMIND_TOKEN"])

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
# 2. 多源數據整合模組 (TWSE + FinMind + yf)
# ===============================
@st.cache_data(ttl=3600)
def get_advanced_quant_data(stock_id: str):
    raw_id = stock_id.split('.')[0]
    df = pd.DataFrame()
    current_price = 0.0
    
    # --- 1. 最後防線：直接從證交所 OpenAPI 獲取今日價格 ---
    # 這是不需要 API Key 且最權威的來源，用來確保程式不崩潰
    try:
        twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
        res = requests.get(twse_url, timeout=5).json()
        for item in res:
            if item['Code'] == raw_id:
                current_price = float(item['ClosingPrice'])
                break
    except:
        pass

    # --- 2. 抓取 K 線數據 (容錯處理) ---
    try:
        # 優先嘗試 yfinance
        ticker = yf.Ticker(f"{raw_id}.TW")
        df = ticker.history(period="1y")
        if df.empty:
            df = yf.Ticker(f"{raw_id}.TWO").history(period="1y")
        
        if not df.empty and current_price == 0:
            current_price = float(df['Close'].iloc[-1])
    except:
        # 若 yfinance 失敗，嘗試 FinMind
        try:
            df_fm = FM_DATA_LOADER.get_data(
                dataset="TaiwanStockPrice",
                stock_id=raw_id,
                start_date=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            )
            if not df_fm.empty:
                df = df_fm.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
                df.set_index('Date', inplace=True)
                df.index = pd.to_datetime(df.index)
                if current_price == 0: current_price = float(df['Close'].iloc[-1])
        except:
            pass

    # 檢測：如果連價格都抓不到，才報錯
    if current_price == 0:
        st.error("🚫 證交所、Yahoo、FinMind 聯防失效，請檢查網路連線或稍後再試。")
        return None, None

    # --- 3. 基本面與技術指標 (加入極度防呆) ---
    roe, gross_margin, pe, pb, dividend_yield = 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        # 基本面抓取 (這部分若失敗就讓它 0，AI 會自行根據知識庫補完)
        df_fin = FM_DATA_LOADER.get_data(dataset="TaiwanStockFinancialStatements", stock_id=raw_id, start_date='2024-01-01')
        if not df_fin.empty:
            def safe_extract(t):
                m = df_fin[df_fin['type'] == t]
                return float(m.iloc[-1]['value']) if not m.empty else 0.0
            roe = safe_extract('Return_on_Equity_A_Percent')
            gross_margin = safe_extract('Gross_Profit_Margin')
    except: pass

    # --- 4. 計算指標 (確保欄位存在) ---
    # 如果 df 為空，建立一個包含今日價格的虛擬 df 以免後續計算報錯
    if df.empty:
        df = pd.DataFrame([{'Close': current_price}], index=[pd.Timestamp.now()])

    try:
        if len(df) > 20: # 數據量夠才算技術指標
            df.ta.stoch(high='High', low='Low', close='Close', k=9, d=3, append=True)
            df.ta.macd(close='Close', fast=12, slow=26, signal=9, append=True)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MA20'] = ta.sma(df['Close'], length=20)
        df = df.fillna(0)
        
        name_map = {"3481": "群創光電", "3499": "環天科技", "2330": "台積電"}
        stock_name = name_map.get(raw_id, f"台股 {raw_id}")

        metrics = {
            "名稱": stock_name,
            "現價": round(current_price, 2),
            "PE": pe, "PB": pb, "ROE": round(roe, 2), "毛利率": round(gross_margin, 2), "殖利率": dividend_yield,
            "K值": round(df.filter(like='STOCHk').iloc[-1], 2) if not df.filter(like='STOCHk').empty else 0,
            "D值": round(df.filter(like='STOCHd').iloc[-1], 2) if not df.filter(like='STOCHd').empty else 0,
            "MACD": round(df.filter(like='MACD_12_26_9').iloc[-1], 2) if not df.filter(like='MACD_12_26_9').empty else 0,
            "RSI14": round(df['RSI'].iloc[-1], 2) if 'RSI' in df.columns else 0,
            "乖離率%": round(((current_price / df['MA20'].iloc[-1]) - 1) * 100, 2) if 'MA20' in df.columns and df['MA20'].iloc[-1] != 0 else 0
        }
        return metrics, df.tail(10)
    except Exception as e:
        return {"名稱": name_map.get(raw_id, f"台股 {raw_id}"), "現價": current_price, "PE": 0, "PB": 0, "ROE": 0, "毛利率": 0, "殖利率": 0, "K值": 0, "D值": 0, "MACD": 0, "RSI14": 0, "乖離率%": 0}, df.tail(1)

# ===============================
# 3. UI 介面 (保持您的架構)
# ===============================
st.title("🚀 專業量化投資分析系統")

with st.sidebar:
    stock_input = st.text_input("輸入台股代號", value="3481")
    default_model = st.selectbox("首選分析模型", AVAILABLE_MODELS)
    run_btn = st.button("生成五大核心報告", type="primary")

if run_btn:
    data, history = get_advanced_quant_data(stock_input)
    
    if data:
        # A. 數據看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前價格", data["現價"])
        c2.metric("基本面(ROE/毛利)", f"{data['ROE']}% / {data['毛利率']}%")
        c3.metric("技術面(KD/RSI)", f"{data['K值']} / {data['RSI14']}")
        c4.metric("價值面(PE/PB)", f"{data['PE']} / {data['PB']}")

        st.divider()

        # B. 核心深度分析報告 (保持您的 Prompt 結構)
        st.subheader(f"📝 {data['名稱']} ({stock_input}) 深度分析報告")
        
        prompt = f"""
        你是一位精通股票數據分析與價值投資的專家。請針對台股代號 {stock_input} 名稱 {data['名稱']} 撰寫深度報告。
        數據參考：
        - 財務：ROE {data.get('ROE', 0)}%, 毛利 {data.get('毛利率', 0)}%, PE {data.get('PE', 0)}, PB {data.get('PB', 0)}, 殖利率 {data.get('殖利率', 0)}%
        - 技術：K/D {data.get('K值', 0)}/{data.get('D值', 0)}, MACD {data.get('MACD', 0)}, RSI {data.get('RSI14', 0)}, 乖離率 {data.get('乖離率%', 0)}%
        
        請依照下列五大模組分析：
        🌍 【全球局勢與宏觀風險分析】：分析2026年當前全球環境局勢（如關稅新制、地緣衝突）對該公司的衝擊。判斷其為「受災戶」或「受惠者」，並評估供應鏈韌性。
        💎 【內在價值審查分析】：根據毛利與 ROE 數據評估其「護城河」類型。判斷在 2026 年通膨環境下是否具備轉嫁成本的「定價權」。
        📉 【股價走勢與動能判斷】：結合K/D值、MACD值、RSI值的數據判斷目前股價走勢是「法人佈局」還是「散戶非理性波動」。
        🎯 【法人目標價與時間預估】：預估市場平均目標價，分析其合理性，並給出明確股價與回歸價值的具體預估時間（如：1個季度、半年內）。
        📈 【終極投資策略建議】：給出具體明確的價位及建議，長線進場價位（價值面）、短線支撐價位（技術面）、停損價位（基本面轉弱點）的分析。
        請嚴格禁止任何前言、引言或自我介紹，並依照上列五大模組撰寫，需專業、精準、理性、具備前瞻性並確保內容專業、精準，若數據顯示為 0，請依據您對該代號的行業知識輔助判斷。
        """

        summary_placeholder = st.empty()
        summary_placeholder.info("📡 正在串接多方數據並由 AI 生成報告...")

        # 模型嘗試邏輯 (保持您的機制)
        success = False
        try_models = [default_model] + [m for m in AVAILABLE_MODELS if m != default_model]
        for m_name in try_models:
            try:
                response = client.models.generate_content(model=m_name, contents=prompt)
                summary_placeholder.markdown(response.text)
                success = True
                break
            except: continue
        
        if not success:
            summary_placeholder.error("❌ 模型回應失敗。")

        st.divider()

        # C. 底層數據表格
        col_m, col_h = st.columns([1, 2])
        with col_m:
            st.write("### 量化指標摘要")
            st.table(pd.DataFrame([data]).T.rename(columns={0: "量化數值"}))
        with col_h:
            st.write("### 近十日歷史數據")
            st.dataframe(history.style.format("{:.2f}"), use_container_width=True)
            
    else:
        st.error("無法抓取數據，請確認代號或 API 狀態。")
