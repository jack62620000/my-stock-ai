import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

# 頁面配置
st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 1. 名稱對照 (加強穩定性) ---
@st.cache_data(ttl=600) # 快取 10 分鐘，避免頻繁請求
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 嘗試讀取
        df_gsheet = conn.read(worksheet="代碼對照表")
        df_gsheet.columns = [str(c).strip() for c in df_gsheet.columns] # 清理標題空白
        
        temp_dict = {}
        for i in range(len(df_gsheet)):
            try:
                code = str(df_gsheet.iloc[i, 0]).strip()
                name = str(df_gsheet.iloc[i, 1]).strip()
                if code.isdigit():
                    temp_dict[code] = name
            except: continue
        return temp_dict
    except Exception as e:
        # 如果失敗，不要中斷程式，只在側邊欄顯示警告
        st.sidebar.warning("⚠️ 試算表連線中...若持續失敗請檢查網址")
        return {}

name_map = get_stock_names()

# --- 2. 抓取 Yahoo 數據 (加入快取避免 Rate Limit) ---
@st.cache_data(ttl=3600) # 股價數據快取 1 小時
def fetch_stock_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            s = yf.Ticker(f"{code}{suffix}")
            inf = s.info
            # 檢查是否有基本數據
            if 'currentPrice' in inf or 'regularMarketPrice' in inf:
                h = s.history(period="150d")
                if not h.empty:
                    return inf, h
        except: continue
    return None, None

# --- 3. UI 控制台 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('正在分析數據，請稍候...'):
        info, df = fetch_stock_data(code_input)
        
        if info is None:
            st.error("❌ 無法取得數據。可能原因：代碼錯誤、Yahoo 流量限制 (請等5分鐘再試)。")
        else:
            # 顯示中文名稱
            display_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
            st.title(f"📈 {display_name} ({code_input}) 戰情報告")

            # 計算數據
            price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            eps = info.get('trailingEps', 0) or 1
            intrinsic = round(eps * 15, 2) # 預設基準 PE 15
            safety_val = (intrinsic / price) - 1 if price > 0 else 0

            # 顯示排版
            col1, col2, col3 = st.columns(3)
            col1.metric("目前現價", f"{price} 元")
            col2.metric("實證價值", f"{intrinsic} 元")
            col3.metric("安全邊際", f"{round(safety_val*100, 2)}%")

            st.divider()
            
            # 技術指標分析
            st.markdown("### 📉 股價走勢分析")
            rsi = ta.rsi(df['Close'], length=14).iloc[-1]
            st.write(f"**RSI (14):** {round(rsi, 2)}")
            st.write(f"**20MA 狀態:** {'🌕 強勢' if price > df['Close'].rolling(20).mean().iloc[-1] else '🌑 弱勢'}")

else:
    st.info("👈 請在左側輸入台股代碼開始分析")
