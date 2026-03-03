import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股AI戰情室 - 完整版", layout="wide")

@st.cache_data(ttl=86400)
def get_all_stock_names():
    names_dict = {}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    p = str(item).split('　')
                    if len(p) >= 2: names_dict[p[0].strip()] = p[1].strip()
        return names_dict
    except: return {"2330": "台積電", "3131": "弘塑"}

name_map = get_all_stock_names()

def get_full_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            
            # --- 技術指標計算 (對齊試算表) ---
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            macd = ta.macd(df['Close'])
            bbands = ta.bbands(df['Close'], length=20, std=2)
            
            return {"info": info, "df": df, "stoch": stoch, "macd": macd, "bbands": bbands, "price": hist['Close'].iloc[-1]}
        except: continue
    return None

# --- UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入代碼", placeholder="3131").strip()

if code_input:
    d = get_full_data(code_input)
    if d:
        name = name_map.get(code_input, code_input)
        st.title(f"📊 {name} ({code_input}) 完整診斷報告")

        # --- 第一部分：台股分析 (精簡展示) ---
        # (此處保留妳原本的基本面邏輯，略過不重寫以節省篇幅)

        # --- 第二部分：股價走勢分析 (全欄位還原) ---
        st.header("📉 股價走勢分析 (各項欄位數據與判斷)")
        
        df, latest = d['df'], d['df'].iloc[-1]
        
        # 1. 均線與乖離
        with st.container(border=True):
            st.subheader("【 均線與乖離 】")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("MA5 (週線)", f"{round(latest['MA5'],1)}", help="短線多空強弱")
            c2.metric("MA20 (月線)", f"{round(latest['MA20'],1)}", help="中線生命支撐")
            c3.metric("MA60 (季線)", f"{round(latest['MA60'],1)}", help="長線趨勢方向")
            bias = (d['price'] / latest['MA20'] - 1) * 100
            status = "🔥過熱" if bias > 10 else "❄️超跌" if bias < -10 else "✅正常"
            c4.metric("乖離率 (%)", f"{round(bias, 2)}%", status)

        # 2. 量能與強弱
        with st.container(border=True):
            st.subheader("【 量能與強弱 】")
            c1, c2, c3, c4 = st.columns(4)
            vol_now = int(latest['Volume']/1000)
            c1.metric("當日成交量", f"{vol_now} 張")
            vol_avg = int(df['Volume'].tail(5).mean()/1000)
            c2.metric("5日成交均量", f"{vol_avg} 張")
            v_ratio = latest['Volume'] / (df['Volume'].shift(1).iloc[-1])
            v_status = "放量" if v_ratio > 1.5 else "縮量"
            c3.metric("能量變化", v_status, f"{round(v_ratio,2)}x")
            c4.metric("RSI(14)", f"{round(latest['RSI'],1)}", "過熱" if latest['RSI']>70 else "超賣" if latest['RSI']<30 else "")

        # 3. 動能與指標 (KD / MACD)
        with st.container(border=True):
            st.subheader("【 動能與指標 】")
            c1, c2, c3, c4 = st.columns(4)
            k, d_val = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
            c1.metric("K值", f"{round(k,1)}")
            c2.metric("D值", f"{round(d_val,1)}", "多頭交叉" if k>d_val else "空頭交叉")
            m_hist = d['macd'].iloc[-1, 2] # MACD Histogram
            c3.metric("MACD柱狀體", f"{round(m_hist, 2)}", "翻紅" if m_hist>0 else "翻綠")
            amp = (latest['High'] - latest['Low']) / latest['Low'] * 100
            c4.metric("股價振幅", f"{round(amp, 2)}%")

        # 4. 籌碼與區間 (布林通道)
        with st.container(border=True):
            st.subheader("【 籌碼與區間 】")
            c1, c2, c3, c4 = st.columns(4)
            up, low = d['bbands'].iloc[-1, 2], d['bbands'].iloc[-1, 0]
            c1.metric("布林上軌(壓力)", f"{round(up, 1)}")
            c2.metric("布林下軌(支撐)", f"{round(low, 1)}")
            c3.metric("走勢評等", "🌕 強勢" if d['price'] > latest['MA20'] else "🌑 弱勢")
            # 策略建議
            advice = "分批佈局" if latest['RSI'] < 40 else "觀望回檔" if bias > 8 else "持股續抱"
            c4.metric("策略建議", advice)

        # 5. 技術診斷總結
        st.divider()
        st.subheader("💡 綜合技術診斷")
        diag = []
        if k > d_val: diag.append("✅ KD金叉：短線動能轉強。")
        if m_hist > 0: diag.append("✅ MACD翻紅：趨勢偏多。")
        if d['price'] > up: diag.append("⚠️ 股價突破布林上軌：注意短線乖離修正。")
        if latest['RSI'] > 75: diag.append("🚨 RSI 過熱：避免追高。")
        
        if not diag: diag.append("目前趨勢盤整，無明顯買賣訊號。")
        for line in diag: st.write(line)

    else:
        st.error("❌ 抓取數據失敗。")
