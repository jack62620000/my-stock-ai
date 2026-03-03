import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 1. 【核心修正】更精準的中文名稱抓取邏輯 ---
@st.cache_data(ttl=300)
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 讀取「台股分析」分頁
        df_gsheet = conn.read(worksheet="台股分析")
        
        # 這裡改用循環掃描，確保不受標頭行數影響
        # 尋找任何看起來像股票代碼(數字)的格子，並抓取它右邊那格
        temp_dict = {}
        for index, row in df_gsheet.iterrows():
            code = str(row.iloc[0]).strip() # 假設 A 欄是代碼
            name = str(row.iloc[1]).strip() # 假設 B 欄是名稱
            if code.isdigit() and len(code) >= 4: # 如果是 4 位數以上的數字
                temp_dict[code] = name
        return temp_dict
    except Exception as e:
        return {}

name_map = get_stock_names()

# --- 2. 產業 PE 基準 ---
def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

# --- 3. UI 介面 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('正在讀取數據...'):
        try:
            stock = yf.Ticker(f"{code_input}.TW")
            info = stock.info
            df = stock.history(period="150d")
            if not info.get('currentPrice') or df.empty:
                stock = yf.Ticker(f"{code_input}.TWO")
                info = stock.info
                df = stock.history(period="150d")

            # --- 顯示中文名稱 ---
            # 如果對照表裡有，就顯示中文；沒有的話，強行顯示代碼
            stock_display_name = name_map.get(code_input, f"個股 {code_input}")
            st.title(f"📈 {stock_display_name} 戰情報告")

            # --- 數據運算 (基本面) ---
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            fcf_raw = info.get('freeCashflow', 0) or 0
            eps = info.get('trailingEps', 0)
            sector_type, pe_bench = get_sector_pe(info.get('industry', ''))
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0
            pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5

            # 第一區塊排版
            st.markdown("### 📋 台股基本面分析")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("目前現價", f"{price} 元")
                st.write(f"**ROE:** {round(roe*100,2)}%")
                st.write(f"**毛利率:** {round(info.get('grossMargins',0)*100,2)}%")
            with m_col2:
                st.metric("實證價值", f"{intrinsic} 元")
                st.write(f"**EPS:** {eps}")
                st.write(f"**市場PE:** {round(info.get('trailingPE',0),2)}")
            with m_col3:
                st.metric("安全邊際", f"{round(safety_val*100,2)}%")
                st.write(f"**現金流:** {round(fcf_raw/100000000,2)} 億")
                st.write(f"**負債比:** {round(debt_ratio*100,2)}%")
            with m_col4:
                st.write(f"**52週位階:** {round(pos_52*100,1)}%")
                st.write(f"**殖利率:** {round(info.get('dividendYield',0)*100,2)}%")
                st.write(f"**營收成長:** {round(info.get('revenueGrowth',0)*100,2)}%")

            # T 欄洞察
            is_excellent = (roe > 0.18 and fcf_raw > 0 and debt_ratio < 0.5)
            if is_excellent and safety_val > 0.15: insight = "💎【極致價值】體質卓越且定價低估，為核心首選。"
            elif is_excellent and safety_val < -0.15: insight = "📈【優質溢價】績優標的但目前預期透支。"
            elif fcf_raw <= 0: insight = "🚨【高度警戒】盈餘品質差(現金流負)。"
            else: insight = "⏳【中性觀望】數據處於中庸地帶。"
            st.info(f"**💡 全方位決策洞察 (T欄)：** {insight}")

            st.divider()

            # 第二區塊：走勢分析
            st.markdown("### 📉 股價走勢分析")
            df['EMA12'] = ta.ema(df['Close'], length=12)
            df['EMA26'] = ta.ema(df['Close'], length=26)
            df['MACD'] = df['EMA12'] - df['EMA26']
            df['Signal'] = ta.ema(df['MACD'], length=9)
            rsi = ta.rsi(df['Close'], length=14).iloc[-1]
            kd = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            k_val, d_val = kd['STOCHk_9_3_3'].iloc[-1], kd['STOCHd_9_3_3'].iloc[-1]
            
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                st.write(f"**RSI (14):** {round(rsi, 2)}")
                st.write(f"**KD值:** K {round(k_val,1)} / D {round(d_val,1)}")
            with t_col2:
                st.write(f"**MACD:** {'📈 多方' if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else '📉 空方'}")
                st.write(f"**量能噴發比:** {round(df['Volume'].iloc[-1]/df['Volume'].rolling(5).mean().iloc[-1], 2)}x")
            with t_col3:
                st.write(f"**機構持股:** {round(info.get('heldPercentInstitutions', 0)*100, 2)}%")
                st.write(f"**今日成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")

        except Exception as e:
            st.error(f"分析失敗，請檢查代碼或稍後再試。")
