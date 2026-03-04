import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 診斷報告", layout="wide")

# 2. 數據抓取函式
def get_stock_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="1y")
            if df.empty: continue
            info = ticker.info
            return {
                "p": df['Close'].iloc[-1],
                "df": df,
                "eps": info.get('trailingEps') or info.get('forwardEps') or 0,
                "roe": info.get('returnOnEquity', 0),
                "name": info.get('shortName') or info.get('longName') or code
            }
        except: continue
    return None

# 3. UI 介面
st.sidebar.title("📈 控制面板")
code_input = st.sidebar.text_input("輸入股票代碼", value="3131").strip()

if code_input:
    d = get_stock_data(code_input)
    
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 診斷報告")
        
        # --- 第一部分：數據指標 ---
        intrinsic = d['eps'] * 20 
        safety = (intrinsic / d['p']) - 1 if d['p'] > 0 else 0
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(d['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(d['roe']*100, 2)}%")

        # --- 第二部分：技術分析 ---
        st.header("📉 技術走勢分析")
        df = d['df'].copy()
        df['MA20'] = ta.sma(df['Close'], length=20)
        latest = df.iloc[-1]
        ma20_val = latest['MA20'] if not pd.isna(latest['MA20']) else d['p']
        
        with st.container(border=True):
            t1, t2, t3 = st.columns(3)
            t1.write(f"**月線(MA20):** {round(ma20_val, 1)}")
            t2.write(f"**52週高點:** {round(df['High'].max(), 1)}")
            if d['p'] > ma20_val:
                t3.success("多頭趨勢")
            else:
                t3.warning("空頭整理")

        看到這個 404 錯誤，代表妳的新 API Key 已經連線成功了（這很棒！），但它回報「找不到模型」。這通常是因為 Google AI Studio 的新專案（New Project）在某些區域預設還沒完全開通 v1beta 版本中的 gemini-1.5-flash 模型。

我們直接把模型名稱改成最原始、最穩定、絕對不會報 404 的 gemini-pro（第一代專業版），這能跳過版本不匹配的問題。

🛠️ 最終修正：改用最穩定的模型名稱
請修改 app.py 中 GenerativeModel 的那一列，改為如下內容：

Python
        # --- 第三部分：Gemini AI 專家點評 (穩定備案版) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                
                # 關鍵修正：將 'gemini-1.5-flash' 改為 'gemini-pro'
                # 這是 Google 最穩定的模型名稱，幾乎不會出現 404
                model = genai.GenerativeModel('gemini-pro')
                
                prompt = f"妳是專業台股分析師。分析{d['name']}({code_input})：股價{d['p']}，ROE{round(d['roe']*100,1)}%。請用30字給出短線戰術。"
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.info(response.text)
                else:
                    st.warning("AI 連結成功但未回傳文字。")
                    
            except Exception as error:
                # 如果 gemini-pro 也不行，我們顯示更細節的訊息
                st.error(f"⚠️ 連線細節：{str(error)}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")

