import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股AI戰情室", layout="wide")

# --- 1. 自動化名稱抓取 ---
@st.cache_data(ttl=86400)
def get_all_stock_names():
    names_dict = {}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
                    "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    parts = str(item).split('　')
                    if len(parts) >= 2:
                        names_dict[parts[0].strip()] = parts[1].strip()
        return names_dict
    except:
        return {"2330": "台積電", "2317": "鴻海", "3131": "弘塑"}

name_map = get_all_stock_names()

# --- 2. 核心數據抓取與計算 (對齊試算表所有欄位) ---
def get_stock_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y") # 抓一年份計算 52週與均線
            if hist.empty: continue
            
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- 台股分析欄位 ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_margin = info.get('grossMargins', 0) or 0
            op_margin = info.get('operatingMargins', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            current_ratio = info.get('currentRatio', 0) or 0
            quick_ratio = info.get('quickRatio', 0) or 0
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000 # 億元
            div_yield = info.get('dividendYield', 0) or 0
            rev_growth = info.get('revenueGrowth', 0) or 0
            
            # 估值邏輯
            pe_market = info.get('trailingPE', 0) or 0
            ind = info.get('industry', '')
            if "Semiconductor" in ind: pe_bench = 22.5
            elif "Financial" in ind: pe_bench = 14
            else: pe_bench = 12
            
            intrinsic = eps * pe_bench
            safety = (intrinsic / price) - 1 if price > 0 else 0
            low_52, high_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0
            
            # --- 股價走勢分析欄位 ---
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            bbands = ta.bbands(df['Close'], length=20, std=2)
            
            return {
                "price": price, "roe": roe, "eps": eps, "gp": gp_margin, "op": op_margin,
                "debt": debt_ratio, "fcf": fcf, "current": current_ratio, "quick": quick_ratio,
                "div": div_yield, "rev": rev_growth, "pe_m": pe_market, "pe_b": pe_bench,
                "intrinsic": intrinsic, "safety": safety, "pos_52": pos_52,
                "df": df, "macd": macd, "bbands": bbands, "info": info
            }
        except: continue
    return None

# --- 3. UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="例如: 3131").strip()

if code_input:
    data = get_stock_metrics(code_input)
    if data:
        stock_name = name_map.get(code_input, f"個股 {code_input}")
        st.title(f"📈 {stock_name} ({code_input}) 投資與走勢診斷")

        # --- 第一部分：台股分析 (基本面) ---
        st.header("📋 台股分析 (基本面/估值/風險)")
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("目前價格", f"{round(data['price'], 1)} 元")
            c2.metric("實證合理價", f"{round(data['intrinsic'], 1)} 元", f"基準PE: {data['pe_b']}")
            c3.metric("安全邊際", f"{round(data['safety']*100, 1)}%", "具補漲空間" if data['safety']>0.1 else "溢價")
            c4.metric("52週位階", f"{round(data['pos_52']*100, 1)}%", "過熱" if data['pos_52']>0.75 else "低檔")

        with st.container(border=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.write("**【 獲利品質 】**")
                st.write(f"ROE: {round(data['roe']*100, 2)}% {'✅' if data['roe']>0.15 else ''}")
                st.write(f"毛利率: {round(data['gp']*100, 2)}%")
                st.write(f"營業利益率: {round(data['op']*100, 2)}%")
            with f2:
                st.write("**【 進階風險 】**")
                st.write(f"自由現金流: {round(data['fcf'], 1)} 億")
                st.write(f"負債比率: {round(data['debt']*100, 1)}%")
                st.write(f"速動比率: {round(data['quick']*100, 1)}%")
            with f3:
                st.write("**【 成長過濾 】**")
                st.write(f"近四季 EPS: {data['eps']}")
                st.write(f"營收年增率: {round(data['rev']*100, 1)}%")
                st.write(f"現金殖利率: {round(data['div']*100, 2)}%")
            with f4:
                # AI 全方位決策 (T欄邏輯)
                st.write("**【 AI 全方位決策 】**")
                if data['roe'] > 0.18 and data['pos_52'] < 0.35:
                    st.success("🌟 卓越成長：高ROE+低位階")
                elif data['safety'] > 0.1:
                    st.success("🟢 分批買進：價值低估")
                elif data['pos_52'] > 0.8:
                    st.error("🟠 過熱警戒：位階過高")
                else:
                    st.info("⏳ 中性觀望：靜待訊號")

        st.divider()

        # --- 第二部分：股價走勢分析 (技術面) ---
        st.header("📉 股價走勢分析 (指標/動能/籌碼)")
        df = data['df']
        latest = df.iloc[-1]
        
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**【 均線與乖離 】**")
                st.write(f"MA5 (週線): {round(latest['MA5'], 1)}")
                st.write(f"MA20 (月線): {round(latest['MA20'], 1)}")
                bias = (data['price'] / latest['MA20'] - 1) * 100
                st.write(f"月線乖離: {round(bias, 1)}% ({'過熱' if bias>10 else '超跌' if bias<-10 else '正常'})")
            with t2:
                st.write("**【 量能與強弱 】**")
                st.write(f"今日成交量: {int(latest['Volume']/1000)} 張")
                vol_ratio = latest['Volume'] / df['Volume'].tail(5).mean()
                st.write(f"量能噴發比: {round(vol_ratio, 2)}x")
                st.write(f"RSI(14): {round(latest['RSI'], 1)}")
            with t3:
                st.write("**【 動能與指標 】**")
                st.write(f"MACD: {'📈 金叉' if data['macd'].iloc[-1, 0] > data['macd'].iloc[-1, 1] else '📉 死叉'}")
                st.write(f"布林上軌: {round(data['bbands'].iloc[-1, 2], 1)}")
                st.write(f"布林下軌: {round(data['bbands'].iloc[-1, 0], 1)}")
            with t4:
                st.write("**【 診斷與策略 】**")
                if data['price'] > latest['MA20']:
                    st.write("走勢評等: 🌕 強勢")
                else:
                    st.write("走勢評等: 🌑 弱勢")
                st.write("策略: " + ("觀望回檔" if bias > 8 else "尋找支撐"))

    else:
        st.error("❌ 無法取得數據。請確認代碼（如 2330, 3131）是否正確，或稍後再試。")

