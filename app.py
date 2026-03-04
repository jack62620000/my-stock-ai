import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import time

# 1. 頁面設定
st.set_page_config(page_title="巴菲特 AI 全方位戰情室", layout="wide")
st.title("🧙‍♂️ 巴菲特 x 策略分析師：台股深度診斷")
st.markdown("---")

# 2. 強化數據抓取 (基本面 + 技術面 + 法人數據)
def get_advanced_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            df = t.history(period="1y")
            if df.empty: continue
            
            info = t.info
            # 計算技術指標
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            return {
                "name": info.get('shortName') or f"股票 {code}",
                "price": df['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0),
                "margin": info.get('grossMargins', 0),
                "debt": info.get('debtToEquity', 0),
                "df": df.tail(60), # 取最近 60 天走勢
                "target_high": info.get('targetHighPrice'), # 法人最高目標價
                "target_mean": info.get('targetMeanPrice'), # 法人平均目標價
                "recommendation": info.get('recommendationKey', 'N/A') # 法人評等
            }
        except: continue
    return None

# 3. AI 分析函式 (整合走勢與法人預測)
@st.cache_data(ttl=600)
def get_comprehensive_analysis(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(target_model)
        
        # 整理技術面現況
        latest = d['df'].iloc[-1]
        trend_status = "多頭 (價在月線與季線上)" if d['price'] > latest['MA20'] > latest['MA60'] else "整理或空頭"
        
        prompt = f"""
        你現在是融合了「股神巴菲特」價值眼光與「高盛首席策略師」技術判斷的 AI 顧問。
        請針對 {d['name']}({code}) 進行多維度深度分析。

        【當前數據清單】
        - 目前股價：{round(d['price'],1)} 元
        - 財務指標：ROE {round(d['roe']*100,2)}%, 毛利 {round(d['margin']*100,2)}%, 負債比 {round(d['debt'],2)}
        - 技術走勢：RSI(14)為 {round(latest['RSI'],1)}, 趨勢狀態為 {trend_status}
        - 法人觀點：平均目標價 {d['target_mean'] if d['target_mean'] else '暫無數據'}, 評等為 {d['recommendation']}

        請提供以下四個層次的詳細報告：

        1. 💎【巴菲特的價值審查】：
           從護城河、財務穩健度分析，這家公司是否符合「好生意、好管理、好價格」？

        2. 📈【技術走勢與動能分析】：
           目前的股價走勢處於什麼階段（築底、噴發、過熱、回檔）？RSI 與均線透露了什麼訊息？

        3. 🎯【法人目標價與空間估算】：
           分析法人平均目標價與現價的差距。如果目前沒有法人目標價，請根據 PE 與成長性給出你的「內在價值預估」。

        4. ⏳【達陣時間預估與操作決策】：
           綜合「基本面價值」與「技術面動能」，預估股價若要達到合理/目標價位，大約需要多少時間（例如 3-6 個月或 1 年以上）？並給出最終具體的買賣/持有策略。
        
        語氣要求：準確、犀利、多面向分析，篇幅約 300-500 字，禁止敷衍。
        """
        
        response = model.generate_content(prompt)
        return response.text, target_model
    except Exception as e:
        return str(e), None

# 4. UI 執行
code_input = st.sidebar.text_input("🔍 輸入股票代碼", value="3131").strip()
st.sidebar.button("🧹 清除快取", on_click=lambda: st.cache_data.clear())

if code_input:
    data = get_advanced_data(code_input)
    if data:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            with st.spinner(f'正在進行全方位大數據診斷：{data["name"]}...'):
                ans, m_name = get_comprehensive_analysis(data, code_input, api_key)
                
                if m_name:
                    # 佈局分欄
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.metric("目前股價", f"{round(data['price'],1)} 元")
                    with col2:
                        target = data['target_mean'] if data['target_mean'] else "觀察中"
                        st.metric("法人平均目標價", f"{target} 元")
                    
                    st.markdown(f"### 📋 全方位診斷報告：{data['name']} ({code_input})")
                    st.write(ans)
                    st.caption(f"分析來源：Gemini AI ({m_name.split('/')[-1]})")
                else:
                    st.error(f"⚠️ 連線錯誤：{ans}")
        else:
            st.error("🔑 請在 Secrets 設定 GEMINI_API_KEY")
    else:
        st.warning("❌ 暫時抓不到數據，請重試或更換代碼。")
