import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 1. 中文名稱抓取 (增加連線防錯) ---
@st.cache_data(ttl=300)
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_gsheet = conn.read(worksheet="台股分析")
        temp_dict = {}
        for i in range(len(df_gsheet)):
            try:
                code = str(df_gsheet.iloc[i, 0]).strip()
                name = str(df_gsheet.iloc[i, 1]).strip()
                if code.isdigit(): temp_dict[code] = name
            except: continue
        return temp_dict
    except:
        return {}

name_map = get_stock_names()

# --- 2. 側邊欄 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('AI 正在搜尋上市櫃數據...'):
        # --- 3. 強化的自動偵測邏輯 ---
        stock_data = None
        info = {}
        df = pd.DataFrame()
        
        # 依序嘗試 .TW (上市) 與 .TWO (上櫃)
        for suffix in [".TW", ".TWO"]:
            try:
                temp_stock = yf.Ticker(f"{code_input}{suffix}")
                temp_info = temp_stock.info
                # 檢查是否真的有抓到價格
                if temp_info.get('currentPrice') or temp_info.get('regularMarketPrice'):
                    stock_data = temp_stock
                    info = temp_info
                    df = stock_data.history(period="150d")
                    if not df.empty:
                        break # 抓到了，跳出迴圈
            except:
                continue

        # --- 4. 判斷是否成功抓取 ---
        if not info or df.empty:
            st.error(f"❌ 找不到代碼 {code_input} 的數據。請確認代碼是否正確，或 Yahoo Finance 暫時斷線。")
        else:
            # 決定名稱
            stock_display_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
            st.title(f"📈 {stock_display_name} ({code_input}) 戰情報告")

            # 數據運算
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
            fcf_raw = info.get('freeCashflow', 0) or 0
            eps = info.get('trailingEps', 0)
            
            # 基準PE邏輯
            ind = str(info.get('industry', ''))
            pe_bench = 15
            if any(k in ind for k in ["半導體", "IC設計"]): pe_bench = 25
            elif any(k in ind for k in ["電腦", "電子", "通訊"]): pe_bench = 20
            
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0
            
            # 顯示表格與洞察 (維持之前的精美排版)
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("目前現價", f"{price} 元")
            m_col2.metric("實證價值", f"{intrinsic} 元")
            m_col3.metric("安全邊際", f"{round(safety_val*100, 2)}%")
            
            # T 欄洞察
            is_excellent = (roe > 0.18 and fcf_raw > 0)
            if is_excellent and safety_val > 0.1: insight = "💎【優質低估】具備複利成長基因，且目前價格合理。"
            elif fcf_raw <= 0: insight = "🚨【注意現金流】雖然股價波動，但本業現金流入不敷出。"
            else: insight = "⏳【盤整觀望】數據處於中性區間。"
            st.info(f"**💡 全方位決策洞察 (T欄)：** {insight}")

            # 技術指標 (略，維持之前的呈現)
            st.divider()
            st.markdown("### 📉 股價走勢分析")
            t_col1, t_col2 = st.columns(2)
            t_col1.write(f"**今日成交量:** {int(df['Volume'].iloc[-1]/1000)} 張")
            t_col2.write(f"**20MA 狀態:** {'🌕 強勢' if price > df['Close'].rolling(20).mean().iloc[-1] else '🌑 弱勢'}")
