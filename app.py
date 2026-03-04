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

       看到這個 404 錯誤（即使妳已經換了新 Key），這代表妳所在的 API 區域或目前的專案設定，無法透過 v1beta 這個預設路徑找到 gemini-1.5-flash。

這在 Google AI Studio 的新帳號中偶爾會發生。我們現在用最後一個、也是最粗暴但有效的解決方法：「不指定型號，讓程式去列出妳帳號下所有能用的名字」，然後直接抓第一個來用。

🛠️ 請將 app.py 的「第三部分」換成這段：
這段代碼會先問 Google：「喂，妳現在到底准許我用哪一個模型？」然後直接跟它溝通。

Python
        看到這個 404 錯誤（即使妳已經換了新 Key），這代表妳所在的 API 區域或目前的專案設定，無法透過 v1beta 這個預設路徑找到 gemini-1.5-flash。

這在 Google AI Studio 的新帳號中偶爾會發生。我們現在用最後一個、也是最粗暴但有效的解決方法：「不指定型號，讓程式去列出妳帳號下所有能用的名字」，然後直接抓第一個來用。

🛠️ 請將 app.py 的「第三部分」換成這段：
這段代碼會先問 Google：「喂，妳現在到底准許我用哪一個模型？」然後直接跟它溝通。

Python
        # --- 第三部分：Gemini AI 專家點評 (終極相容版) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                
                # 1. 自動抓取妳帳號下所有支援「生成內容」的模型清單
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if available_models:
                    # 2. 從清單中選一個（優先找 flash，沒有就找 pro，再沒有就抓第一個）
                    selected_model_name = next((m for m in available_models if '1.5-flash' in m), 
                                             next((m for m in available_models if 'pro' in m), 
                                             available_models[0]))
                    
                    model = genai.GenerativeModel(selected_model_name)
                    
                    # 3. 測試呼叫
                    prompt = f"妳是台股專家，請分析{d['name']}({code_input})，股價{d['p']}，給出一句20字內建議。"
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        st.info(f"模型 ({selected_model_name.split('/')[-1]}) 診斷：\n\n{response.text}")
                    else:
                        st.warning("AI 已連線但未回傳內容。")
                else:
                    st.error("❌ 妳的 API Key 目前沒有可用模型，請確認 Google AI Studio 帳號狀態。")
                    
            except Exception as error:
                err_str = str(error)
                if "429" in err_str:
                    st.error("⚠️ 額度已滿，請等 1 分鐘後再重新整理。")
                else:
                    st.error(f"⚠️ 連線細節：{err_str[:100]}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")

