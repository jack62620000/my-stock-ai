import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import time

# 1. 頁面基礎設定
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# 2. 名稱快取
@st.cache_data(ttl=86400)
def get_stock_names():
    return {"2330": "台積電", "3131": "弘塑", "2317": "鴻海", "2454": "聯發科"}

name_map = get_stock_names()

# 3. 強化版數據抓取
def fetch_data_safe(code):
    # 嘗試不同的後置碼
    suffixes = [".TW", ".TWO"]
    for suffix in suffixes:
        try:
            full_code = f"{code}{suffix}"
            ticker = yf.Ticker(full_code)
            # 增加抓取天數以確保指標計算穩定
            df = ticker.history(period="2y")
            if df.empty or len(df) < 60:
                continue
            
            # 獲取 info 的容錯處理
            try:
                info = ticker.info
            except:
                info = {}
                
            return {
                "p": df['Close'].iloc[-1],
                "info": info,
                "df": df,
                "name": name_map.get(code, info.get('shortName', code))
            }
        except Exception as e:
            continue
    return None

# 4. 介面與控制
st.sidebar.header("⚙️ 控制面板")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

if code_input:
    # 顯示載入動畫增加體驗
    with st.spinner(f'正在分析 {code_input}，請稍候...'):
        data = fetch_data_safe(code_input)
    
    if data:
        st.title(f"📊 {data['name']} ({code_input}) 全方位診斷報告")
        
        # --- 第一部分：基本面 ---
        st.header("📋 第一部分：基本面與估值")
        info = data['info']
        eps = info.get('trailingEps') or info.get('forwardEps') or 1.0
        # 簡易估值邏輯
        intrinsic = eps * 22.5
        safety = (intrinsic / data['p']) - 1 if data['p'] > 0 else 0
        
        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("目前股價", f"{round(data['p'], 1)} 元")
            m2.metric("合理價(估)", f"{round(intrinsic, 1)} 元")
            m3.metric("安全邊際", f"{round(safety*100, 1)}%")
            m4.metric("ROE", f"{round(info.get('returnOnEquity', 0)*100, 2)}%")

        # --- 第二部分：技術分析 (絕對顯示區) ---
        st.header("📉 第二部分：技術走勢分析")
        df = data['df'].copy()
        # 預計算指標
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        latest = df.iloc[-1]
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線 】**")
                ma20_val = latest['MA20'] if not pd.isna(latest['MA20']) else 0
                st.write(f"月線(MA20): {round(ma20_val, 1)}")
                st.write(f"狀態: {'高於月線' if data['p'] > ma20_val else '低於月線'}")
            with t2:
                st.write("**【 動能 】**")
                rsi_val = latest['RSI'] if not pd.isna(latest['RSI']) else 0
                st.write(f"RSI(14): {round(rsi_val, 1)}")
            with t3:
                st.write("**【 區間 】**")
                st.write(f"52週最高: {round(df['High'].max(), 1)}")
                st.write(f"52週最低: {round(df['Low'].min(), 1)}")
            with t4:
                st.write("**【 指標診斷 】**")
                if data['p'] > ma20_val:
                    st.success("✅ 多頭趨勢")
                else:
                    st.warning("⚠️ 弱勢整理")

        # --- 第三部分：Gemini AI (錯誤攔截保護) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        # 檢查 Secrets 中是否有 KEY
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"妳是台股權威專家，針對 {data['name']}({code_input}) 提供分析。數據：價格{data['p']}，ROE {round(info.get('returnOnEquity', 0)*100, 1)}%，RSI {round(rsi_val, 1)}。請用 50 字內給出精闢的短線操作策略。"
                
                # 增加逾時控制
                response = model.generate_content(prompt)
                if response and response.text:
                    st.info(response.text)
                else:
                    st.write("AI 思考中，請重新整理。")
            except Exception as e:
                st.warning(f"AI 模組連接中 (錯誤代碼: {str(e)[:20]}...)")
        else:
            st.error("🔑 尚未設定 API Key！請到 Streamlit Cloud Settings -> Secrets 加入 GEMINI_API_KEY")
            
    else:
        st.error(f"❌ 目前抓取不到 {code_input} 的數據。請確認代碼是否正確，或等 10 秒後再重新整理網頁。")
