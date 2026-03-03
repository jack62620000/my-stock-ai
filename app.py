import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="家傳五星級存股戰情室", layout="wide")

# --- 1. 名稱對照 (Google Sheets) ---
@st.cache_data(ttl=600)
def get_stock_names():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_gsheet = conn.read(worksheet="代碼對照表").astype(str)
        return dict(zip(df_gsheet.iloc[:, 0].str.strip(), df_gsheet.iloc[:, 1].str.strip()))
    except:
        return {}

name_map = get_stock_names()

# --- 2. 核心數據抓取 (重新撰寫，解決找不到數據的問題) ---
def get_clean_data(code):
    # 嘗試上市與上櫃後綴
    for suffix in [".TW", ".TWO"]:
        ticker_str = f"{code}{suffix}"
        try:
            ticker = yf.Ticker(ticker_str)
            # 這裡改用 history 抓取，比 info 更穩定，不會被 404 擋掉
            hist = ticker.history(period="150d")
            
            if not hist.empty:
                # 抓取最新的價格
                latest_price = hist['Close'].iloc[-1]
                # 嘗試抓取 info，若失敗則給予預設值
                try:
                    info = ticker.info
                except:
                    info = {"shortName": ticker_str}
                
                # 強制注入價格，確保後面運算不會出錯
                if 'currentPrice' not in info or info['currentPrice'] is None:
                    info['currentPrice'] = latest_price
                
                return info, hist
        except:
            continue
    return None, None

# --- 3. UI 介面 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2330").strip()

if code_input:
    with st.spinner('正在分析中...'):
        info, df = get_clean_data(code_input)
        
        if info is None:
            st.error(f"❌ 無法取得 {code_input} 的數據。請確認代碼是否正確。")
        else:
            # 顯示名稱
            display_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
            st.title(f"📈 {display_name} ({code_input}) 戰情報告")

            # 數據運算 (B-T 欄核心邏輯)
            price = info.get('currentPrice', 0)
            roe = info.get('returnOnEquity', 0) or 0
            eps = info.get('trailingEps', 0) or 0
            fcf = info.get('freeCashflow', 0) or 0
            
            # 簡化版基準 PE 判斷
            pe_bench = 25 if "Semiconductors" in info.get('industry', '') else 15
            intrinsic = round(eps * pe_bench, 2)
            safety_val = (intrinsic / price) - 1 if price > 0 else 0

            # 區塊化呈現
            c1, c2, c3 = st.columns(3)
            c1.metric("目前現價", f"{round(price, 2)} 元")
            c2.metric("實證價值", f"{intrinsic} 元")
            c3.metric("安全邊際", f"{round(safety_val*100, 2)}%")

            # T 欄洞察
            st.markdown("---")
            if roe > 0.15 and fcf > 0:
                st.info(f"💡 **T欄洞察：** {display_name} 體質優異，現金流充沛。目前安全邊際為 {round(safety_val*100)}%。")
            else:
                st.warning(f"💡 **T欄洞察：** 數據顯示目前體質一般，建議觀察現金流與 ROE 變化。")

            # 走勢分析 (增加 RSI)
            st.subheader("📉 股價走勢分析")
            df['RSI'] = ta.rsi(df['Close'], length=14)
            st.write(f"**最新 RSI (14):** {round(df['RSI'].iloc[-1], 2)}")
            st.write(f"**20MA 狀態:** {'🌕 強勢期' if price > df['Close'].rolling(20).mean().iloc[-1] else '🌑 盤整期'}")

else:
    st.info("👈 請在左側輸入台股代碼 (如: 2317, 3131)")
