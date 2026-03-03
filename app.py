import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="五星存股戰情室", layout="wide")

# --- 1. 自動化名稱對照 (Google Sheets + 證交所備援) ---
@st.cache_data(ttl=86400) # 一天只抓一次網路資料，效率最高
def get_stock_names():
    names = {}
    # 第一步：嘗試從 Google Sheets 抓取
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_gsheet = conn.read(worksheet="代碼對照表").astype(str)
        names = dict(zip(df_gsheet.iloc[:, 0].str.strip(), df_gsheet.iloc[:, 1].str.strip()))
        if names: return names
    except:
        pass # 如果失敗，進行下一步

    # 第二步：【自動化核心】直接從台灣證交所網路抓取 (備援方案)
    try:
        # 抓取上市清單
        tw_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        df_tw = pd.read_html(tw_url)[0]
        # 抓取上櫃清單
        two_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        df_two = pd.read_html(two_url)[0]
        
        # 整理數據：將代碼與名稱拆開 (原始資料格式為 "2330 台積電")
        full_df = pd.concat([df_tw, df_two])
        for item in full_df[0]:
            parts = item.split('\u3000') # 證交所中間用全型空白隔開
            if len(parts) == 2:
                names[parts[0]] = parts[1]
        return names
    except:
        return {"2330": "台積電", "2317": "鴻海"} # 萬一連網路都掛了的最後防線

name_map = get_stock_names()

# --- 2. 數據抓取邏輯 (維持上次成功的版本) ---
def get_clean_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="150d")
            if not hist.empty:
                try: info = ticker.info
                except: info = {}
                info['currentPrice'] = hist['Close'].iloc[-1]
                return info, hist
        except: continue
    return None, None

# --- 3. UI 顯示 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼 (如: 2317)").strip()

if code_input:
    info, df = get_clean_data(code_input)
    if info:
        # 這裡就會優先抓到中文名稱了！
        display_name = name_map.get(code_input, info.get('shortName', f"個股 {code_input}"))
        st.title(f"📈 {display_name} ({code_input}) 戰情報告")
        
        # ... 後續排版同前 ...
        st.metric("目前價格", f"{info['currentPrice']} 元")
    else:
        st.error("找不到該代碼數據。")
