import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="台股五星級 AI 戰情室", layout="wide")

# --- 1. 名稱對照 (加入防崩潰備案) ---
@st.cache_data(ttl=86400)
def get_names():
    names = {}
    try:
        # 嘗試從證交所抓取最新名單
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
                    "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df_list = pd.read_html(url)
            if df_list:
                df = df_list[0]
                for item in df[0]:
                    if '　' in str(item):
                        p = str(item).split('　')
                        names[p[0].strip()] = p[1].strip()
    except: pass 
    return names

name_map = get_names()

# --- 2. 數據抓取函式 (強化穩定度) ---
def get_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            t = yf.Ticker(f"{code}{suffix}")
            h = t.history(period="250d")
            if not h.empty:
                inf = t.info
                # 確保價格存在
                if 'currentPrice' not in inf or not inf['currentPrice']:
                    inf['currentPrice'] = h['Close'].iloc[-1]
                return inf, h
        except: continue
    return None, None

# --- 3. UI 介面設計 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('AI 正在讀取試算表所有欄位與數據...'):
        info, df = get_data(code_input)
        
        if info:
            name = name_map.get(code_input, f"個股 {code_input}")
            st.title(f"📈 {name} ({code_input}) 戰情報告")
            
            # --- 台股分析部分 (完全還原試算表第 1-4 列) ---
            st.header("📋 台股分析 (基本面與估值)")
            
            # 第一區：獲利品質
            with st.container(border=True):
                st.subheader("【 獲利品質與護城河 】")
                c1, c2, c3, c4 = st.columns(4)
                roe = info.get('returnOnEquity', 0)
                c1.metric("ROE (賺錢效率)", f"{round(roe*100, 2)}%", "卓越" if roe > 0.15 else "警戒")
                c2.metric("毛利率 (競爭力)", f"{round(info.get('grossMargins', 0)*100, 2)}%")
                c3.metric("營業利益率 (本業獲利)", f"{round(info.get('operatingMargins', 0)*100, 2)}%")
                debt = info.get('debtToEquity', 0) / 100
                c4.metric("負債比率 (財務壓力)", f"{round(debt*100, 1)}%", delta_color="inverse")
            
            # 第二區：成長與估值
            with st.container(border=True):
                st.subheader("【 成長性與估值分析 】")
                c1, c2, c3, c4 = st.columns(4)
                eps = info.get('trailingEps', 0) or 0
                ind = info.get('industry', '')
                pe_bench = 22.5 if "Semiconductors" in ind else 15
                intrinsic = eps * pe_bench
                c1.metric("實證合理價", f"{round(intrinsic, 1)} 元")
                c2.metric("近四季 EPS", f"{eps} 元")
                low_52, high_52 = df['Low'].min(), df['High'].max()
                pos_52 = (info['currentPrice'] - low_52) / (high_52 - low_52)
                c3.metric("52週位階", f"{round(pos_52*100, 1)}%", "過熱" if pos_52 > 0.75 else "低檔")
                safety = (intrinsic / info['currentPrice']) - 1
                c4.metric("安全邊際", f"{round(safety*100, 1)}%", "具補漲空間" if safety > 0.1 else "溢價")

            # AI 診斷 (T 欄)
            if roe > 0.18 and pos_52 < 0.35: res = "🌟【卓越成長】高獲利品質且低位階。"
            elif safety > 0.1: res = "🟢【分批買進】體質穩健且具備補漲空間。"
            else: res = "⏳【中性觀望】各項數據處於盤整區。"
            st.info(f"**🤖 AI 全方位決策洞察：** {res}")

            st.divider()

            # --- 股價走勢分析部分 ---
            st.header("📉 股價走勢分析 (技術指標)")
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            with st.container(border=True):
                st.subheader("【 均線與動能指標 】")
                g1, g2, g3 = st.columns(3)
                g1.write(f"**MA5 (週線):** {round(df['MA5'].iloc[-1], 1)}")
                g1.write(f"**MA20 (月線):** {round(df['MA20'].iloc[-1], 1)}")
                g2.write(f"**RSI (14):** {round(df['RSI'].iloc[-1], 1)}")
                g2.write(f"**成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")
                bias = (info['currentPrice'] / df['MA20'].iloc[-1] - 1) * 100
                g3.write(f"**乖離率:** {round(bias, 2)}% ({'過熱' if bias > 10 else '正常'})")
                g3.write(f"**走勢評等:** {'🌕 強勢' if info['currentPrice'] > df['MA20'].iloc[-1] else '🌑 弱勢'}")
        else:
            st.error("❌ 抓取數據失敗。請確認代號（如 2330）是否正確，或稍後再試。")
