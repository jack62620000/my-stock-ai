import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta
import requests

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 股市首席分析報告", layout="centered")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. 繞過封鎖的數據處理函式 ---
@st.cache_data(ttl=3600) # 快取 1 小時，減少被封鎖機率
def get_stock_data(ticker_id):
    pure_id = ticker_id.replace(".TW", "").replace(".TWO", "")
    full_id = f"{pure_id}.TW"
    
    # 建立一個 Session 並模擬瀏覽器標頭，降低被 Yahoo 阻擋的風險
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    df = pd.DataFrame()
    info = {}
    
    try:
        # 使用自定義 session 抓取
        stock = yf.Ticker(full_id, session=session)
        df = stock.history(period="1y")
        info = stock.info
        
        if not df.empty:
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df = pd.concat([df, ta.macd(df['Close']), ta.stoch(df['High'], df['Low'], df['Close'])], axis=1)
    except Exception as e:
        st.warning(f"⚠️ yfinance 暫時限制存取 (Rate Limit)，部分數據將受限。")

    # (B) FinMind: 獲取籌碼 (這通常不會被封鎖，是很好的備案)
    df_inst = pd.DataFrame()
    try:
        dl = DataLoader()
        # 如果你有 FinMind Token，建議在 Secrets 設定並在此處 login
        start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=pure_id, start_date=start_date)
    except Exception as e:
        st.error(f"FinMind 籌碼數據獲取失敗: {e}")
    
    return df, df_inst, info

# --- 3. 生成 Prompt (增加數據缺失處理) ---
def generate_cio_report(ticker, df, df_inst, info):
    # 如果 yfinance 掛了，嘗試從有限的資訊或 FinMind 數據中分析
    has_df = not df.empty
    latest = df.iloc[-1] if has_df else {}
    prev = df.iloc[-2] if has_df and len(df)>1 else {}
    
    rsi_val = latest.get('RSI', 0.0)
    macd_val = latest.get('MACD_12_26_9', 0.0)
    k_val = latest.get('STOCHk_14_3_3', 0.0)
    price = latest.get('Close', 0.0)
    
    f_net, t_net = "無數據", "無數據"
    if not df_inst.empty and 'Foreign_Investor_Buy' in df_inst.columns:
        last_5 = df_inst.tail(5)
        f_net = last_5['Foreign_Investor_Buy'].sum() - last_5['Foreign_Investor_Sell'].sum()
        t_net = last_5['Investment_Trust_Buy'].sum() - last_5['Investment_Trust_Sell'].sum()
    
    prompt = f"""
    你是一位融合「價值投資」與「量化分析」的首席投資官 (CIO)。
    請針對股票代號：{ticker} 進行詳細分析。

    【當前真實數據】
    - 當前股價：{price}
    - 財務指標：毛利 {info.get('grossMargins', '未知')}, ROE {info.get('returnOnEquity', '未知')}
    - 技術指標：RSI={rsi_val:.2f}, MACD={macd_val:.2f}, K值={k_val:.2f}
    - 籌碼動向：近五日外資累計買賣超 {f_net} 股, 投信累計買賣超 {t_net} 股
    
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
    with st.spinner("🚀 正在安全獲取數據中..."):
        df_data, df_inst, stock_info = get_stock_data(stock_code)
        
        # 只要有籌碼或股價其中之一，就讓 AI 嘗試分析
        if df_data.empty and df_inst.empty:
            st.error("❌ 所有數據源均暫時無法存取，請稍後再試。")
        else:
            final_prompt = generate_cio_report(stock_code, df_data, df_inst, stock_info)
            
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(final_prompt)
                
                st.markdown(f"## 📊 {stock_code} 綜合研究報告")
                st.markdown(response.text)
                st.divider()
                st.download_button("📩 下載報告", response.text, file_name=f"{stock_code}_report.txt")
            except Exception as e:
                st.error(f"AI 分析出錯：{e}")
