import streamlit as st
import yfinance as yf
import google.generativeai as genai
import time

# 1. 頁面設定
st.set_page_config(page_title="巴菲特 AI 投資診斷", layout="centered")
st.title("🧙‍♂️ 巴菲特的 AI 投資戰情室")
st.markdown("---")

# 2. 數據抓取函式 (抓取更多巴菲特在意的指標)
def get_buffett_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            hist = t.history(period="1y")
            if hist.empty: continue
            
            info = t.info
            return {
                "name": info.get('shortName') or f"股票 {code}",
                "price": hist['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0),
                "margin": info.get('grossMargins', 0), # 毛利率 (看護城河)
                "debt": info.get('debtToEquity', 0),    # 負債比 (看財務體質)
                "fcf": info.get('freeCashflow', 0),    # 自由現金流 (看含金量)
                "rev_growth": info.get('revenueGrowth', 0) # 營收成長
            }
        except: continue
    return None

# 3. 側邊欄控制
if st.sidebar.button("🧹 清除快取並重試"):
    st.cache_data.clear()
    st.rerun()

# 4. AI 分析函式 (巴菲特人格設定)
@st.cache_data(ttl=600)
def get_buffett_analysis(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        # 自動找模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(target_model)
        
        # --- 關鍵：巴菲特人格 Prompt ---
        prompt = f"""
        你現在是股神巴菲特 (Warren Buffett)。請針對 {d['name']}({code}) 的數據進行深度價值投資分析。
        
        【財務數據】
        - 現價：{round(d['price'],1)} 元
        - ROE：{round(d['roe']*100, 2)}% (目標 15% 以上)
        - 毛利率：{round(d['margin']*100, 2)}% (看競爭力)
        - 負債比率：{round(d['debt'], 2)} (看財務風險)
        - 營收成長：{round(d['rev_growth']*100, 2)}%
        
        【請依照以下格式進行「多維度」詳細點評】：
        1. 💎【競爭優勢與護城河】：從毛利與ROE判斷這公司是否有長期護城河？
        2. 🛡️【經營品質與財務穩定度】：評估負債與獲利能力的安全性。
        3. ⚖️【內在價值估算】：基於數據，目前價格是「安全邊際高」還是「過度投機」？
        4. 📈【股神終極建議】：給出長線持有或觀望的具體決策（約 150 字）。
        
        語氣要專業、穩重，專注於「長期價值」而非短線波動。
        """
        
        response = model.generate_content(prompt)
        return response.text, target_model
    except Exception as e:
        return str(e), None

# 5. UI 執行
code_input = st.text_input("🔍 請輸入代碼 (例如: 2330, 3131)", value="3131").strip()

if code_input:
    data = get_buffett_data(code_input)
    if data:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            with st.spinner('巴菲特正在閱讀財報中...'):
                ans, m_name = get_buffett_analysis(data, code_input, api_key)
                
                if m_name:
                    st.markdown(f"### 🖋️ 巴菲特的診斷報告：{data['name']}")
                    st.write(ans) # 這裡會顯示多段落分析
                    st.caption(f"分析來源：Gemini AI ({m_name.split('/')[-1]})")
                else:
                    st.error(f"⚠️ 連線錯誤：{ans}")
        else:
            st.error("🔑 請設定 API Key")
    else:
        st.warning("❌ 抓不到數據，請重試。")

st.divider()
st.caption("「人生就像滾雪球，重要的是找到夠濕的雪和夠長的坡道。」— 巴菲特")
