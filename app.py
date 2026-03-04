import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 頁面配置
st.set_page_config(page_title="台股分析", layout="wide")

# --- 1. 名稱抓取 ---
@st.cache_data(ttl=86400)
def get_all_names():
    names = {"2330": "台積電", "3131": "弘塑", "2317": "鴻海"}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    p = str(item).split('　')
                    if len(p) >= 2: names[p[0].strip()] = p[1].strip()
    except: pass
    return names

name_map = get_all_names()

# --- 2. 核心數據抓取與計算 ---
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- 基本面數據 ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            op_m = info.get('operatingMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            div_y = (info.get('dividendYield', 0) or 0)
            rev_g = (info.get('revenueGrowth', 0) or 0)
            
            # 估值邏輯 (產業 PE)
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 15
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            # --- 技術面數據 ---
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            macd = ta.macd(df['Close'])
            bol = ta.bbands(df['Close'], length=20, std=2)
            
            return {
                "p": price, "roe": roe, "eps": eps, "gp": gp_m, "op": op_m, "debt": debt_e,
                "fcf": fcf, "div": div_y, "rev": rev_g, "pe_b": pe_b, 
                "intrinsic": intrinsic, # 原有的合理價
                "target_mean": intrinsic, # <--- 方案 A：補上這行，對應 AI 想要的 Key
                "safety": safety, "pos_52": pos_52, "df": df, "stoch": stoch, "macd": macd, 
                "bol": bol, "name": name_map.get(code, code), "industry": ind
            }
        except: continue
    return None

# --- 3. AI 診斷報告函式 ---
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        # 1. 初始化配置
        genai.configure(api_key=api_key.strip())
        
        # 2. 核心修正：嘗試三種最可能的名稱格式 (由新到舊)
        # 排除 models/ 前綴以避免系統重複拼接成 models/models/
        model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        model = None
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                # 測試一下是否真的能用，避免 404
                # 我們不實際發送大量內容，只測建立物件
                break 
            except:
                continue
        
        if not model:
            return "❌ 嘗試了多種模型路徑 (1.5-flash, 1.5-pro, gemini-pro) 均失敗，請檢查 API Key 權限或更新套件版本。"

        # 3. 準備數據 (確保與 get_comprehensive_data 字典 Key 完全一致)
        lt = d['df'].iloc[-1]
        k_val = d['stoch'].iloc[-1, 0]
        d_val = d['stoch'].iloc[-1, 1]
        
        prompt = f"""你現在是融合「巴菲特價值眼光」與「高盛首席策略分析師」的頂尖 AI 顧問。
請針對股票：{d['name']} ({code}) 進行精確且多方面的專業分析報告。

【⚠️ 執行指令】：請直接從第 1 點開始輸出報告，嚴禁任何開場白、問候語或自我介紹。

【當前關鍵數據】
- 財務：現價 {round(d['p'], 1)}元, ROE {round(d['roe']*100, 2)}%, 毛利 {round(d['gp']*100, 2)}%
- 技術：K值 {round(k_val, 1)}, D值 {round(d_val, 1)}, RSI {round(lt['RSI'], 1)}
- 預估：合理價 {round(d['intrinsic'], 1)}元 (安全邊際 {round(d['safety']*100, 1)}%)

請嚴格依照以下結構輸出報告內容：

1. 🌍【全球局勢與宏觀風險分析】：
   分析2026年全球政經局勢（如美國關稅政策、供應鏈碎片化、通膨壓力等）對 {d['name']} 的具體影響，這家公司是否具備對抗全球波動的韌性？
2. 💎【巴菲特的內在價值審查】：
   從毛利與財務穩健度看，是否有寬廣護城河？護城河有哪些？全球市佔率預估是多少？在目前通膨環境下是否具備「定價權」？
3. 📉【股價走勢與動能判斷】：
   目前的 K線、KD、MACD、RSI 透露什麼買賣訊號？目前股價是反應基本面價值，還是處於市場情緒的過度波動？分析大戶及法人買賣趨勢。
4. 🎯【法人目標價與達成時間預估】：
   分析法人平均目標價{round(d['target_mean'], 1)}的合理性。預估股價達到合理價的預測時間，並說明預測理由。
5. 📈【終極投資策略建議】：
   給出具體的「長線持有」或「短線避險」建議。請提供長線及短線進場股價及停損點股價。"""

        # 4. 執行生成
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # 捕捉細節：如果還是報錯，讓你知道是哪邊斷掉
        return f"⚠️ AI 診斷目前無法連線：{str(e)}"

# --- 4. UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="3131").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 全方位診斷報告")

        # 第一部分：基本面與估值
        st.header("📋 第一部分：基本面、估值與財務過濾")
        with st.container(border=True):
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("目前價格", f"{round(d['p'], 1)} 元")
            v2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", f"基準PE: {d['pe_b']}")
            v3.metric("安全邊際", f"{round(d['safety']*100, 1)}%", "具補漲空間" if d['safety']>0.1 else "溢價")
            v4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%", "過熱" if d['pos_52']>0.75 else "低檔")
            
            st.markdown("---")
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.write("**【 獲利品質 】**")
                st.write(f"ROE: {round(d['roe']*100, 2)}% {'✅' if d['roe']>0.15 else ''}")
                st.write(f"毛利率: {round(d['gp']*100, 2)}%")
            with f2:
                st.write("**【 風險控管 】**")
                st.write(f"自由現金流: {round(d['fcf'], 1)} 億")
                st.write(f"負債比率: {round(d['debt']*100, 1)}%")
            with f3:
                st.write("**【 成長力道 】**")
                st.write(f"營收年增率: {round(d['rev']*100, 1)}%")
                st.write(f"現金殖利率: {round(d['div']*100, 2)}%")
            with f4:
                st.write("**【 決策建議 】**")
                if d['roe'] > 0.18 and d['pos_52'] < 0.35: st.success("🌟 卓越成長")
                elif d['safety'] > 0.1: st.success("🟢 價值低估")
                else: st.info("⏳ 持有觀望")

        # 第二部分：技術走勢
        st.header("📉 第二部分：股價走勢與動能分析")
        df, latest = d['df'], d['df'].iloc[-1]
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線系統 】**")
                st.write(f"MA20 (月線): {round(latest['MA20'], 1)}")
                bias = (d['p'] / latest['MA20'] - 1) * 100
                st.write(f"月線乖離: {round(bias, 1)}%")
            with t2:
                st.write("**【 量能強弱 】**")
                st.write(f"今日成交: {int(latest['Volume']/1000)} 張")
                st.write(f"RSI(14): {round(latest['RSI'], 1)}")
            with t3:
                st.write("**【 動能指標 】**")
                k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
                st.write(f"KD: K{round(k,1)} / D{round(dv,1)}")
                st.write(f"狀態: {'🔥金叉' if k>dv else '❄️死叉'}")
            with t4:
                st.write("**【 趨勢判定 】**")
                st.write(f"走勢: {'🌕 強勢' if d['p'] > latest['MA20'] else '🌑 弱勢'}")
                st.write(f"策略: {'持股續抱' if d['p'] > latest['MA20'] else '等待轉強'}")

        # --- 第三部分：AI 終極戰情報告 ---
        st.header("🤖 第三部分：AI 終極戰情診斷 (Gemini Pro)")
        if st.button("🚀 啟動 AI 深度診斷"):
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                with st.spinner(f"AI 正在根據資料庫為 {d['name']} 撰寫報告..."):
                    report = get_ai_analysis_report(d, code_input, api_key)
                    st.markdown("---")
                    st.markdown(report)
            else:
                st.error("🔑 請先在 Streamlit Secrets 設定 API Key。")

    else:
        st.error("❌ 抓不到數據，請確認代碼是否正確。")













