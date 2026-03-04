import streamlit as st
import yfinance as yf
import google.generativeai as genai
import time

# 1. 頁面標題
st.set_page_config(page_title="台股 AI 智慧分析", layout="centered")
st.title("🤖 台股 AI 專家診斷")

# 2. 輸入框
code = st.text_input("🔍 請輸入台股代碼", value="3131").strip()

# 3. 穩定抓取函式
def get_clean_data(code):
    # 嘗試不同的後綴，並加入小延遲避免被封鎖
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            # 抓取歷史股價
            hist = t.history(period="1mo")
            if hist.empty: continue
            
            # 抓取基本面 (info 有時會失敗，所以用 try 包起來)
            try:
                info = t.info
                name = info.get('shortName') or info.get('longName') or f"股票 {code}"
                roe = info.get('returnOnEquity', 0)
                eps = info.get('trailingEps', 0)
            except:
                name = f"股票 {code}"
                roe = 0
                eps = 0
                
            return {
                "name": name,
                "price": hist['Close'].iloc[-1],
                "roe": roe,
                "eps": eps
            }
        except:
            time.sleep(0.5)
            continue
    return None

# 4. 執行與顯示
if code:
    with st.spinner('AI 分析中...'):
        data = get_clean_data(code)
        
        if data:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key.strip())
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 這是餵給 AI 的秘密指令
                    prompt = f"你是頂尖台股分析師。分析{data['name']}({code})，現價{data['price']}元，ROE為{round(data['roe']*100,2)}%。請給出一段40字內的投資診斷建議。"
                    
                    response = model.generate_content(prompt)
                    
                    # 僅顯示結果
                    st.success(f"### 📋 {data['name']} ({code}) 診斷結果")
                    st.info(response.text)
                    
                except:
                    st.error("⚠️ AI 暫時忙碌中，請稍後再試。")
            else:
                st.error("🔑 請先在 Streamlit Cloud 設定 GEMINI_API_KEY")
        else:
            st.warning(f"❌ 暫時抓不到 {code} 的數據。Yahoo 伺服器忙碌中，請點擊網頁右上角 'Rerun' 重試一次。")

st.divider()
st.caption("註：本建議由 AI 生成，投資請謹慎評估。")
