import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import time

# 1. 頁面基礎設定
st.set_page_config(page_title="台股 AI 智慧分析", layout="centered")
st.title("🤖 台股 AI 專家診斷")
st.caption("輸入代碼，由 Gemini AI 為您提供即時投資點評")

# 2. 數據抓取函式 (強化穩定度)
def get_clean_data(code):
    # 優先嘗試 .TWO (上櫃) 再嘗試 .TW (上市)
    for suffix in [".TWO", ".TW"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            # 抓取 1 個月歷史股價
            hist = ticker.history(period="1mo")
            if hist.empty: continue
            
            # 抓取基本面資料
            try:
                info = ticker.info
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

# 3. 側邊欄與輸入
code = st.text_input("🔍 請輸入台股代碼 (例如: 2330, 3131, 2317)", value="3131").strip()

# 4. 執行與顯示邏輯
if code:
    with st.spinner('AI 正在讀取數據並撰寫報告...'):
        data = get_clean_data(code)
        
        if data:
            # 從 Streamlit Secrets 取得 API KEY
            api_key = st.secrets.get("GEMINI_API_KEY")
            
            if api_key:
                try:
                    # 配置 Gemini
                    genai.configure(api_key=api_key.strip())
                    
                    # --- 自動偵測可用模型 (解決 404 錯誤) ---
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    if available_models:
                        # 挑選順序：1.5-flash > 1.5-pro > 1.0-pro > 第一個可用模型
                        target_model = next((m for m in available_models if '1.5-flash' in m), 
                                          next((m for m in available_models if '1.5-pro' in m), 
                                          next((m for m in available_models if 'gemini-pro' in m), 
                                          available_models[0])))
                        
                        model = genai.GenerativeModel(target_model)
                        
                        # AI 分析指令 (Prompt)
                        prompt = f"""
                        你是資深台股分析師。
                        分析標的：{data['name']}({code})
                        目前股價：{round(data['price'], 1)} 元
                        ROE (股東權益報酬率)：{round(data['roe']*100, 2)}%
                        
                        請用 40 字以內，給出精簡且具參考價值的短線與長線建議。
                        """
                        
                        response = model.generate_content(prompt)
                        
                        # 顯示分析結果
                        st.success(f"### 📋 {data['name']} ({code}) 診斷結果")
                        st.info(response.text)
                        st.caption(f"使用模型版本: {target_model.split('/')[-1]}")
                        
                    else:
                        st.error("❌ 您的 API Key 目前沒有可用模型，請確認 Google AI Studio 權限。")
                        
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg:
                        st.error("⚠️ AI 暫時忙碌中（次數限制），請等待 60 秒後再重試。")
                    else:
                        st.error(f"⚠️ AI 連線細節：{err_msg}")
            else:
                st.error("🔑 尚未在 Streamlit Cloud 的 Settings > Secrets 設定 GEMINI_API_KEY")
        else:
            st.warning(f"❌ 暫時抓不到代碼 {code} 的數據。請確認代碼是否正確，或稍後再試。")

st.divider()
st.caption("💡 提示：若出現連線錯誤，請點擊網頁右上角 '...' 中的 'Rerun'。")
