import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 診斷報告", layout="wide")

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

# 5. UI 介面與邏輯處理
if code_input:
    data = fetch_data(code_input) # <--- 剛才這裡少了一個括號，現在補上了
    
    if data: # <--- 變數名稱統一口徑，改用 data
        st.title(f"📊 {data['name']} ({code_input}) 診斷報告")
        
        # --- 第一部分：數據指標 ---
        st.header("📋 第一部分：基本面與估值")
        info = data['info']
        eps = info.get('trailingEps', 0) or 1 
        intrinsic = eps * 22.5 
        safety = (intrinsic / data['p']) - 1
        roe_val = info.get('returnOnEquity', 0)
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(data['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(roe_val*100, 2)}%")

        # --- 第二部分：技術走勢分析 ---
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
                if data['p'] > latest['MA20']:
                    st.success("持股續抱")
                else:
                    st.warning("觀望為宜")

        # --- 第三部分：Gemini AI 專家點評 ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if available_models:
                    target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
                    model = genai.GenerativeModel(target_model)
                    
                    # 修正 Prompt 中的變數名稱
                    prompt = f"妳是台股專家，請針對 {data['name']}({code_input}) 分析：價格 {data['p']}，ROE {round(roe_val*100,1)}%。請給出 30 字內的投資建議。"
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        st.info(response.text)
                    else:
                        st.warning("AI 已連線但未回傳內容。")
                else:
                    st.error("❌ 找不到可用模型。")
                    
            except Exception as error:
                st.error(f"⚠️ 連線細節：{str(error)}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")
            
    else:
        st.error("❌ 無法抓取數據，請確認代碼是否正確。")
