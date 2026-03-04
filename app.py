import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 頁面基礎設定
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# 2. 名稱快取 (確保網頁跑得快)
@st.cache_data(ttl=86400)
def get_stock_names():
    return {"2330": "台積電", "3131": "弘塑", "2317": "鴻海", "2454": "聯發科"}

name_map = get_stock_names()

# 3. 數據抓取函式 (加強版)
def fetch_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="1y")
            if df.empty: continue
            
            info = ticker.info
            # 準備數據包
            return {
                "p": df['Close'].iloc[-1],
                "info": info,
                "df": df,
                "name": name_map.get(code, info.get('shortName', code))
            }
        except: continue
    return None

# 4. 側邊欄輸入
st.sidebar.header("⚙️ 控制面板")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

if code_input:
    data = fetch_data(code_input)
    
    if data:
        st.title(f"📊 {data['name']} ({code_input}) 全方位診斷報告")
        
        # --- 第一部分：基本面與估值 ---
        st.header("📋 第一部分：基本面與估值")
        info = data['info']
        eps = info.get('trailingEps', 0) or 1 # 避免除以0
        intrinsic = eps * 22.5 # 假設基準PE為22.5
        safety = (intrinsic / data['p']) - 1
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(data['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(info.get('returnOnEquity', 0)*100, 2)}%")

        # --- 第二部分：技術走勢分析 (保證顯示) ---
        st.header("📉 第二部分：技術走勢分析")
        df = data['df'].copy()
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        latest = df.iloc[-1]
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線 】**")
                st.write(f"月線(MA20): {round(latest['MA20'], 1)}")
                st.write(f"股價位置: {'高於月線' if data['p'] > latest['MA20'] else '低於月線'}")
            with t2:
                st.write("**【 動能 】**")
                st.write(f"RSI(14): {round(latest['RSI'], 1)}")
            with t3:
                st.write("**【 狀態 】**")
                st.write(f"52週最高: {df['High'].max()}")
                st.write(f"52週最低: {df['Low'].min()}")
            with t4:
                st.write("**【 建議策略 】**")
                st.success("持股續抱" if data['p'] > latest['MA20'] else "觀望為宜")

        # --- 第三部分：Gemini AI 診斷 (放在最後，失敗也不影響上面) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        if "GEMINI_API_KEY" in st.secrets:
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"妳是台股分析師，分析 {data['name']}。股價{data['p']}，ROE {round(info.get('returnOnEquity', 0)*100, 1)}%。請用 50 字內給出投資建議。"
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.warning("AI 目前忙碌中，請稍後重新整理網頁。")
        else:
            st.error("⚠️ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
            
    else:
        st.error(f"❌ 無法取得 {code_input} 的數據，請檢查代碼是否正確或稍後再試。")
