import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="巴菲特台股全自動戰情室", layout="wide")

# --- 1. 自動名稱對照 (證交所備援機制) ---
@st.cache_data(ttl=86400)
def get_all_stock_names():
    names = {}
    try:
        # 上市與上櫃清單同步抓取
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
                    "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    parts = str(item).split('　')
                    if len(parts) >= 2: names[parts[0].strip()] = parts[1].strip()
        return names
    except:
        return {"2330": "台積電", "2317": "鴻海", "3131": "弘塑"}

name_map = get_all_stock_names()

# --- 2. 核心數據運算 (對齊試算表 A-T 欄) ---
def get_full_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # 【台股分析工作表】關鍵指標擷取
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_margin = info.get('grossMargins', 0) or 0
            op_margin = info.get('operatingMargins', 0) or 0
            current_ratio = info.get('currentRatio', 0) or 0
            debt_ratio = info.get('debtToEquity', 0) / 100
            div_yield = info.get('dividendYield', 0) or 0
            rev_growth = info.get('revenueGrowth', 0) or 0
            fcf = info.get('freeCashflow', 0) / 100000000 # 億元
            
            # 【估值邏輯】
            pe_bench = 25 if any(k in str(info.get('industry','')) for k in ["Semiconductors", "Computer"]) else 15
            intrinsic = eps * pe_bench
            safety = (intrinsic / price) - 1 if price > 0 else 0
            pos_52 = (price - hist['Low'].min()) / (hist['High'].max() - hist['Low'].min())
            
            # 【股價走勢分析】技術指標
            df = hist.copy()
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            macd = ta.macd(df['Close'])
            
            return {
                "price": price, "name": name_map.get(code, info.get('shortName', code)),
                "intrinsic": intrinsic, "safety": safety, "pos_52": pos_52,
                "roe": roe, "eps": eps, "gp": gp_margin, "op": op_margin,
                "current": current_ratio, "debt": debt_ratio, "div": div_yield, 
                "rev": rev_growth, "fcf": fcf, "df": df, "macd": macd, "pe_bench": pe_bench
            }
        except: continue
    return None

# --- 3. UI 介面展示 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="例如: 3131").strip()

if code_input:
    d = get_full_metrics(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 戰情報告")
        
        # 區塊一：核心估值與位階 (A-L 欄)
        st.subheader("💎 獲利品質與核心估值")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("目前股價", f"{round(d['price'], 1)} 元")
        m2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", help=f"EPS({d['eps']}) x 基準PE({d['pe_bench']})")
        m3.metric("安全邊際", f"{round(d['safety']*100, 1)}%")
        m4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%")

        # 區塊二：財務健康過濾 (M-Q 欄)
        st.markdown("---")
        st.subheader("🔍 進階財務風險過濾")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write(f"**ROE:** {round(d['roe']*100, 2)}% {'✅' if d['roe']>0.15 else '⚠️'}")
            st.write(f"**毛利率:** {round(d['gp']*100, 2)}%")
        with f2:
            st.write(f"**自由現金流:** {round(d['fcf'], 1)} 億")
            st.write(f"**營收年增率:** {round(d['rev']*100, 1)}%")
        with f3:
            st.write(f"**流動比率:** {round(d['current']*100, 1)}%")
            st.write(f"**負債比率:** {round(d['debt']*100, 1)}%")
        with f4:
            st.write(f"**現金殖利率:** {round(d['div']*100, 2)}%")
            st.write(f"**實證 PE:** {d['pe_bench']} 倍")

        # 區塊三：AI 全方位決策 (T 欄)
        st.markdown("---")
        if d['roe'] > 0.18 and d['safety'] > 0.1: 
            res = "🌟【卓越成長】高獲利且低估值，適合長線佈局。"
        elif d['pos_52'] > 0.85: 
            res = "🟠【過熱警戒】位階過高，建議等待回檔不追高。"
        elif d['fcf'] < 0: 
            res = "🚨【現金流警訊】盈餘品質不佳，需注意資金周轉。"
        else: 
            res = "⏳【中性觀望】目前數據處於平衡點，建議分批入場。"
        st.info(f"**🤖 AI 決策判斷：** {res}")

        # 區塊四：股價走勢分析 (技術指標欄位)
        st.divider()
        st.subheader("📉 股價走勢與技術指標")
        t1, t2, t3, t4 = st.columns(4)
        latest_rsi = d['df']['RSI'].iloc[-1]
        t1.write(f"**RSI (14):** {round(latest_rsi, 1)} {'🔥超買' if latest_rsi>70 else '❄️超賣' if latest_rsi<30 else ''}")
        t2.write(f"**20MA 趨勢:** {'🌕多頭' if d['price'] > d['df']['MA20'].iloc[-1] else '🌑空頭'}")
        t3.write(f"**生命線(60MA):** {round(d['df']['MA60'].iloc[-1], 1)}")
        t4.write(f"**MACD 狀態:** {'📈金叉' if d['macd'].iloc[-1, 0] > d['macd'].iloc[-1, 1] else '📉死叉'}")

    else:
        st.error("找不到該代碼數據，請檢查代碼是否正確。")
