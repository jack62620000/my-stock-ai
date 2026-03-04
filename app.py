import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 頁面基礎設定
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# 2. 強化數據抓取與計算
def fetch_data_final(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="1y")
            if df.empty: continue
            
            info = ticker.info
            # 修正：針對台股常見缺失欄位進行多重備份抓取
            roe = info.get('returnOnEquity') or info.get('debtToEquity', 0) * 0 # 若無ROE則顯示0
            eps = info.get('trailingEps') or info.get('forwardEps') or 0
            
            return {
                "p": df['Close'].iloc[-1],
                "info": info,
                "df": df,
                "roe": roe,
                "eps": eps,
                "name": info.get('shortName') or info.get('longName') or code
            }
        except: continue
    return None

# 3. 介面
st.sidebar.header("⚙️ 控制面板")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

if code_input:
    data = fetch_data_final(code_input)
    
    if data:
        st.title(f"📊 {data['name']} ({code_input}) 全方位診斷報告")
        
        # --- 第一部分：數據面板 ---
        intrinsic = data['eps'] * 20 # 調整合理價倍數
        safety = (intrinsic / data['p']) - 1 if data['p'] > 0 else 0
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(data['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元" if data['eps'] > 0 else "計算中")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(data['roe']*100, 2)}%")

        # --- 第二部分：技術分析 ---
        st.header("📉 第二部分：技術走勢分析")
        df = data['df'].copy()
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        latest = df.iloc[-1]
        ma20_val = latest['MA20'] if not pd.isna(latest['MA20']) else data['p']
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線 】**")
                st.write(f"月線: {round(ma20_val, 1)}")
            with t2:
                st.write("**【 動能 】**")
                st.write(f"RSI: {round(latest['RSI'], 1) if not pd.isna(latest['RSI']) else '－'}")
            with t3:
                st.write("**【 區間 】**")
                st.write(f"52週高: {round(df['High'].max(), 1)}")
            with t4:
                st.write("**【 指標診斷 】**")
                st.success("多頭趨勢") if data['p'] > ma20_val else st.warning("空頭整理")

        # --- 第三部分：Gemini AI (修正 404 名稱錯誤) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # 核心修正：明確指定模型名稱，避免 404 錯誤
                model = genai.GenerativeModel('gemini-1.5-flash') 
                
                prompt = f"妳是台股權威分析師。分析{data['name']}({code_input})：股價{data['p']}，ROE{round(data['roe']*100, 1)}%。請用30字給出短線戰術。"
                
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                # 顯示更友善的錯誤提示
                st.warning("AI 目前正在更新模型資料，請稍後再試。")
                if "404" in str(e):
                    st.write("*(註：偵測到模型型號更新中)*")
        else:
            st.error("🔑 請在 Secrets 中設定 GEMINI_API_KEY")
    else:
        st.error("❌ 抓取不到數據，請檢查代碼或稍後再試。")
