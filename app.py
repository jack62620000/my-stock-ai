import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 頁面設定
st.set_page_config(page_title="巴菲特 AI 全方位戰情室", layout="wide")
st.title("🧙‍♂️ 巴菲特 x 策略分析師：台股深度診斷系統")
st.markdown("---")

# 2. 強化數據抓取 (包含 K線, KD, MACD, RSI, 法人籌碼趨勢)
def get_full_analysis_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            df = t.history(period="1y")
            if df.empty: continue
            
            info = t.info
            # --- 技術指標計算 ---
            # KD 指標
            kd = ta.stoch(df['High'], df['Low'], df['Close'])
            df = pd.concat([df, kd], axis=1)
            # MACD
            macd = ta.macd(df['Close'])
            df = pd.concat([df, macd], axis=1)
            # RSI & 均線
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            
            # 模擬大戶法人動向 (yf 限制，以成交量與股價變化率作為替代參考)
            vol_ma = df['Volume'].rolling(window=5).mean()
            institutional_proxy = "增加" if df['Volume'].iloc[-1] > vol_ma.iloc[-1] and df['Close'].iloc[-1] > df['Open'].iloc[-1] else "持平或減少"

            return {
                "name": info.get('shortName') or f"股票 {code}",
                "sector": info.get('sector', '未知'),
                "price": df['Close'].iloc[-1],
                "roe": info.get('returnOnEquity', 0),
                "margin": info.get('grossMargins', 0),
                "debt": info.get('debtToEquity', 0),
                "target_mean": info.get('targetMeanPrice'),
                "inst_proxy": institutional_proxy,
                "latest_tech": df.iloc[-1], # 包含 KD, MACD, RSI
                "df": df.tail(60)
            }
        except: continue
    return None

# 3. AI 分析函式 (置入妳要求的五大結構)
@st.cache_data(ttl=600)
def get_buffett_pro_analysis(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(target_model)
        
        lt = d['latest_tech']
        
        # --- 妳要求的 5 大結構 Prompt ---
        prompt = f"""
        你現在是融合「巴菲特價值眼光」與「高盛首席策略分析師」的頂尖 AI 顧問。
        請針對股票：{d['name']} ({code}) 進行精確且多方面的專業分析報告。

        【當前關鍵數據】
        - 財務：現價 {round(d['price'],1)}元, ROE {round(d['roe']*100,2)}%, 毛利 {round(d['margin']*100,2)}%
        - 技術：K值 {round(lt['STOCHk_14_3_3'],1)}, D值 {round(lt['STOCHd_14_3_3'],1)}, RSI {round(lt['RSI'],1)}
        - 籌碼：近期法人/大戶買賣力道參考為「{d['inst_proxy']}」
        
        請嚴格依照以下結構輸出報告：

        1. 🌍【全球局勢與宏觀風險分析】：
           分析2026年全球政經局勢（如美國關稅政策、供應鏈碎片化、通膨壓力等）對 {d['name']} 的具體影響，這家公司是否具備對抗全球波動的韌性？

        2. 💎【巴菲特的內在價值審查】：
           從毛利與財務穩健度看，是否有寬廣護城河？護城河有哪些？全球市佔率預估是多少？在目前通膨環境下是否具備「定價權」？

        3. 📉【股價走勢與動能判斷】：
           目前的 K線、KD、MACD、RSI 透露什麼買賣訊號？目前股價是反應基本面價值，還是處於市場情緒的過度波動？

        4. 🎯【法人目標價與達成時間預估】：
           分析法人平均目標價 {d['target_mean'] if d['target_mean'] else 'N/A'} 的合理性。預估股價達到合理價的「時間點」，並說明理由。

        5. 📈【終極投資策略建議】：
           給出具體的「長線持有」或「短線避險」建議。
           - 長線進場價：
           - 短線進場價：
           - 停損點建議：
        
        語氣：犀利、專業、多面向。
        """
        
        response = model.generate_content(prompt)
        return response.text, target_model
    except Exception as e:
        return str(e), None

# 4. UI 介面
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="2330").strip()
st.sidebar.button("🧹 清除快取", on_click=lambda: st.cache_data.clear())

if code_input:
    data = get_full_analysis_data(code_input)
    if data:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            with st.spinner(f'AI 正在為您撰寫深度診斷報告：{data["name"]}...'):
                ans, m_name = get_buffett_pro_analysis(data, code_input, api_key)
                if m_name:
                    st.markdown(f"### 🛡️ 巴菲特 x 策略分析師：{data['name']} ({code_input})")
                    st.write(ans)
                else:
                    st.error(f"⚠️ 錯誤：{ans}")
        else:
            st.error("🔑 請設定 API Key")
    else:
        st.warning("❌ 抓不到數據。")
