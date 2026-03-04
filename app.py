import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# 頁面配置
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# --- [新增] Gemini 設定區塊 ---
# 這裡會讀取 Streamlit Secrets 中的 GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.sidebar.warning("⚠️ 尚未在 Secrets 設定 Gemini API Key")

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
            
            # 台股分析數據
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            op_m = info.get('operatingMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            rev_g = (info.get('revenueGrowth', 0) or 0)
            
            # 估值與位階
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 12
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            # 技術指標
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            bol = ta.bbands(df['Close'], length=20, std=2)
            
            return {
                "p": price, "roe": roe, "eps": eps, "gp": gp_m, "op": op_m, "debt": debt_e,
                "fcf": fcf, "rev": rev_g, "pe_b": pe_b, "intrinsic": intrinsic, "safety": safety, "pos_52": pos_52,
                "df": df, "stoch": stoch, "bol": bol, "name": name_map.get(code, code)
            }
        except: continue
    return None

# --- [新增] AI 分析函式 ---
def get_gemini_analysis(d, code):
    prompt = f"""
    妳是專業台股分析師。請針對以下數據給出精確建議：
    標的：{d['name']} ({code})
    目前價格：{d['p']}，合理價：{d['intrinsic']}
    ROE：{round(d['roe']*100, 2)}%，安全邊際：{round(d['safety']*100, 1)}%
    52週位階：{round(d['pos_52']*100, 1)}%
    請用 80 字內分析其投資價值。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI 分析暫時無法載入。"

# --- 3. UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", value="3131").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 全方位診斷報告")

        # 第一部分：基本面
        st.header("📋 第一部分：台股分析 (基本面、估值、風險)")
        with st.container(border=True):
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("目前價格", f"{round(d['p'], 1)} 元")
            v2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", f"基準PE: {d['pe_b']}")
            v3.metric("安全邊際", f"{round(d['safety']*100, 1)}%")
            v4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%")
            
            st.markdown("---")
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.write("**【 獲利品質 】**")
                st.write(f"ROE: {round(d['roe']*100, 2)}% {'✅' if d['roe']>0.15 else ''}")
                st.write(f"毛利率: {round(d['gp']*100, 2)}%")
            with f2:
                st.write("**【 進階風險 】**")
                st.write(f"自由現金流: {round(d['fcf'], 1)} 億")
                st.write(f"負債比率: {round(d['debt']*100, 1)}%")
            with f3:
                st.write("**【 成長過濾 】**")
                st.write(f"近四季 EPS: {d['eps']}")
                st.write(f"營收年增率: {round(d['rev']*100, 1)}%")
            with f4:
                # --- 這裡顯示 Gemini 分析 ---
                st.write("**【 🤖 Gemini AI 深度分析 】**")
                if "GEMINI_API_KEY" in st.secrets:
                    with st.spinner('AI 正在思考中...'):
                        analysis = get_gemini_analysis(d, code_input)
                        st.info(analysis)
                else:
                    st.error("請在 Streamlit Secrets 設定 API Key")

        # 第二部分：技術面 (省略重複邏輯，維持妳原本的表格內容)
        st.header("📉 第二部分：股價走勢分析")
        # ... (此處可放妳原本的 t1~t4 欄位程式碼) ...

    else:
        st.error("❌ 無法取得數據。")
