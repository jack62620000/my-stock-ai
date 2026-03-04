import streamlit as st
import yfinance as yf
import google.generativeai as genai
import time

# 1. 頁面標題
st.set_page_config(page_title="台股 AI 智慧分析", layout="centered")
st.title("🤖 台股 AI 專家診斷")

# 2. 側邊欄：手動重新整理按鈕
if st.sidebar.button("🧹 清除快取並重試"):
    st.cache_data.clear()
    st.rerun()

# 3. 數據抓取 (保持穩定)
def get_clean_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            hist = t.history(period="1mo")
            if hist.empty: continue
            info = t.info
            return {
                "name": info.get('shortName') or info.get('longName') or f"股票 {code}",
                "price": hist['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0)
            }
        except: continue
    return None

# 4. AI 分析函式 (加入快取機制：同代碼 10 分鐘內不重問)
@st.cache_data(ttl=600)
def get_ai_response(name, code, price, roe, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        
        # 自動偵測模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        
        model = genai.GenerativeModel(target_model)
        prompt = f"你是台股分析師。分析{name}({code})，現價{round(price, 1)}元，ROE為{round(roe*100,2)}%。請給出40字內操作建議。"
        
        response = model.generate_content(prompt)
        return response.text, target_model
    except Exception as e:
        return str(e), None

# 5. 主要執行邏輯
code_input = st.text_input("🔍 請輸入台股代碼", value="3131").strip()

if code_input:
    data = get_clean_data(code_input)
    
    if data:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            # 呼叫帶有快取的 AI 函式
            ai_text, model_name = get_ai_response(data['name'], code_input, data['price'], data['roe'], api_key)
            
            if model_name: # 代表成功
                st.success(f"### 📋 {data['name']} ({code_input}) 診斷結果")
                st.info(ai_text)
                st.caption(f"模型: {model_name}")
            else: # 代表失敗
                if "429" in ai_text:
                    st.error("⚠️ Google API 額度已滿。請點擊左側『清除快取』並等 60 秒再試。")
                else:
                    st.error(f"⚠️ 連線錯誤：{ai_text}")
        else:
            st.error("🔑 請設定 API Key")
    else:
        st.warning("❌ 抓不到數據，請確認代碼。")
