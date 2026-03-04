import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# ========= 🎨 完美樣式 =========
st.markdown("""
<style>
h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
h2, h3 { font-size: 1.6rem !important; margin: 0.3rem 0 0.5rem 0 !important; }
.st-emotion-cache-1r4fnda { padding: 0.5rem 1rem !important; margin-bottom: 0.3rem !important; }
</style>
""", unsafe_allow_html=True)

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
    except: pass  # lxml錯誤忽略
    return names

name_map = get_all_names()

st.sidebar.markdown("### 📈 **台股AI診斷**")
st.sidebar.markdown("---")

# --- 2. 核心數據 ---
@st.cache_data(ttl=300)
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            div_y = info.get('dividendYield', 0) or 0
            rev_g = info.get('revenueGrowth', 0) or 0
            
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 15
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            
            return {
                "p": price, "roe": roe, "eps": eps, "gp": gp_m, "debt": debt_e,
                "fcf": fcf, "div": div_y, "rev": rev_g, "pe_b": pe_b, 
                "intrinsic": intrinsic, "target_mean": intrinsic,
                "safety": safety, "pos_52": pos_52, "df": df, "stoch": stoch, 
                "name": name_map.get(code, code), "industry": ind
            }
        except: continue
    return None

# --- 3. AI報告 ---
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        lt = d['df'].iloc[-1]
        k_val = d['stoch'].iloc[-1, 0]
        d_val = d['stoch'].iloc[-1, 1]
        
        prompt = f"""針對 {d['name']} ({code})：
現價 {round(d['p'], 1)}元, ROE {round(d['roe']*100, 2)}%
K值 {round(k_val, 1)}, RSI {round(lt['RSI'], 1)}
合理價 {round(d['intrinsic'], 1)}元

請依序回答：
1. 🌍全球局勢影響
2. 💎護城河分析  
3. 📉技術面判斷
4. 🎯目標價預估
5. 📈投資建議"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI錯誤：{str(e)[:80]}"

# --- 4. UI ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input})")
        
        # 第一部分
        st.header("📋 基本面與估值")
        with st.container(border=True):
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("現價", f"{round(d['p'], 1)} 元")
            v2.metric("合理價", f"{round(d['intrinsic'], 1)} 元", f"PE: {d['pe_b']}")
            v3.metric("安全邊際", f"{round(d['safety']*100, 1)}%")
            v4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%")
            
            st.markdown(" ")
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                roe_pct = round(d['roe']*100,1)
                roe_delta = round((d['roe']*100-15),1)
                v1.metric("ROE", f"{roe_pct}%", f"{roe_delta:+.1f}%")
            with f2:
                fcf_color = "🟢正" if d['fcf']>0 else "🔴負"
                st.metric("現金流", f"{round(d['fcf'],1)}億", fcf_color)
            with f3: st.metric("營收年增", f"{round(d['rev']*100,1)}%")
            with f4:
                if d['roe'] > 0.18: st.success("🌟 卓越成長")
                elif d['safety'] > 0.1: st.success("🟢 價值低估")
                else: st.info("⏳ 觀望")
        
        # 第二部分
        st.markdown(" ")
        st.header("📉 技術面分析")
        df, latest = d['df'], d['df'].iloc[-1]
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                bias = (d['p'] / latest['MA20'] - 1) * 100
                st.metric("MA20乖離", f"{round(bias, 1)}%")
            with t2: st.metric("RSI", f"{round(latest['RSI'], 1)}")
            with t3:
                k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
                st.metric("KD", f"K{round(k,1)}")
            with t4: st.metric("趨勢", "強勢" if d['p'] > latest['MA20'] else "弱勢")
        
        # 第三部分
        st.markdown(" ")
        st.header("🤖 AI終極診斷")
        api_status = st.secrets.get("GEMINI_API_KEY")
        col1, col2 = st.columns([1,4])
        with col1: st.caption("🟢" if api_status else "🔴")
        with col2: st.caption("Gemini 2.5")
        
        if st.button("🚀 AI深度分析", type="primary", use_container_width=True):
            if api_status:
                with st.spinner(f"分析 {d['name']}..."):
                    report = get_ai_analysis_report(d, code_input, api_status)
                    st.markdown("### 📋 AI報告")
                    st.markdown(report)
                    st.balloons()
            else:
                st.error("🔧 Settings → Secrets → GEMINI_API_KEY")
    else:
        st.error("❌ 請確認股票代碼（如2330）")
