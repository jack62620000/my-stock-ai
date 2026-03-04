import streamlit as st
import yfinance as yf
import google.generativeai as genai

# 1. 頁面標題與樣式
st.set_page_config(page_title="台股 AI 專家點評", layout="centered")
st.title("🤖 台股 AI 智慧分析")
st.caption("輸入代碼，立即獲取 Gemini AI 的投資點評")

# 2. 側邊欄與輸入
code = st.text_input("🔍 請輸入台股代碼 (例如: 2330, 3131)", value="2330").strip()

# 3. 數據抓取函式 (僅抓取關鍵數值供 AI 參考)
def get_ai_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="1mo")
            if df.empty: continue
            
            info = ticker.info
            return {
                "name": info.get('shortName') or info.get('longName') or f"台股 {code}",
                "price": df['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0),
                "pe": info.get('trailingPE', 0),
                "rev_growth": info.get('revenueGrowth', 0)
            }
        except: continue
    return None

# 4. 執行 AI 分析
if code:
    with st.spinner('AI 正在讀取數據並撰寫報告...'):
        data = get_ai_data(code)
        
        if data:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key.strip())
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 餵給 AI 的背景資料 (使用者看不到，只有 AI 看得到)
                    prompt = f"""
                    你是專業台股分析師。請針對以下數據進行點評：
                    股票：{data['name']}({code})
                    現價：{round(data['price'], 1)}
                    ROE：{round(data['roe']*100, 2)}%
                    本益比：{round(data['pe'], 2)}
                    營收成長：{round(data['rev_growth']*100, 2)}%
                    
                    請用 50 字內，針對這檔股票給出毒辣且精準的短線與長線操作建議。
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # 5. 僅顯示 AI 點評結果
                    st.chat_message("assistant").write(f"### 📋 {data['name']} ({code}) 診斷結果")
                    st.info(response.text)
                    
                except Exception as e:
                    st.error("⚠️ AI 暫時無法連線，請稍後再試。")
            else:
                st.error("🔑 尚未設定 API Key")
        else:
            st.error("❌ 找不到該股票數據，請確認代碼是否正確。")

st.divider()
st.caption("註：本分析由 AI 自動生成，僅供參考，不代表投資建議。")
