import streamlit as st
import yfinance as yf
import google.generativeai as genai
import time

# 1. 頁面標題與設定
st.set_page_config(page_title="台股 AI 專家診斷", layout="centered")
st.title("🤖 台股 AI 專家診斷")

# 2. 側邊欄與輸入
code = st.text_input("🔍 請輸入台股代碼 (例如: 2330, 3131)", value="3131").strip()

# 3. 數據抓取函式 (定義區：必須放在使用之前)
def get_clean_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            hist = t.history(period="1mo")
            if hist.empty: continue
            
            try:
                info = t.info
                name = info.get('shortName') or info.get('longName') or f"股票 {code}"
                roe = info.get('returnOnEquity', 0)
            except:
                name = f"股票 {code}"
                roe = 0
                
            return {
                "name": name,
                "price": hist['Close'].iloc[-1],
                "roe": roe
            }
        except:
            continue
    return None

# 4. 程式執行區塊 (這裡才會用到 data)
if code:
    with st.spinner('AI 正在讀取數據並撰寫報告...'):
        # 先抓取數據，存入 data 變數中
        data = get_clean_data(code)
        
        if data:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key.strip())
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 餵給 AI 的背景資料
                    prompt = f"你是台股專家。分析{data['name']}({code})，現價{round(data['price'], 1)}元，ROE為{round(data['roe']*100,2)}%。請給出一段40字內的投資診斷建議。"
                    
                    response = model.generate_content(prompt)
                    
                    # 顯示結果
                    st.success(f"### 📋 {data['name']} ({code}) 診斷結果")
                    st.info(response.text)
                    
                except Exception as e:
                    # 顯示詳細錯誤，方便我們排除 API Key 問題
                    st.error(f"⚠️ AI 連線細節：{str(e)}")
            else:
                st.error("🔑 尚未在 Secrets 設定 GEMINI_API_KEY")
        else:
            st.warning(f"❌ 暫時抓不到 {code} 的數據。請確認代碼是否正確，或稍後再試。")

st.divider()
st.caption("註：本建議由 AI 生成，僅供參考。")
