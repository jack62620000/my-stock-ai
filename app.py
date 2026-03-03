import streamlit as st
import yfinance as yf
import pandas as pd

# 網頁配置
st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

st.title("🚀 家傳五星級存股戰情室 (全功能完整版)")
st.sidebar.header("功能選單")
code_input = st.sidebar.text_input("請輸入台股代碼", placeholder="例如: 2330")

if code_input:
    with st.spinner('正在同步全球財報數據...'):
        try:
            # 1. 自動偵測上市櫃並抓取
            stock = yf.Ticker(f"{code_input}.TW")
            info = stock.info
            df = stock.history(period="120d")
            if not info.get('currentPrice') or df.empty:
                stock = yf.Ticker(f"{code_input}.TWO")
                info = stock.info
                df = stock.history(period="120d")

            # 2. 核心運算 (還原試算表 B-T 欄邏輯)
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            fcf_raw = info.get('freeCashflow', 0) or 0
            qr_raw = info.get('quickRatio') or 0
            cr_raw = info.get('currentRatio') or 0
            eps = info.get('trailingEps', 0)
            rev_growth = info.get('revenueGrowth', 0) or 0
            div_yield = info.get('dividendYield', 0) or 0
            sector_type, pe_bench = get_sector_pe(info.get('industry', ''))
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0
            pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5

            # S 欄：五星評等
            if roe > 0.18 and pos_52 < 0.35 and fcf_raw > 0: rating = "🌟 積極布局"
            elif safety_val > 0.1: rating = "🟢 分批買進"
            elif roe > 0.12 and pos_52 < 0.6: rating = "🟡 持有觀望"
            else: rating = "🚫 暫不考慮"

            # T 欄：全方位洞察 (維持最終定稿邏輯)
            is_excellent = (roe > 0.18 and fcf_raw > 0 and debt_ratio < 0.5)
            if is_excellent and safety_val > 0.15: insight = "💎【極致價值】體質卓越且定價低估，為核心首選。"
            elif is_excellent and safety_val < -0.15: insight = "📈【優質溢價】績優標的但目前預期透支，建議不加新倉。"
            elif fcf_raw <= 0: insight = "🚨【高度警戒】盈餘品質差(現金流負)，隨時有崩盤風險。"
            else: insight = "⏳【中性觀望】各項數據處於中庸地帶。"

            # 3. 呈現【台股分析】全欄位表格
            st.subheader(f"📊 {info.get('shortName')} (代號: {code_input}) - 台股分析")
            
            # 建立 DataFrame 模擬試算表欄位
            main_df = pd.DataFrame({
                "項目": ["現價", "ROE", "毛利率", "營益率", "負債比", "市場PE", "基準PE", "52週位階", "EPS", "實證價值", "現金流(億)", "流動比", "速動比", "殖利率", "營收成長率", "安全邊際", "五星評等"],
                "數據內容": [
                    f"{price} 元", f"{round(roe*100,2)}%", f"{round(info.get('grossMargins',0)*100,2)}%", f"{round(info.get('operatingMargins',0)*100,2)}%",
                    f"{round(debt_ratio*100,2)}%", f"{round(info.get('trailingPE',0),2)}", pe_bench, f"{round(pos_52*100,1)}%", eps, f"{intrinsic} 元",
                    f"{round(fcf_raw/100000000,2)} 億", f"{round(cr_raw*100,2)}%", f"{round(qr_raw*100,2)}%", f"{round(div_yield*100,2)}%",
                    f"{round(rev_growth*100,2)}%", f"{round(safety_val*100,2)}%", rating
                ]
            })
            st.table(main_df)
            st.info(f"**💡 全方位決策洞察 (T欄)：** {insight}")

            # 4. 呈現【股價走勢分析】欄位
            st.subheader("📈 股價走勢分析 (籌碼/量能指標)")
            cur_p = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            vol_today = df['Volume'].iloc[-1] / 1000
            avg_vol_5 = df['Volume'].rolling(5).mean().iloc[-1] / 1000
            amp = (df['High'].iloc[-1] - df['Low'].iloc[-1]) / df['Close'].iloc[-2]

            trend_df = pd.DataFrame({
                "走勢分析指標": ["五日均張變化", "量能噴發比", "股價振幅", "機構持股", "走勢評等"],
                "數值": [f"{round(vol_today - avg_vol_5, 1)} 張", f"{round(vol_today/avg_vol_5, 2)}x", f"{round(amp*100, 2)}%", f"{round(info.get('heldPercentInstitutions', 0)*100, 2)}%", "🌕強勢" if cur_p > ma20 else "🌑弱勢"]
            })
            st.table(trend_df)

        except Exception as e:
            st.error(f"分析失敗：請確認代號是否正確。")
