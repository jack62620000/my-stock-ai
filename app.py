import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

# 1. 網頁頁面配置
st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 2. 建立 Google Sheets 連線與名稱對照 ---
@st.cache_data(ttl=300)
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 關鍵：對齊妳的分頁名稱「代碼對照表」
        df_gsheet = conn.read(worksheet="代碼對照表").astype(str)
        
        temp_dict = {}
        # 遍歷每一列，假設 A 欄是代碼，B 欄是中文名稱
        for i in range(len(df_gsheet)):
            try:
                code = df_gsheet.iloc[i, 0].strip()
                name = df_gsheet.iloc[i, 1].strip()
                if code.isdigit() and len(code) >= 4:
                    temp_dict[code] = name
            except:
                continue
        
        if temp_dict:
            st.sidebar.success(f"✅ 已成功載入 {len(temp_dict)} 檔對照資料")
        return temp_dict
    except Exception as e:
        st.sidebar.error("❌ 無法讀取『代碼對照表』分頁")
        return {}

name_map = get_stock_names()

# --- 3. 產業 PE 基準邏輯 ---
def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

# --- 4. 側邊欄與搜尋控制 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('正在同步全球財報與技術指標...'):
        try:
            # 自動嘗試上市 (.TW) 或 上櫃 (.TWO)
            stock_data = None
            info = {}
            df = pd.DataFrame()
            
            for suffix in [".TW", ".TWO"]:
                temp_stock = yf.Ticker(f"{code_input}{suffix}")
                temp_info = temp_stock.info
                if temp_info.get('currentPrice') or temp_info.get('regularMarketPrice'):
                    stock_data = temp_stock
                    info = temp_info
                    df = stock_data.history(period="150d")
                    if not df.empty: break

            if not info or df.empty:
                st.error(f"❌ 找不到代碼 {code_input} 的數據")
            else:
                # --- 標題：個股中文名稱 ---
                # 優先從試算表抓中文名，抓不到才用 Yahoo 的
                display_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
                st.title(f"📈 {display_name} ({code_input}) 戰情報告")

                # --- 運算邏輯 (還原試算表 B-T 欄) ---
                price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
                roe = info.get('returnOnEquity', 0) or 0
                debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
                fcf_raw = info.get('freeCashflow', 0) or 0
                eps = info.get('trailingEps', 0)
                sector_type, pe_bench = get_sector_pe(info.get('industry', ''))
                intrinsic = round(eps * pe_bench, 2)
                safety_val = (intrinsic / price) - 1 if price > 0 else 0
                pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5
                div_yield = info.get('dividendYield', 0) or 0

                # --- 第一區塊：基本面分析 ---
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
                    st.write(f"**負債比:** {round(debt_ratio*100,2)}%")
                    st.write(f"**殖利率:** {round(div_yield*100,2)}%")
                with m_col4:
                    st.write(f"**52週位階:** {round(pos_52*100,1)}%")
                    st.write(f"**流動比:** {round(info.get('currentRatio',0)*100,2)}%")
                    st.write(f"**營收成長:** {round(info.get('revenueGrowth',0)*100,2)}%")

                # T 欄深度洞察
                is_excellent = (roe > 0.18 and fcf_raw > 0)
                if is_excellent and safety_val > 0.1: insight = "💎【極致價值】體質卓越且定價低估，為核心首選。"
                elif fcf_raw <= 0: insight = "🚨【高度警戒】盈餘品質差(現金流負)。"
                else: insight = "⏳【中性觀望】數據處於中庸地帶。"
                st.info(f"**💡 全方位決策洞察 (T欄)：** {insight}")

                st.divider()

                # --- 第二區塊：走勢分析 ---
                st.markdown("### 📉 股價走勢分析")
                # 指標計算
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
                    st.write(f"**MACD趨勢:** {'📈 多方' if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else '📉 空方'}")
                    st.write(f"**量能噴發比:** {round(df['Volume'].iloc[-1]/df['Volume'].rolling(5).mean().iloc[-1], 2)}x")
                with t_col3:
                    st.write(f"**機構持股:** {round(info.get('heldPercentInstitutions', 0)*100, 2)}%")
                    st.write(f"**今日成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")

        except Exception as e:
            st.error(f"分析失敗，錯誤訊息: {e}")
else:
    st.info("👈 請在左側輸入台股代碼 (例如: 2317)")
