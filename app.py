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

       # --- 第三部分：Gemini AI 專家點評 (穩定強化版) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                
                # 測試過最容易成功的版本名稱
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 增加一點參數設定，讓回傳更穩定
                prompt = f"妳是台股專家，請針對股票代碼 {code_input} 給出一句 30 字內的策略建議。目前股價約 {d['p']} 元。"
                
                # 加入 safety_settings 避免因為敏感詞被過濾
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        max_output_tokens=100,
                        temperature=0.7
                    )
                )
                
                if response and response.text:
                    st.info(response.text)
                else:
                    st.warning("AI 已連線但未回傳內容，可能正在排隊中，請稍候重新整理。")
                    
            except Exception as e:
                # 這裡會顯示最真實的錯誤原因（例如：Quota exceeded 或 Model not found）
                st.error(f"目前連線狀態：{str(e)}")
        else:
            st.error("🔑 請在 Secrets 中設定 GEMINI_API_KEY")
