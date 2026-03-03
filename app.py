import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股五星級 AI 戰情室 (完整透明版)", layout="wide")

# --- 1. 自動化名稱 ---
@st.cache_data(ttl=86400)
def get_all_stock_names():
    names = {"2330": "台積電", "2317": "鴻海", "3131": "弘塑"}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
                    "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    p = str(item).split('　')
                    names[p[0].strip()] = p[1].strip()
        return names
    except: return names

name_map = get_all_stock_names()

# --- 2. 數據抓取與換算邏輯 ---
def get_stock_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- 原始抓取數據 ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            op_m = info.get('operatingMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            current_r = info.get('currentRatio', 0) or 0
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            div_y = info.get('dividendYield', 0) or 0
            rev_g = info.get('revenueGrowth', 0) or 0
            
            # --- 公式換算數據 ---
            ind = info.get('industry', '')
            if "Semiconductor" in ind: pe_bench = 22.5
            elif "Financial" in ind: pe_bench = 14
            else: pe_bench = 12
            
            intrinsic = eps * pe_bench
            safety = (intrinsic / price) - 1 if price > 0 else 0
            low_52, high_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0
            
            return {
                "price": price, "roe": roe, "eps": eps, "gp": gp_m, "op": op_m,
                "debt": debt_e, "current": current_r, "fcf": fcf, "div": div_y,
                "rev": rev_g, "pe_b": pe_bench, "intrinsic": intrinsic, 
                "safety": safety, "pos_52": pos_52, "df": hist, "info": info
            }
        except: continue
    return None

# --- 3. UI 渲染 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="例如: 3131").strip()

if code_input:
    d = get_stock_metrics(code_input)
    if d:
        name = name_map.get(code_input, f"個股 {code_input}")
        st.title(f"📈 {name} ({code_input}) 投資全診斷")

        # --- A. 台股分析：估值區 ---
        st.subheader("🛡️ 核心估值分析 (公式換算)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前價格", f"{round(d['price'], 1)} 元", help="[數據源] Yahoo Finance 即時報價")
        c2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", help=f"[公式] 近四季 EPS ({d['eps']}) × 基準 PE ({d['pe_b']})")
        c3.metric("安全邊際", f"{round(d['safety']*100, 1)}%", help="[公式] (合理價 ÷ 目前價) - 1")
        c4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%", help="[公式] (目前價 - 一年最低) ÷ 一年價差")

        # --- B. 台股分析：財務健康 (原始數據) ---
        st.markdown("---")
        st.subheader("🔍 財務品質過濾 (財報原始數據)")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write(f"**ROE:** {round(d['roe']*100, 2)}% `(賺錢效率)`")
            st.write(f"**毛利率:** {round(d['gp']*100, 2)}% `(競爭力)`")
        with f2:
            st.write(f"**自由現金流:** {round(d['fcf'], 1)} 億 `(含金量)`")
            st.write(f"**負債比率:** {round(d['debt']*100, 1)}% `(風險)`")
        with f3:
            st.write(f"**營收年增率:** {round(d['rev']*100, 1)}% `(動能)`")
            st.write(f"**現金殖利率:** {round(d['div']*100, 2)}% `(配息)`")
        with f4:
            st.write(f"**流動比率:** {round(d['current']*100, 1)}% `(短期周轉)`")
            st.write(f"**基準 PE:** {d['pe_b']} 倍 `(產業設定)`")

        # --- C. 股價走勢分析 ---
        st.divider()
        st.subheader("📉 技術走勢分析 (指標計算)")
        df = d['df']
        df['MA20'] = df['Close'].rolling(20).mean()
        df['RSI'] = ta.rsi(df['Close'], length=14)
        latest_rsi = df['RSI'].iloc[-1]
        bias = (d['price'] / df['MA20'].iloc[-1] - 1) * 100

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("RSI (14)", f"{round(latest_rsi, 1)}", help="[計算] 過去14日漲跌力道")
        t2.metric("月線乖離率", f"{round(bias, 1)}%", help="[公式] (目前價 ÷ MA20) - 1")
        t3.write(f"**MA20 (月線):** {round(df['MA20'].iloc[-1], 1)}")
        t4.write(f"**成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")

        # --- D. AI 全方位決策 ---
        st.divider()
        if d['roe'] > 0.18 and d['pos_52'] < 0.35:
            st.success(f"🤖 **AI 決策：🌟 卓越成長標的** (符合 ROE > 18% 且低位階)")
        elif d['safety'] > 0.1:
            st.success(f"🤖 **AI 決策：🟢 價值低估，具補漲空間**")
        else:
            st.info(f"🤖 **AI 決策：⏳ 中性觀察中**")

    else:
        st.error("❌ 抓取失敗，請確認代碼或稍後再試。")
