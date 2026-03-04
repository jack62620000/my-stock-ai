import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 1. 頁面設定
st.set_page_config(page_title="台股分析", layout="wide")
st.title("台股分析")
st.markdown("---")

# 2. 強化數據抓取
def get_full_analysis_data(code):
    for suffix in [".TWO", ".TW"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            df = t.history(period="1y")
            if df.empty: continue
            
            info = t.info
            # --- 技術指標計算 ---
            # KD 指標 (預設 14, 3, 3)
            kd = ta.stoch(df['High'], df['Low'], df['Close'])
            # MACD
            macd = ta.macd(df['Close'])
            # RSI & 均線
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            
            # 合併所有指標到 df
            df = pd.concat([df, kd, macd], axis=1)
            
            # 模擬大戶法人動向
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
                "latest_tech": df.iloc[-1], 
                "df": df.tail(60)
            }
        except: continue
    return None

# 3. AI 分析函式
@st.cache_data(ttl=1800)
def get_buffett_pro_analysis(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        
        # 取得所有可用模型
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1. 調整優先順序：避開目前報錯的 2.0-flash，優先找 1.5-flash
        # 因為 1.5 的免費額度通常比較穩，不會隨便歸零
        target_model = None
        for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro']:
            if preferred in model_list:
                target_model = preferred
                break
        
        # 如果找不到 1.5 系列，才隨便抓一個（除了 2.0 以外的）
        if not target_model:
            target_model = next((m for m in model_list if '2.0' not in m), model_list[0])
            
        model = genai.GenerativeModel(target_model)
        
        lt = d['latest_tech']
        
        # 確保抓得到 KD 欄位，若名稱不符則預設為 0
        k_val = lt.get('STOCHk_14_3_3', 0)
        d_val = lt.get('STOCHd_14_3_3', 0)
        
        prompt = f"""你現在是融合「巴菲特價值眼光」與「高盛首席策略分析師」的頂尖 AI 顧問。
請針對股票：{d['name']} ({code}) 進行精確且多方面的專業分析報告。

【⚠️ 執行指令】：請直接從第 1 點開始輸出報告，嚴禁任何開場白、問候語或自我介紹。

【當前關鍵數據】
- 財務：現價 {round(d['price'],1)}元, ROE {round(d['roe']*100,2)}%, 毛利 {round(d['margin']*100,2)}%
- 技術：K值 {round(k_val,1)}, D值 {round(d_val,1)}, RSI {round(lt['RSI'],1)}
- 籌碼：近期法人/大戶買賣力道參考為「{d['inst_proxy']}」

請嚴格依照以下結構輸出報告內容：

1. 🌍【全球局勢與宏觀風險分析】：
   分析2026年全球政經局勢（如美國關稅政策、供應鏈碎片化、通膨壓力等）對 {d['name']} 的具體影響，這家公司是否具備對抗全球波動的韌性？

2. 💎【巴菲特的內在價值審查】：
   從毛利與財務穩健度看，是否有寬廣護城河？護城河有哪些？全球市佔率預估是多少？在目前通膨環境下是否具備「定價權」？

3. 📉【股價走勢與動能判斷】：
   目前的 K線、KD、MACD、RSI 透露什麼買賣訊號？目前股價是反應基本面價值，還是處於市場情緒的過度波動？分析大戶及法人買賣趨勢。

4. 🎯【法人目標價與達成時間預估】：
   分析法人平均目標價 {d['target_mean'] if d['target_mean'] else 'N/A'} 的合理性。預估股價達到合理價的預測時間，並說明預測理由。

5. 📈【終極投資策略建議】：
   給出具體的「長線持有」或「短線避險」建議。請提供長線及短線進場股價及停損點股價。"""

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
            with st.spinner(f'AI 正在分析 {data["name"]}...'):
                ans, m_name = get_buffett_pro_analysis(data, code_input, api_key)
                if m_name:
                    st.markdown(f"### 🛡️ AI分析報告：{data['name']} ({code_input})")
                    st.write(ans)
                else:
                    st.error(f"⚠️ 錯誤：{ans}")
        else:
            st.error("🔑 請設定 API Key")
    else:
        st.warning("❌ 抓不到數據，請確認代碼。")

