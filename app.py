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

        # --- 第三部分：Gemini AI 專家點評 (自動偵測模型版) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                
                # 自動找尋可用的模型名稱 (避免 404)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if available_models:
                    # 優先挑選 flash，沒有就挑第一個
                    target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
                    model = genai.GenerativeModel(target_model)
                    
                    prompt = f"妳是台股專家，請針對 {d['name']}({code_input}) 分析：價格 {d['p']}，ROE {round(d['roe']*100,1)}%。請給出 30 字內的投資建議。"
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        st.info(response.text)
                    else:
                        st.warning("AI 已連線但未回傳內容。")
                else:
                    st.error("❌ 找不到可用模型，請確認 API Key 權限。")
                    
            except Exception as error:
                st.error(f"⚠️ 連線細節：{str(error)}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")
            
    else:
        st.error("❌ 無法抓取數據，請確認代碼是否正確。")
