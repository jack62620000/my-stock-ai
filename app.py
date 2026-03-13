import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

# 從 Secrets 讀取 Key
if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 數據處理函式 ---
def get_stock_data(ticker_id):
    pure_id = ticker_id.replace(".TW", "").replace(".TWO", "")
    full_id = f"{pure_id}.TW"
    
    # yfinance: 獲取股價
    stock = yf.Ticker(full_id)
    df = stock.history(period="1y")
    info = stock.info
    
    if not df.empty:
        # 技術指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd_df = ta.macd(df['Close'])
        kd_df = ta.stoch(df['High'], df['Low'], df['Close'])
        df = pd.concat([df, macd_df, kd_df], axis=1)
    
    # FinMind: 籌碼面
    df_inst = pd.DataFrame()
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=pure_id, start_date=start_date)
    except:
        pass
    
    return df, df_inst, info

# --- 3. 生成 Prompt (修復 prev 變數缺失問題) ---
def generate_cio_report(ticker, df, df_inst, info):
    # 確保數據至少有兩筆才能計算漲跌
    if len(df) < 2:
        return "數據不足，無法生成報告。"
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]  # <--- 修正處：定義昨日數據
    
    # 安全取值
    rsi_val = latest.get('RSI', 0.0)
    macd_val = latest.get('MACD_12_26_9', 0.0)
    k_val = latest.get('STOCHk_14_3_3', 0.0)
    
    # 籌碼面彙整
    f_net, t_net = "無數據", "無數據"
    if not df_inst.empty and 'Foreign_Investor_Buy' in df_inst.columns:
        last_5 = df_inst.tail(5)
        f_net = last_5['Foreign_Investor_Buy'].sum() - last_5['Foreign_Investor_Sell'].sum()
        t_net = last_5['Investment_Trust_Buy'].sum() - last_5['Investment_Trust_Sell'].sum()
    
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

# --- 4. Streamlit UI ---
st.title("🤖 首席分析師：AI 投資決策報告")

with st.sidebar:
    stock_code = st.text_input("輸入台股代號 (如: 2330)", value="2330")
    submit = st.button("生成深度報告", type="primary")

if submit:
    with st.spinner("🚀 數據同步中，請稍候..."):
        df, df_inst, info = get_stock_data(stock_code)
        
        if df is None or df.empty:
            st.error("抓取不到股價數據，請檢查代號是否有誤。")
        else:
            full_prompt = generate_cio_report(stock_code, df, df_inst, info)
            
            # 使用 Gemini 生成回答
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                # 如果你想讓 AI 查 2026 的最新新聞，取消下面這行的註解（需 API 支援）：
                # model = genai.GenerativeModel('gemini-1.5-flash', tools=[{"google_search": {}}])
                
                response = model.generate_content(full_prompt)
                
                st.markdown(f"## 📊 {stock_code} 綜合研究報告")
                st.markdown(response.text)
                
                st.divider()
                st.download_button("📩 下載報告", response.text, file_name=f"{stock_code}_report.txt")
            except Exception as e:
                st.error(f"AI 分析失敗：{e}")
