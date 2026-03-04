import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 診斷報告", layout="wide")

# 2. 數據抓取函式 (極致防錯版)
def fetch_data(code):
    # 優先嘗試 .TWO (上櫃) 再嘗試 .TW (上市)
    for suffix in [".TWO", ".TW"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            # 抓取 2 年資料確保指標計算正確
            df = ticker.history(period="2y")
            
            if df.empty or len(df) < 20:
                continue
            
            # 嘗試取得 info，若失敗則給予基本字典預設值
            try:
                info = ticker.info
            except:
                info = {}
                
            return {
                "p": df['Close'].iloc[-1],
                "info": info,
                "df": df,
                "name": info.get('shortName') or info.get('longName') or f"台股 {code}"
            }
        except:
            continue
    return None

# 3. 側邊欄輸入
st.sidebar.header("⚙️ 控制面板")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

# 4. 邏輯處理
if code_input:
    data = fetch_data(code_input)
    
    if data:
        st.title(f"📊 {data['name']} ({code_input}) 診斷報告")
        
        # --- 第一部分：數據指標 ---
        info = data['info']
        # 強化資料防禦：如果抓不到 EPS，給予 10 或是從股價反推
        eps = info.get('trailingEps') or info.get('forwardEps') or 1
        roe_val = info.get('returnOnEquity') or 0.1 # 找不到就預設 10%
        
        intrinsic = eps * 22.5 
        safety = (intrinsic / data['p']) - 1
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(data['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(roe_val*100, 2)}%")

        # --- 第二部分：技術分析 ---
        df = data['df'].copy()
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        latest = df.iloc[-1]
        ma20_p = latest['MA20'] if not pd.isna(latest['MA20']) else data['p']
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            t1.write(f"**月線(MA20):** {round(ma20_p, 1)}")
            t2.write(f"**RSI(14):** {round(latest['RSI'], 1) if not pd.isna(latest['RSI']) else '計算中'}")
            t3.write(f"**52週最高:** {round(df['High'].max(), 1)}")
            if data['p'] > ma20_p:
                t4.success("📈 多頭趨勢")
            else:
                t4.warning("📉 觀望為宜")

        # --- 第三部分：Gemini AI 點評 ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"你是專家。分析{data['name']}({code_input})，股價{data['p']}，ROE{round(roe_val*100,1)}%。請給30字建議。"
                response = model.generate_content(prompt)
                st.info(response.text)
            except:
                st.error("AI 暫時無法回應，可能是額度已滿。")
        else:
            st.error("🔑 請在 Secrets 設定 GEMINI_API_KEY")
            
    else:
        st.error(f"❌ 抓取失敗。Yahoo Finance 目前不給看 {code_input}。請等 10 秒後重新輸入，或換個代碼試試（例如 2330）。")
