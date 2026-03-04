import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 診斷報告", layout="wide")

# 2. 名稱快取
@st.cache_data(ttl=86400)
def get_stock_names():
    return {"2330": "台積電", "3131": "弘塑", "2317": "鴻海", "2454": "聯發科"}

name_map = get_stock_names()

# 3. 數據抓取函式 (強化版：確保 data 不會是 None)
def fetch_data(code):
    # 嘗試兩種後綴
    for suffix in [".TW", ".TWO"]:
        try:
            ticker_str = f"{code}{suffix}"
            ticker = yf.Ticker(ticker_str)
            # 增加抓取天數以確保 MA20 有足夠數據
            df = ticker.history(period="1y")
            
            if df.empty or len(df) < 20:
                continue
            
            info = ticker.info
            # 確保至少有股價數據
            current_p = df['Close'].iloc[-1]
            
            return {
                "p": current_p,
                "info": info,
                "df": df,
                "name": name_map.get(code, info.get('shortName', code))
            }
        except Exception as e:
            continue
    return None

# 4. 側邊欄輸入
st.sidebar.header("⚙️ 控制面板")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

# 5. UI 介面與邏輯處理
if code_input:
    # 呼叫函式並存入 data 變數
    data = fetch_data(code_input)
    
    # 這裡很重要：檢查變數名稱必須是 data，而不是 d
    if data is not None:
        st.title(f"📊 {data['name']} ({code_input}) 診斷報告")
        
        # --- 第一部分：數據指標 ---
        st.header("📋 第一部分：基本面與估值")
        info = data['info']
        # 抓取 EPS，若無則預設為 1 避免計算錯誤
        eps = info.get('trailingEps') or info.get('forwardEps') or 1
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
                ma20_p = latest['MA20'] if not pd.isna(latest['MA20']) else data['p']
                st.write(f"月線(MA20): {round(ma20_p, 1)}")
                st.write(f"位置: {'高於月線' if data['p'] > ma20_p else '低於月線'}")
            with t2:
                st.write("**【 動能 】**")
                rsi_p = latest['RSI'] if not pd.isna(latest['RSI']) else 50
                st.write(f"RSI(14): {round(rsi_p, 1)}")
            with t3:
                st.write("**【 狀態 】**")
                st.write(f"52週最高: {round(df['High'].max(), 1)}")
                st.write(f"52週最低: {round(df['Low'].min(), 1)}")
            with t4:
                st.write("**【 建議策略 】**")
                if data['p'] > ma20_p:
                    st.success("持股續抱")
                else:
                    st.warning("觀望為宜")

        # --- 第三部分：Gemini AI 點評 ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                # 簡單化模型選擇邏輯
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"妳是台股專家，請針對 {data['name']}({code_input}) 分析：價格 {data['p']}，ROE {round(roe_val*100,1)}%。請給出 30 字內的投資建議。"
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.info(response.text)
            except Exception as error:
                st.error(f"AI 暫時休息中...")
        else:
            st.error("🔑 請設定 API Key")
            
    else:
        st.error(f"❌ 無法抓取股票代碼 {code_input} 的數據。請檢查：\n1. 代碼是否輸入正確\n2. Yahoo Finance 是否連線正常")
