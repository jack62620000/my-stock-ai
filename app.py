import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import numpy as np

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
    except: pass
    return names

name_map = get_all_names()

st.sidebar.markdown("### 📈 **台股AI診斷**")
st.sidebar.markdown("---")

# --- 2. 核心數據（🔥 完整修正版）---
@st.cache_data(ttl=300)
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            
            price = hist['Close'].iloc[-1]
            
            # 🔥 完整財報數據
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
                
                # 技術面原始數據
                'df': hist,
                'name': name_map.get(code, code),
                'info': info  # 🔥 保留完整info
            }
            
            # 🔥 計算所有必要技術指標
            df = hist.copy()
            
            # 均線
            df['MA20'] = ta.sma(df['Close'], length=20)
            
            # RSI
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # KD指標
            stoch = ta.stoch(df['High'], df['Low'], df['Close'])
            if stoch is not None and not stoch.empty:
                df['stoch'] = stoch['STOCHk_14_3_3']
                df['stochd'] = stoch['STOCHd_14_3_3']
            else:
                df['stoch'] = 50  # 預設值
                df['stochd'] = 50
            
            # 計算衍生數據
            financials['pe_ratio'] = price / max(financials['eps'], 0.01)
            financials['rsi'] = df['RSI'].iloc[-1]
            financials['df'] = df
            
            # 🔥 補齊財報顯示所需欄位（使用安全預設值）
            financials.update({
                'gp': financials['gross_margin'],
                'op': financials['operating_margin'],
                'debt': financials['debt_to_equity'],
                'rev': financials['revenue_growth'],
                'div': financials['dividend_yield']
            })
            
            return financials
            
        except Exception:
            continue
    return None

# --- 3. AI報告（修正）---
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        df = d['df']
        latest = df.iloc[-1]
        k_val = latest.get('stoch', 50)
        d_val = latest.get('stochd', 50)
        
        prompt = f"""針對 {d['name']} ({code})：
現價 {round(d['p'], 1)}元, ROE {round(d['roe']*100, 2)}%
K值 {round(k_val, 1)}, RSI {round(latest.get('RSI', 50), 1)}
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
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip().upper()

if code_input:
    with st.spinner(f'🔄 正在分析 {code_input}...'):
        d = get_comprehensive_data(code_input)
    
    if d:
        st.title(f"📊 {d.get('name', code_input)} ({code_input})")
        
        # 第一部分：完整財報（修正）
        st.header("📋 第一部分：完整財報")
        with st.container(border=True):
            # 第1列
            c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
            c1.metric("現價", f"${round(d.get('p',0),1):,.0f}")
            c2.metric("合理價", f"${round(d.get('intrinsic',0),1):,.0f}")
            c3.metric("安全邊際", f"{d.get('safety',0)*100:.1f}%")
            c4.metric("52週", f"{d.get('pos_52',0)*100:.1f}%")
            c5.metric("ROE", f"{d.get('roe',0)*100:.1f}%")
            c6.metric("毛利率", f"{d.get('gp',0)*100:.1f}%")
            pe = d.get('p',0) / max(d.get('eps',0.01), 0.01)
            c7.metric("本益比", f"{pe:.1f}x")

            st.markdown(" ")

            # 第2列
            f1,f2,f3,f4,f5,f6,f7 = st.columns(7)
            f1.metric("營業利益率", f"{d.get('op',0)*100:.1f}%")
            f2.metric("負債比率", f"{d.get('debt',0)*100:.1f}%")
            f3.metric("EPS", f"{d.get('eps',0):.2f}")
            f4.metric("現金流", f"{d.get('fcf',0):.1f}億")
            f5.metric("營收成長", f"{d.get('rev',0)*100:.1f}%")
            f6.metric("殖利率", f"{d.get('div',0)*100:.1f}%")
            rsi_val = d.get('df', pd.DataFrame()).get('RSI', pd.Series([50])).iloc[-1] if not d.get('df', pd.DataFrame()).empty else 50
            f7.metric("RSI", f"{rsi_val:.0f}")

            st.markdown(" ")

            # 第3列
            s1,s2,s3,s4,s5,s6,s7 = st.columns(7)
            info = d.get('info', {})
            s1.metric("流動比率", f"{info.get('currentRatio','N/A')}")
            s2.metric("速動比率", f"{info.get('quickRatio','N/A')}")
            s3.metric("淨利率", f"{info.get('profitMargins',0)*100:.1f}%")
            s4.metric("盈餘成長", f"{info.get('earningsGrowth',0)*100:.1f}%")
            s5.metric("前瞻P/E", f"{info.get('forwardPE','N/A')}")
            s6.metric("P/B", f"{info.get('priceToBook',0):.1f}x")
            s7.metric("PEG", f"{info.get('pegRatio','N/A')}")

        # 第二部分：技術面（修正）
        st.markdown(" ")
        st.header("📉 第二部分：股價走勢與動能分析")
        df = d.get('df', pd.DataFrame())
        if not df.empty:
            latest = df.iloc[-1]
            price = d.get('p', 0)
            
            with st.container(border=True):
                t1, t2, t3, t4 = st.columns(4)
                with t1:
                    st.write("**【 均線系統 】**")
                    ma20 = latest.get('MA20', price)
                    st.write(f"MA20: {round(ma20, 1)}")
                    bias = (price / ma20 - 1) * 100 if ma20 > 0 else 0
                    st.write(f"乖離: {round(bias, 1)}%")
                with t2:
                    st.write("**【 量能強弱 】**")
                    st.write(f"成交: {int(latest.get('Volume',0)/1000)}張")
                    st.write(f"RSI: {round(latest.get('RSI',50), 1)}")
                with t3:
                    k, dv = latest.get('stoch',50), latest.get('stochd',50)
                    st.write("**【 動能指標 】**")
                    st.write(f"KD: K{round(k,1)} / D{round(dv,1)}")
                    st.write(f"{'🔥金叉' if k>dv else '❄️死叉'}")
                with t4:
                    st.write("**【 趨勢判定 】**")
                    trend = "🌕 強勢" if price > ma20 else "🌑 弱勢"
                    advice = "持股續抱" if price > ma20 else "等待轉強"
                    st.write(trend)
                    st.write(advice)
        else:
            st.warning("⚠️ 無法取得技術面數據")

        # 第三部分：AI診斷
        st.markdown(" ")
        st.header("🤖 第三部分：AI 終極戰情診斷")
        api_status = st.secrets.get("GEMINI_API_KEY", "")
        col1, col2 = st.columns([1, 4])
        with col1:
            status_icon = "🟢 已連線" if api_status else "🔴 未連線"
            st.caption(f"**{status_icon}**")
        with col2:
            st.caption(f"**Gemini 2.5 Flash**")
        
        if st.button("🚀 啟動 AI 深度診斷", type="primary", use_container_width=True):
            if api_status:
                with st.spinner(f"🤖 AI 分析 {d['name']}..."):
                    report = get_ai_analysis_report(d, code_input, api_status)
                    st.markdown("### 📋 **AI 終極投資報告**")
                    st.markdown("---")
                    st.markdown(report)
                    st.balloons()
                    st.success("✅ AI診斷完成！")
            else:
                st.error("🔧 **設定Cloud Secrets**：App Settings → Secrets → GEMINI_API_KEY")
    else:
        st.error("❌ 請確認股票代碼（如2330、2317），支援 .TW 和 .TWO")
