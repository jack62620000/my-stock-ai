import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# --- 1. 名稱抓取 (備援機制) ---
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

# --- 2. 核心數據抓取與全面計算 ---
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- [台股分析] 欄位數據 ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            op_m = info.get('operatingMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            curr_r = (info.get('currentRatio', 0) or 0)
            quick_r = (info.get('quickRatio', 0) or 0)
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            div_y = (info.get('dividendYield', 0) or 0)
            rev_g = (info.get('revenueGrowth', 0) or 0)
            
            # 估值換算
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 12
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            # --- [股價走勢] 指標計算 ---
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
                "fcf": fcf, "div": div_y, "rev": rev_g, "curr": curr_r, "quick": quick_r,
                "pe_b": pe_b, "intrinsic": intrinsic, "safety": safety, "pos_52": pos_52,
                "df": df, "stoch": stoch, "macd": macd, "bol": bol, "name": name_map.get(code, code)
            }
        except: continue
    return None

# --- 3. UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="3131").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 全方位診斷報告")

        # --- 第一部分：台股分析 (基本面與估值) ---
        st.header("📋 第一部分：台股分析 (基本面、估值、風險)")
        with st.container(border=True):
            # 估值核心 (加入 Help 公式標註)
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("目前價格", f"{round(d['p'], 1)} 元", help="[來源] Yahoo Finance 即時價格")
            v2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", f"基準PE: {d['pe_b']}", 
                      help=f"[公式] 近四季 EPS ({d['eps']}) × 基準 PE ({d['pe_b']})")
            v3.metric("安全邊際", f"{round(d['safety']*100, 1)}%", "具補漲空間" if d['safety']>0.1 else "溢價", 
                      help="[公式] (實證合理價 ÷ 目前股價) - 1")
            v4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%", "過熱" if d['pos_52']>0.75 else "低檔",
                      help="[公式] (目前價 - 一年最低) ÷ (一年最高 - 一年最低)")
            
            # 財務過濾 (加入來源小字)
            st.markdown("---")
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.write("**【 獲利品質 】**")
                st.write(f"ROE: {round(d['roe']*100, 2)}% `(財報)`")
                st.write(f"毛利率: {round(d['gp']*100, 2)}% `(財報)`")
                st.write(f"營業利益率: {round(d['op']*100, 2)}% `(財報)`")
            with f2:
                st.write("**【 進階風險 】**")
                st.write(f"自由現金流: {round(d['fcf'], 1)} 億 `(計算)`")
                st.write(f"負債比率: {round(d['debt']*100, 1)}% `(財報)`")
                st.write(f"速動比率: {round(d['quick']*100, 1)}% `(財報)`")
            with f3:
                st.write("**【 成長過濾 】**")
                st.write(f"近四季 EPS: {d['eps']} `(財報)`")
                st.write(f"營收年增率: {round(d['rev']*100, 1)}% `(月報)`")
                st.write(f"現金殖利率: {round(d['div']*100, 2)}% `(計算)`")
            with f4:
                # 還原試算表深度分析邏輯
                st.write("**【 AI 決策深度分析 】**")
                if d['roe'] > 0.18 and d['pos_52'] < 0.35:
                    st.success("🌟 卓越成長：高ROE且位階安全，建議佈局。")
                elif d['safety'] > 0.1:
                    st.success("🟢 價值低估：安全邊際充足，具備補漲潛力。")
                elif d['pos_52'] > 0.8:
                    st.error("🟠 過熱警戒：位階過高，建議分批獲利。")
                else:
                    st.info("⏳ 中性觀望：指標未同步，靜待買點出現。")

        # --- 第二部分：股價走勢分析 ---
        st.header("📉 第二部分：股價走勢分析 (均線、動能、區間)")
        df, latest = d['df'], d['df'].iloc[-1]
        bias = (d['p'] / latest['MA20'] - 1) * 100
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線與乖離 】**")
                st.write(f"MA5 (週線): {round(latest['MA5'], 1)} `(251)`")
                st.write(f"MA20 (月線): {round(latest['MA20'], 1)} `(251)`")
                st.write(f"MA60 (季線): {round(latest['MA60'], 1)} `(251)`")
                st.write(f"月線乖離: {round(bias, 1)}% `(公式)`")
            with t2:
                st.write("**【 量能與強弱 】**")
                st.write(f"今日成交量: {int(latest['Volume']/1000)} 張")
                vol_avg = df['Volume'].tail(5).mean()
                v_ratio = latest['Volume'] / vol_avg
                st.write(f"量能噴發比: {round(v_ratio, 2)}x `(公式)`")
                st.write(f"RSI(14): {round(latest['RSI'], 1)} `(14日)`")
            with t3:
                st.write("**【 動能指標 】**")
                k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
                st.write(f"KD值: K{round(k,1)} / D{round(dv,1)} `(9,3)`")
                st.write(f"KD狀態: {'🔥金叉' if k>dv else '❄️死叉'}")
                m_hist = d['macd'].iloc[-1, 2]
                st.write(f"MACD柱狀體: {round(m_hist, 2)} `(趨勢)`")
            with t4:
                st.write("**【 籌碼與區間 】**")
                st.write(f"布林上軌: {round(d['bol'].iloc[-1, 2], 1)} `(壓力)`")
                st.write(f"布林下軌: {round(d['bol'].iloc[-1, 0], 1)} `(支撐)`")
                st.write(f"走勢評等: {'🌕 強勢' if d['p'] > latest['MA20'] else '🌑 弱勢'}")
                st.write(f"策略: {'尋找支撐' if latest['RSI'] < 40 else '觀望回檔' if bias > 8 else '持股續抱'}")

    else:
        st.error("❌ 無法取得數據。")
