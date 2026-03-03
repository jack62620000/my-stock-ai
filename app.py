import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="巴菲特台股戰情室", layout="wide")

# --- 1. 名稱與參數對照 (對應您的試算表標籤) ---
@st.cache_data(ttl=86400)
def get_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="代碼對照表").astype(str)
        return dict(zip(df.iloc[:, 0].str.strip(), df.iloc[:, 1].str.strip()))
    except:
        return {}

name_map = get_names()

# --- 2. 核心數據抓取與計算 (還原試算表公式) ---
def get_stock_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            
            info = ticker.info
            # 基本資訊
            price = hist['Close'].iloc[-1]
            low_52 = hist['Low'].min()
            high_52 = hist['High'].max()
            
            # 1. 獲利品質與護城河
            roe = info.get('returnOnEquity', 0)
            gp_margin = info.get('grossMargins', 0)
            op_margin = info.get('operatingMargins', 0)
            debt_to_equity = (info.get('debtToEquity', 0)) / 100
            
            # 2. 成長性與估值 (J、K、L 欄公式)
            eps = info.get('trailingEps', 0)
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0.5
            
            # 基準 PE 判斷 (I 欄邏輯)
            ind = info.get('industry', '')
            pe_bench = 20 if any(k in ind for k in ["Semiconductors", "Computer", "Electronics"]) else 15
            intrinsic = eps * pe_bench
            
            # 3. 進階風險 (M、O、P、Q 欄)
            fcf = info.get('freeCashflow', 0) / 100000000 # 轉億元
            current_ratio = info.get('currentRatio', 0)
            div_yield = info.get('dividendYield', 0)
            rev_growth = info.get('revenueGrowth', 0)
            
            # 4. 決策支援 (R、S 欄)
            safety_margin = (intrinsic / price) - 1 if price > 0 else 0
            
            return {
                "price": price, "roe": roe, "gp": gp_margin, "op": op_margin, "debt": debt_to_equity,
                "eps": eps, "pos_52": pos_52, "pe_bench": pe_bench, "intrinsic": intrinsic,
                "fcf": fcf, "current_ratio": current_ratio, "div_yield": div_yield, "rev_growth": rev_growth,
                "safety": safety_margin, "industry": ind, "df": hist
            }
        except: continue
    return None

# --- 3. UI 介面顯示 ---
code_input = st.sidebar.text_input("輸入台股代碼 (如: 2330, 2317)").strip()

if code_input:
    data = get_stock_metrics(code_input)
    if data:
        name = name_map.get(code_input, f"個股 {code_input}")
        st.title(f"📈 {name} ({code_input}) 全方位戰情報告")
        
        # --- 第一區塊：獲利品質與估值 (試算表 A-L 欄) ---
        st.subheader("🛡️ 獲利品質與核心估值")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("目前股價", f"{round(data['price'], 1)} 元")
        col2.metric("實證合理價", f"{round(data['intrinsic'], 1)} 元")
        col3.metric("安全邊際", f"{round(data['safety']*100, 1)}%")
        col4.metric("52週位階", f"{round(data['pos_52']*100, 1)}%")
        
        # --- 第二區塊：進階風險過濾 (試算表 M-Q 欄) ---
        st.markdown("---")
        st.subheader("🔍 進階財務風險過濾")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.write(f"**ROE:** {round(data['roe']*100, 2)}% {'✅' if data['roe']>0.15 else '⚠️'}")
            st.write(f"**毛利率:** {round(data['gp']*100, 2)}%")
        with f2:
            st.write(f"**自由現金流:** {round(data['fcf'], 1)} 億")
            st.write(f"**營收年增率:** {round(data['rev_growth']*100, 1)}%")
        with f3:
            st.write(f"**流動比率:** {round(data['current_ratio']*100, 1)}%")
            st.write(f"**負債比率:** {round(data['debt']*100, 1)}%")
        with f4:
            st.write(f"**現金殖利率:** {round(data['div_yield']*100, 2)}%")
            st.write(f"**基準 PE:** {data['pe_bench']} 倍")

        # --- 第三區塊：AI 數據分析與診斷 (試算表 T 欄) ---
        st.markdown("---")
        # 根據您試算表的 T 欄判斷邏輯進行自動化診斷 
        if data['roe'] > 0.18 and data['pos_52'] < 0.35:
            insight = "🌟【卓越成長】高獲利且低位階，屬極品標的。"
        elif data['safety'] > 0.1:
            insight = "🟢【分批買進】體質穩健且具備補漲空間。"
        elif data['pos_52'] > 0.8:
            insight = "🟠【過熱警戒】位階過高，建議「不加新倉」靜待回檔。"
        elif data['roe'] < 0.08:
            insight = "🚫【暫不考慮】獲利能力低於基準，缺乏吸引力。"
        else:
            insight = "⏳【中性觀望】各項數據處於中庸地帶，建議保留現金彈性。"
        
        st.info(f"**🤖 AI 全方位決策洞察：** {insight}")

        # --- 第四區塊：股價走勢分析 ---
        st.divider()
        st.subheader("📉 股價技術走勢")
        df = data['df']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        
        t1, t2, t3 = st.columns(3)
        t1.write(f"**最新 RSI (14):** {round(df['RSI'].iloc[-1], 2)}")
        t2.write(f"**20MA 趨勢:** {'🌕 多方' if data['price'] > ma20 else '🌑 空方'}")
        t3.write(f"**成交量狀態:** {int(df['Volume'].iloc[-1]/1000)} 張")
