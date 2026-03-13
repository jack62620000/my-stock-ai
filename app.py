import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 初始化設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

# 請在 Secrets 中設定您的 API Key
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 高效數據抓取模組 ---
def get_clean_data(ticker_id):
    # (A) yfinance: 基礎股價與財報
    stock = yf.Ticker(f"{ticker_id}.TW")
    df_yf = stock.history(period="1y")
    info = stock.info
    
    # (B) FinMind: 法人籌碼 (這部分對你的第3點與第4點至關重要)
    dl = DataLoader()
    # 若有 token 建議加上 dl.login_by_token(api_token=st.secrets["FINMIND_TOKEN"])
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    df_inst = dl.taiwan_stock_institutional_investors(stock_id=ticker_id, start_date=start_date)
    
    return df_yf, df_inst, info

# --- 3. 核心 Prompt 工程 (整合你要求的五大分析) ---
def generate_cio_report(ticker, df, df_inst, info):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 計算技術指標文字化
    rsi = ta.rsi(df['Close'], length=14).iloc[-1]
    macd = ta.macd(df['Close']).iloc[-1]
    kd = ta.stoch(df['High'], df['Low'], df['Close']).iloc[-1]
    
    # 籌碼面摘要
    inst_summary = df_inst.tail(5)
    f_total = inst_summary['Foreign_Investor_Buy'].sum() - inst_summary['Foreign_Investor_Sell'].sum()
    t_total = inst_summary['Investment_Trust_Buy'].sum() - inst_summary['Investment_Trust_Sell'].sum()

    prompt = f"""
    你是一位融合「價值投資」與「量化分析」的首席投資官 (CIO)。
    請針對股票代號：{ticker} 進行極致詳細的專業分析。

    【當前真實數據快報】
    - 股價：{latest['Close']:.2f} (昨收 {prev['Close']:.2f})
    - 財務：毛利率 {info.get('grossMargins', 0)*100:.2f}% / ROE {info.get('returnOnEquity', 0)*100:.2f}%
    - 指標：RSI={rsi:.2f}, MACD_Line={macd['MACD_12_26_9']:.2f}, K={kd['STOCHk_14_3_3']:.2f}
    - 籌碼：近五日外資累計買賣超 {f_total} 股, 投信累計買賣超 {t_total} 股

    請嚴格按照以下條列式回答：
    🌍 【全球局勢與宏觀風險分析】：分析2026年當前全球重大時事（如關稅新制、區域地緣衝突、主要國家通膨指標）對該公司的具體衝擊。請判斷該公司屬於「受災戶」還是「受惠者」，並評估其供應鏈的韌性。
    💎 【內在價值審查分析】：根據提供的毛利與 ROE 數據，評估其「護城河」類型（無形資產、轉換成本、網絡效應或成本優勢）。在2026年的環境下，該公司是否具備轉嫁成本給消費者的「定價權」？
    📉 【股價走勢與動能判斷】：綜合解讀 KD（超買/超賣）、MACD（趨勢轉折）、RSI（動能強弱）訊號。特別注意： 對比「法人買賣超數據」與「股價漲跌」，判斷目前是法人大戶有計畫的佈局，還是散戶情緒帶動的非理性波動。
    🎯 【法人目標價與時間預估】：請參考 2026 年最新投顧報告摘要，列出市場對該股的平均目標價。若當前股價高於/低於目標價，請分析其合理性，並預估股價回歸合理價值所需的具體時間（如：1 個季度、半年內）。
    📈 【終極投資策略建議】：請給出具體的「長線持有」或「短線避險」建議。請提供明確的：長線進場價位（基於價值估算）、短線支撐價位（基於技術指標）、停損價位（若跌破則基本面轉弱）。
    """
    return prompt

# --- 4. 網頁 UI 佈局 ---
st.title("🤖 首席分析師：AI 投資決策報告")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 參數設定")
    stock_code = st.text_input("輸入台股代號", value="2330")
    run_btn = st.button("生成深度報告", type="primary")
    st.info("此報告結合 yfinance 股價、FinMind 籌碼以及 Gemini 1.5 實時分析。")

if run_btn:
    with st.status("🚀 正在執行多維度分析...", expanded=True) as status:
        st.write("正在從 TWSE/FinMind 抓取真實數據...")
        df_yf, df_inst, info = get_clean_data(stock_code)
        
        st.write("正在整合技術指標與籌碼動向...")
        full_prompt = generate_cio_report(stock_code, df_yf, df_inst, info)
        
        st.write("正在啟動 AI 深度推理 (Gemini 1.5)...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        
        status.update(label="✅ 分析完成", state="complete", expanded=False)

    # 顯示結果
    st.markdown(f"## 📊 {stock_code} 綜合研究報告")
    st.caption(f"報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 呈現 AI 內容
    st.markdown(response.text)
    
    st.divider()
    st.download_button("📩 下載報告文字", response.text, file_name=f"{stock_code}_report.txt")
