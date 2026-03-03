import streamlit as st
import yfinance as yf
import pandas as pd
import time

# 網頁寬度與標題
st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

st.title("🚀 家傳五星級存股戰情室")
st.sidebar.header("控制台")
code_input = st.sidebar.text_input("請輸入台股代碼", placeholder="例如: 2330")

if code_input:
    with st.spinner('AI 正在進行多因子聯動分析...'):
        try:
            # 資料抓取
            stock = yf.Ticker(f"{code_input}.TW")
            info = stock.info
            df = stock.history(period="120d")
            if not info.get('currentPrice') or df.empty:
                stock = yf.Ticker(f"{code_input}.TWO")
                info = stock.info
                df = stock.history(period="120d")

            # 數據運算 (台股分析)
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            fcf_raw = info.get('freeCashflow', 0) or 0
            eps = info.get('trailingEps', 0)
            sector_type, pe_bench = get_sector_pe(info.get('industry', ''))
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0
            pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5

            # T 欄深度洞察 (定稿邏輯)
            is_excellent = (roe > 0.18 and fcf_raw > 0 and debt_ratio < 0.5)
            is_cheap = (safety_val > 0.15)
            is_expensive = (safety_val < -0.15)
            is_low_pos = (pos_52 < 0.35)
            
            if is_excellent and is_cheap:
                insight = f"💎【極致價值】體質卓越且定價低估(空間{round(safety_val*100)}%)。此標的具複利成長基因，低位階提供極高安全邊際，為核心首選。"
            elif is_excellent and is_expensive:
                insight = f"📈【優質溢價】績優標的但目前預期透支。雖然ROE亮眼，但高溢價抵銷回報，建議「持股續抱、不加新倉」。"
            elif not is_excellent and is_cheap and is_low_pos:
                insight = f"🩹【低位修復】體質平庸但股價超跌，具{round(safety_val*100)}%估值修復空間。適合短線賺取反彈。"
            elif fcf_raw <= 0 and is_expensive:
                insight = "🚨【高度警戒】盈餘品質差且股價嚴重過熱。隨時有崩盤風險，應逢高減碼。"
            else:
                insight = "⏳【中性觀望】各項數據處於中庸地帶，建議保留現金彈性。"

            # 呈現台股分析表
            st.subheader(f"📊 {info.get('shortName')} - 台股基本面分析")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("現價", f"{price} 元")
            col2.metric("ROE", f"{round(roe*100, 2)}%")
            col3.metric("安全邊際", f"{round(safety_val*100, 1)}%")
            col4.metric("實證價值", f"{intrinsic} 元")
            
            st.info(f"**全方位決策洞察 (T欄)：** {insight}")

            # 走勢分析數據
            cur_p = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            vol_today = df['Volume'].iloc[-1] / 1000
            avg_vol_5 = df['Volume'].rolling(5).mean().iloc[-1] / 1000
            amp = (df['High'].iloc[-1] - df['Low'].iloc[-1]) / df['Close'].iloc[-2]

            st.subheader("📈 股價走勢分析 (技術/籌碼)")
            st.table(pd.DataFrame({
                "五日均張變化": [f"{round(vol_today - avg_vol_5, 1)} 張"],
                "量能噴發比": [f"{round(vol_today/avg_vol_5, 2)}x"],
                "股價振幅": [f"{round(amp*100, 2)}%"],
                "機構持股": [f"{round(info.get('heldPercentInstitutions', 0)*100, 2)}%"],
                "走勢狀態": ["🌕強勢" if cur_p > ma20 else "🌑弱勢"]
            }))

        except Exception as e:
            st.error(f"分析失敗，請檢查代號是否正確。錯誤訊息: {e}")