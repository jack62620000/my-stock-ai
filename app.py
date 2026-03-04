import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 診斷報告", layout="wide")

# 2. 數據抓取函式 (優化穩定度)
def get_data(code):
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

# 3. 側邊欄與輸入
st.sidebar.title("📈 控制面板")
code_input = st.sidebar.text_input("輸入股票代碼", value="3131").strip()

if code_input:
    d = get_data(code_input)
    
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 診斷報告")
        
        # --- 第一部分：數據指標 ---
        intrinsic = d['eps'] * 20 # 基準估值
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
            # 修正：直接使用文字，避免傳入 DeltaGenerator
            if d['p'] > ma20_val:
                t3.success("多頭趨勢")
            else:
                t3.warning("空頭整理")

        # --- 第三部分：Gemini AI 偵測診斷 ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # 這裡改用最保險的呼叫方式
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 準備測試 Prompt
                test_prompt = f"請分析台股{code_input}，用30字給出建議。"
                
                # 執行呼叫
                response = model.generate_content(test_prompt)
                
                if response.text:
                    st.info(response.text)
                else:
                    st.warning("AI 已連線但未回傳文字。")
                    
            except Exception as e:
                # 這是關鍵！它會顯示真正發生什麼事
                error_msg = str(e)
                if "API_KEY_INVALID" in error_msg:
                    st.error("❌ API Key 無效，請確認 Secrets 中的 Key 是否複製完整。")
                elif "404" in error_msg:
                    st.error("❌ 找不到模型，請確認模型名稱是否正確（建議使用 gemini-1.5-flash）。")
                elif "User location is not supported" in error_msg:
                    st.error("❌ 您的 API Key 地區受限。")
                else:
                    st.error(f"⚠️ AI 出現預料外的錯誤：{error_msg}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")

