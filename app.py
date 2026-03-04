import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# ========= 🎨 完美統一文字大小 =========
st.markdown("""
<style>
/* 標題 */
h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
h2, h3 { font-size: 1.6rem !important; margin: 0.3rem 0 0.5rem 0 !important; }

/* 容器框內文字統一 */
.st-emotion-cache-1r4fnda {
    padding: 0.8rem 1.2rem !important;
    margin-bottom: 0.5rem !important;
}

/* Metric文字統一 */
.metric-container { 
    font-size: 1.0rem !important; 
    margin-bottom: 0.3rem !important; 
}
.metric-value { 
    font-size: 1.4rem !important; 
}
.metric-label { 
    font-size: 0.85rem !important; 
}

/* 一般文字統一 */
div[data-testid="column"] p, div[data-testid="column"] div {
    font-size: 0.95rem !important;
    line-height: 1.3 !important;
}

/* 解決st.write大小問題 */
.element-container p {
    font-size: 0.95rem !important;
    margin: 0.2rem 0 !important;
}
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
            
            # 🔥 完整財報數據（30+項）
            financials = {
                # 價格與估值
                'p': price,
                'pe_b': 22.5 if "Semiconductor" in info.get('industry', '') else 15,
                'intrinsic': info.get('trailingEps', 0) * (22.5 if "Semiconductor" in info.get('industry', '') else 15),
                'safety': (info.get('trailingEps', 0) * 22.5 / price) - 1 if price > 0 else 0,
                'pos_52': (price - hist['Low'].min()) / (hist['High'].max() - hist['Low'].min()) if hist['High'].max() > hist['Low'].min() else 0,
                
                # 獲利能力
                'eps': info.get('trailingEps', 0),
                'forward_eps': info.get('forwardEps', 0),
                'roe': info.get('returnOnEquity', 0),
                'gross_margin': info.get('grossMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'profit_margin': info.get('profitMargins', 0),
                
                # 成長性
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                
                # 財務安全
                'debt_to_equity': info.get('debtToEquity', 0) / 100,
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0),
                'fcf': info.get('freeCashflow', 0) / 100000000,
                
                # 估值
                'trailing_pe': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'price_to_book': info.get('priceToBook', 0),
                'peg_ratio': info.get('pegRatio', 0),
                
                # 股利
                'dividend_yield': info.get('dividendYield', 0),
                'payout_ratio': info.get('payoutRatio', 0),
                
                # 技術面
                'df': hist,
                'name': name_map.get(code, code)
            }
            
            # 計算衍生數據
            financials['pe_ratio'] = price / max(financials['eps'], 0.01)
            
            # 技術指標
            df = hist.copy()
            df['RSI'] = ta.rsi(df['Close'], length=14)
            financials['rsi'] = df['RSI'].iloc[-1]
            financials['df'] = df
            
            return financials
            
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
        
        # 第一部分：5列7欄完整財報
st.header("📋 完整財報分析")
with st.container(border=True):
    # 第1列：價格與估值
    cols1 = st.columns(7)
    cols1[0].metric("現價", f"${financials['p']:,.0f}")
    cols1[1].metric("合理價", f"${financials['intrinsic']:,.0f}")
    cols1[2].metric("安全邊際", f"{financials['safety']*100:.1f}%")
    cols1[3].metric("52週位階", f"{financials['pos_52']*100:.1f}%")
    cols1[4].metric("本益比", f"{financials['pe_ratio']:.1f}x")
    cols1[5].metric("前瞻P/E", f"{financials['forward_pe']:.1f}x")
    cols1[6].metric("P/B比", f"{financials['price_to_book']:.1f}x")
    
    st.markdown(" ")
    
    # 第2列：獲利能力
    cols2 = st.columns(7)
    cols2[0].metric("ROE", f"{financials['roe']*100:.1f}%")
    cols2[1].metric("毛利率", f"{financials['gross_margin']*100:.1f}%")
    cols2[2].metric("營業利益率", f"{financials['operating_margin']*100:.1f}%")
    cols2[3].metric("淨利率", f"{financials['profit_margin']*100:.1f}%")
    cols2[4].metric("過去EPS", f"{financials['eps']:.2f}")
    cols2[5].metric("預估EPS", f"{financials['forward_eps']:.2f}")
    cols2[6].metric("PEG", f"{financials['peg_ratio']:.2f}x")
    
    st.markdown(" ")
    
    # 第3列：成長性
    cols3 = st.columns(7)
    cols3[0].metric("營收成長", f"{financials['revenue_growth']*100:.1f}%")
    cols3[1].metric("盈餘成長", f"{financials['earnings_growth']*100:.1f}%")
    cols3[2].metric("現金流", f"{financials['fcf']:.1f}億")
    cols3[3].metric("殖利率", f"{financials['dividend_yield']*100:.2f}%")
    cols3[4].metric("配發率", f"{financials['payout_ratio']*100:.1f}%")
    cols3[5].metric("RSI", f"{financials['rsi']:.0f}")
    cols3[6].metric("產業", financials['industry'][:15])
    
    st.markdown(" ")
    
    # 第4列：財務安全
    cols4 = st.columns(7)
    cols4[0].metric("負債權益比", f"{financials['debt_to_equity']*100:.1f}%")
    cols4[1].metric("流動比率", f"{financials['current_ratio']:.2f}x")
    cols4[2].metric("速動比率", f"{financials['quick_ratio']:.2f}x")
    cols4[3].metric("追蹤P/E", f"{financials['trailing_pe']:.1f}x")
    cols4[4].metric("現金", f"{info.get('totalCash',0)/100000000:.1f}億")
    cols4[5].metric("總負債", f"{info.get('totalDebt',0)/100000000:.1f}億")
    cols4[6].metric("決策", "🟢買入" if financials['safety']>0.1 else "⏳觀望")

        # 第二部分：技術面分析（正確縮排）
        st.markdown(" ")
        st.header("📉 技術面分析")
        df, latest = d['df'], d['df'].iloc[-1]
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            bias = (d['p'] / latest['MA20'] - 1) * 100
            t1.metric("月線乖離", f"{bias:.1f}%")
            t2.metric("RSI", f"{latest['RSI']:.0f}")
            k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
            t3.metric("KD", f"K{k:.0f}")
            t4.metric("趨勢", "強勢" if d['p'] > latest['MA20'] else "弱勢")
        
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








