import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 1. 中文名稱對應 (對齊代碼對照表) ---
@st.cache_data(ttl=600)
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 讀取「代碼對照表」分頁
        df_gsheet = conn.read(worksheet="代碼對照表").astype(str)
        # 假設 A 欄代碼，B 欄中文名
        return dict(zip(df_gsheet.iloc[:, 0].str.strip(), df_gsheet.iloc[:, 1].str.strip()))
    except:
        return {}

name_map = get_stock_names()

# --- 2. 穩定版數據抓取函數 ---
def get_clean_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="150d")
            if not hist.empty:
                try:
                    info = ticker.info
                except:
                    info = {}
                # 確保價格一定存在
                info['currentPrice'] = hist['Close'].iloc[-1]
                return info, hist
        except:
            continue
    return None, None

# --- 3. UI 介面 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('戰情室數據同步中...'):
        info, df = get_clean_data(code_input)
        
        if info is None:
            st.error(f"❌ 找不到代碼 {code_input}")
        else:
            # 標題顯示
            stock_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
            st.title(f"📈 {stock_name} ({code_input}) 戰情報告")

            # 數據計算
            price = info['currentPrice']
            roe = info.get('returnOnEquity', 0) or 0
            eps = info.get('trailingEps', 0) or 0
            # 基準 PE 判斷
            pe_bench = 25 if "Semiconductors" in info.get('industry', '') else 15
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0

            # --- 第一區塊：排版還原 ---
            st.markdown("### 📋 台股基本面分析")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("目前現價", f"{round(price, 2)} 元")
                st.write(f"**ROE:** {round(roe*100, 2)}%")
            with m2:
                st.metric("實證價值", f"{intrinsic} 元")
                st.write(f"**EPS:** {eps}")
            with m3:
                st.metric("安全邊際", f"{round(safety_val*100, 1)}%")
                st.write(f"**基準PE:** {pe_bench}")
            with m4:
                st.write(f"**毛利率:** {round(info.get('grossMargins', 0)*100, 2)}%")
                st.write(f"**營收成長:** {round(info.get('revenueGrowth', 0)*100, 2)}%")

            # T欄洞察
            if roe > 0.15:
                st.info(f"💡 **T欄洞察：** {stock_name} 獲利能力優異，安全邊際為 {round(safety_val*100)}%。")
            else:
                st.warning(f"💡 **T欄洞察：** 目前成長動能平平，建議分批觀察。")

            st.divider()

            # --- 第二區塊：走勢分析 ---
            st.markdown("### 📉 股價走勢分析")
            df['RSI'] = ta.rsi(df['Close'], length=14)
            t1, t2, t3 = st.columns(3)
            with t1:
                st.write(f"**最新 RSI:** {round(df['RSI'].iloc[-1], 2)}")
            with t2:
                st.write(f"**20MA 走勢:** {'🌕 強勢' if price > df['Close'].rolling(20).mean().iloc[-1] else '🌑 盤整'}")
            with t3:
                st.write(f"**今日成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")
