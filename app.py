import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 頁面設定
st.set_page_config(page_title="全球局勢 AI 投資診斷", layout="wide")
st.title("🌎 全球局勢 x 巴菲特：AI 全方位投資診斷")
st.markdown("---")

# 2. 數據抓取函式 (整合基本面、技術面、法人目標價)
def get_comprehensive_data(code):
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
                "sector": info.get('sector', '未知產業'),
                "industry": info.get('industry', '未知細分產業'),
                "price": df['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0),
                "margin": info.get('grossMargins', 0),
                "debt": info.get('debtToEquity', 0),
                "df": df.tail(60),
                "target_mean": info.get('targetMeanPrice'),
                "recommendation": info.get('recommendationKey', 'N/A')
            }
        except: continue
    return None

# 3. AI 分析函式 (核心：全球局勢連動邏輯)
@st.cache_data(ttl=600)
def get_global_strategy_analysis(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(target_model)
        
        latest = d['df'].iloc[-1]
        
        # 這裡不預設戰爭，而是給予 AI 2026年的大環境框架
        prompt = f"""
        你現在是融合了「巴菲特價值眼光」與「全球地緣政治首席分析師」的頂尖 AI 顧問。
        請針對 {d['name']}({code})，產業別為【{d['sector']} - {d['industry']}】，進行深度診斷。

        【當前數據】
        - 股價：{round(d['price'],1)} 元 | ROE：{round(d['roe']*100,2)}%
        - 技術：RSI(14)為 {round(latest['RSI'],1)}，現價相對於月線({round(latest['MA20'],1)})的位置。
        - 法人預測：平均目標價 {d['target_mean'] if d['target_mean'] else '分析師未覆蓋'}。

        請依照以下結構給出「精確且多方面」的專業報告：

        1. 🌍【全球局勢與宏觀風險分析】：
           分析 2026 年全球政經局勢（如美國關稅政策、供應鏈碎片化、通膨壓力等）對該【{d['sector']}】產業的具體影響。這家公司具備對抗全球波動的韌性嗎？

        2. 💎【巴菲特的內在價值審查】：
           從毛利與財務穩健度來看，這家公司是否有寬廣的護城河？它在目前的全球通膨環境下是否具備「定價權」？

        3. 📉【股價走勢與動能判斷】：
           目前的股價走勢是反應了基本面價值，還是處於市場情緒的過度波動中？技術指標給出了什麼買賣訊號？

        4. 🎯【法人目標價與達成時間預估】：
           分析法人目標價的合理性。並請你根據「目前成長性」與「全球變數」，預估股價達到目標價/合理價的大約時間（例如：3個月、半年或更長），並說明預測理由。

        5. 📈【終極投資策略建議】：
           結合以上所有因素，給出具體的「長線持有」或「短線避險」建議。
        
        語氣：穩重、犀利、數據驅動，篇幅 500 字左右。
        """
        
        response = model.generate_content(prompt)
        return response.text, target_model
    except Exception as e:
        return str(e), None

# 4. UI 介面
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="2330").strip()
st.sidebar.button("🧹 清除快取重試", on_click=lambda: st.cache_data.clear())

if code_input:
    data = get_comprehensive_data(code_input)
    if data:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            with st.spinner(f'全球戰情小組正在為您診斷：{data["name"]}...'):
                ans, m_name = get_global_strategy_analysis(data, code_input, api_key)
                
                if m_name:
                    # 視覺化指標
                    c1, c2, c3 = st.columns(3)
                    c1.metric("目前股價", f"{round(data['price'],1)} 元")
                    c2.metric("產業別", data['sector'])
                    c3.metric("法人目標價", f"{data['target_mean'] if data['target_mean'] else 'N/A'}")
                    
                    st.markdown(f"### 🛡️ 全球局勢與價值分析報告：{data['name']} ({code_input})")
                    st.write(ans)
                    st.caption(f"分析模型: {m_name.split('/')[-1]} | 資訊僅供參考，不構成投資建議")
                else:
                    st.error(f"⚠️ AI 連線異常：{ans}")
        else:
            st.error("🔑 請在 Secrets 設定 GEMINI_API_KEY")
    else:
        st.warning("❌ 無法抓取數據。")
