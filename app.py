import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from FinMind.data import DataLoader
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 頁面與 API 設定 ---
st.set_page_config(page_title="台股 AI 量化決策系統", layout="wide")

# 安全讀取 API Key (請在 Streamlit Cloud Settings 裡設定)
# 本地測試請在專案目錄下建立 .streamlit/secrets.toml
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    # 如果有 FinMind Token 建議也放入，否則呼叫頻率會受限
    FINMIND_TOKEN = st.secrets.get("FINMIND_TOKEN", "") 
except:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 數據抓取模組 ---
@st.cache_data(ttl=3600)
def fetch_all_data(ticker_id):
    # (A) yfinance 數據
    stock = yf.Ticker(f"{ticker_id}.TW")
    df_yf = stock.history(period="1y")
    info = stock.info
    
    # (B) FinMind 籌碼數據
    dl = DataLoader()
    if FINMIND_TOKEN:
        dl.login_by_token(api_token=FINMIND_TOKEN)
    
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    df_inst = dl.taiwan_stock_institutional_investors(
        stock_id=ticker_id, start_date=start_date
    )
    return df_yf, df_inst, info

# --- 3. 技術指標計算 ---
def apply_indicators(df):
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA60'] = ta.sma(df['Close'], length=60)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    kd = ta.stoch(df['High'], df['Low'], df['Close'])
    df = pd.concat([df, macd, kd], axis=1)
    return df

# --- 4. 側邊欄 UI ---
st.sidebar.title("🔍 股市決策參數")
ticker_input = st.sidebar.text_input("輸入台股代號", value="2330")
analyze_btn = st.sidebar.button("啟動 AI 精準分析")

# --- 5. 主內容區 ---
st.title(f"📈 {ticker_input} 智慧決策看板")

if ticker_input:
    df_yf, df_inst, info = fetch_all_data(ticker_input)
    
    if not df_yf.empty:
        df = apply_indicators(df_yf)
        latest = df.iloc[-1]
        
        # 指標卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("當前股價", f"{latest['Close']:.2f}")
        c2.metric("RSI(14)", f"{latest['RSI']:.1f}")
        c3.metric("本益比", f"{info.get('trailingPE', 'N/A')}")
        c4.metric("毛利率", f"{info.get('grossMargins', 0)*100:.1f}%")

        # K線圖
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name='K線', increasing_line_color='#FF3333', decreasing_line_color='#00AA00'
        )])
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='月線(MA20)', line=dict(color='orange')))
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # --- AI 分析區 ---
        if analyze_btn:
            with st.spinner("🤖 AI 正在整合全球時事與籌碼數據..."):
                # 準備籌碼摘要
                inst_recent = df_inst.tail(5)
                f_buy = inst_recent['Foreign_Investor_Buy'].sum() - inst_recent['Foreign_Investor_Sell'].sum()
                t_buy = inst_recent['Investment_Trust_Buy'].sum() - inst_recent['Investment_Trust_Sell'].sum()

                # 設定模型 (啟用 Google Search Grounding)
                # 注意：目前免費版 API 若不支援工具，可移除 tools 部分
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    tools=[{"google_search": {}}] 
                )
                
                prompt = f"""
                你是一位融合「價值投資」與「量化分析」的首席分析師。
                股票: {ticker_input}, 最新價: {latest['Close']:.2f}
                技術面: RSI {latest['RSI']:.1f}, MACD {latest['MACD_12_26_9']:.2f}
                籌碼面: 近五日外資累計買賣超 {f_buy}, 投信累計買賣超 {t_buy}
                財務面: 毛利 {info.get('grossMargins', 0)*100:.2f}%, ROE {info.get('returnOnEquity', 0)*100:.2f}%
                
                請嚴格依據以下結構回答 (使用 2026 年最新時事)：
                1. 🌍【全球局勢與宏觀風險分析】：分析2026年當前全球重大時事（如關稅新制、區域地緣衝突、主要國家通膨指標）對該公司的具體衝擊。請判斷該公司屬於「受災戶」還是「受惠者」，並評估其供應鏈的韌性。
                2. 💎【內在價值審查分析】：根據提供的毛利與 ROE 數據，評估其「護城河」類型（無形資產、轉換成本、網絡效應或成本優勢）。在2026年的環境下，該公司是否具備轉嫁成本給消費者的「定價權」？
                3. 📉【股價走勢與動能判斷】：綜合解讀 KD（超買/超賣）、MACD（趨勢轉折）、RSI（動能強弱）訊號。特別注意： 對比「法人買賣超數據」與「股價漲跌」，判斷目前是法人大戶有計畫的佈局，還是散戶情緒帶動的非理性波動。
                4. 🎯【法人目標價與時間預估】：綜合各界法人預估列出市場對該股的平均目標價。若當前股價高於/低於目標價，請分析其合理性，並預估股價回歸合理價值所需的具體時間（如：1 個季度、半年內）。，給出達成時間與理由。
                5. 📈【終極投資策略建議】：請給出具體的「長線持有」或「短線避險」建議。請提供明確的：長線進場位（基於價值估算）、短線支撐位（基於技術指標）、停損價位（若跌破則基本面轉弱）。
                """
                
                response = model.generate_content(prompt)
                
                # 分頁顯示 AI 結果
                st.markdown("---")
                st.subheader("💡 AI 深度分析報告")
                st.markdown(response.text)
                
                # 額外小提示
                st.caption("數據來源: yfinance, FinMind. AI 分析僅供參考，投資請自行承擔風險。")
    else:
        st.warning("找不到該股票數據，請確認代號是否正確。")
