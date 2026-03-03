import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 網頁配置：設為寬屏幕模式
st.set_page_config(page_title="存股戰情室", layout="wide")

def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

# --- 側邊欄控制 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330")

if code_input:
    with st.spinner('數據讀取中...'):
        try:
            # 1. 抓取資料
            stock = yf.Ticker(f"{code_input}.TW")
            info = stock.info
            df = stock.history(period="120d")
            if not info.get('currentPrice') or df.empty:
                stock = yf.Ticker(f"{code_input}.TWO")
                info = stock.info
                df = stock.history(period="120d")

            # 2. 基礎數據 (台股分析)
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            fcf_raw = info.get('freeCashflow', 0) or 0
            eps = info.get('trailingEps', 0)
            sector_type, pe_bench = get_sector_pe(info.get('industry', ''))
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0
            pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5
            
            # --- 顯示中文名稱 ---
            stock_name = info.get('shortName', '未知名稱')
            st.title(f"📈 {stock_name} ({code_input}) 戰情報告")

            # --- 第一區塊：台股基本面分析 (橫向排版) ---
            st.markdown("### 📋 台股基本面分析")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("現價", f"{price} 元")
                st.write(f"**ROE:** {round(roe*100,2)}%")
                st.write(f"**毛利率:** {round(info.get('grossMargins',0)*100,2)}%")
            with m_col2:
                st.metric("實證價值", f"{intrinsic} 元")
                st.write(f"**營益率:** {round(info.get('operatingMargins',0)*100,2)}%")
                st.write(f"**負債比:** {round(debt_ratio*100,2)}%")
            with m_col3:
                st.metric("安全邊際", f"{round(safety_val*100,1)}%")
                st.write(f"**市場PE:** {round(info.get('trailingPE',0),2)}")
                st.write(f"**基準PE:** {pe_bench}")
            with m_col4:
                st.write(f"**EPS:** {eps}")
                st.write(f"**52週位階:** {round(pos_52*100,1)}%")
                st.write(f"**殖利率:** {round(info.get('dividendYield',0)*100,2)}%")

            # 體質補充與評等
            c1, c2, c3 = st.columns([1,1,2])
            c1.write(f"**流動比:** {round(info.get('currentRatio',0)*100,2)}%")
            c1.write(f"**速動比:** {round(info.get('quickRatio',0)*100,2)}%")
            c2.write(f"**現金流:** {round(fcf_raw/100000000,2)} 億")
            c2.write(f"**營收成長:** {round(info.get('revenueGrowth',0)*100,2)}%")
            
            # S 欄評等
            if roe > 0.18 and pos_52 < 0.35 and fcf_raw > 0: rating = "🌟 積極布局"
            elif safety_val > 0.1: rating = "🟢 分批買進"
            elif roe > 0.12 and pos_52 < 0.6: rating = "🟡 持有觀望"
            else: rating = "🚫 暫不考慮"
            c3.success(f"**五星評等：** {rating}")

            # T 欄深度洞察 (顯眼區塊)
            is_excellent = (roe > 0.18 and fcf_raw > 0 and debt_ratio < 0.5)
            if is_excellent and safety_val > 0.15: insight = f"💎【極致價值】體質卓越且定價低估(空間{round(safety_val*100)}%)。"
            elif is_excellent and safety_val < -0.15: insight = "📈【優質溢價】績優標的但目前預期透支。"
            elif fcf_raw <= 0: insight = "🚨【高度警戒】盈餘品質差(現金流負)。"
            else: insight = "⏳【中性觀望】各項數據處於中庸地帶。"
            st.info(f"**💡 全方位決策洞察 (T欄)：** {insight}")

            st.divider()

            # --- 第二區塊：股價走勢分析 (全欄位還原) ---
            st.markdown("### 📉 股價走勢分析")
            # 技術指標計算
            df['EMA12'] = ta.ema(df['Close'], length=12)
            df['EMA26'] = ta.ema(df['Close'], length=26)
            df['MACD'] = df['EMA12'] - df['EMA26']
            df['Signal'] = ta.ema(df['MACD'], length=9)
            rsi = ta.rsi(df['Close'], length=14).iloc[-1]
            kd = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            k_val = kd['STOCHk_9_3_3'].iloc[-1]
            d_val = kd['STOCHd_9_3_3'].iloc[-1]
            
            cur_p = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            vol_today = df['Volume'].iloc[-1] / 1000
            avg_vol_5 = df['Volume'].rolling(5).mean().iloc[-1] / 1000
            vol_ratio = vol_today / avg_vol_5
            amp = (df['High'].iloc[-1] - df['Low'].iloc[-1]) / df['Close'].iloc[-2]

            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                st.write(f"**RSI (14):** {round(rsi, 2)}")
                st.write(f"**K值:** {round(k_val, 2)} / **D值:** {round(d_val, 2)}")
                st.write(f"**MACD:** {'📈 多方' if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else '📉 空方'}")
            with t_col2:
                st.write(f"**五日均張變化:** {round(vol_today - avg_vol_5, 1)} 張")
                st.write(f"**量能噴發比:** {round(vol_ratio, 2)}x")
                st.write(f"**股價振幅:** {round(amp*100, 2)}%")
            with t_col3:
                st.write(f"**機構持股:** {round(info.get('heldPercentInstitutions', 0)*100, 2)}%")
                st.write(f"**20MA 走勢:** {'🌕 強勢' if cur_p > ma20 else '🌑 弱勢'}")
                st.write(f"**成交量 (張):** {int(vol_today)}")

        except Exception as e:
            st.error(f"分析失敗，錯誤訊息: {e}")
