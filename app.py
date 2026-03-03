import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股 AI 戰情室 (透明數據版)", layout="wide")

@st.cache_data(ttl=86400)
def get_all_stock_names():
    # ... (維持原本證交所抓取邏輯) ...
    return {"2330": "台積電", "2317": "鴻海", "3131": "弘塑"}

name_map = get_all_stock_names()

def get_stock_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- 計算邏輯 ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            
            # 產業 PE 基準公式
            ind = info.get('industry', '')
            if "Semiconductor" in ind: pe_bench = 22.5
            elif "Financial" in ind: pe_bench = 14
            else: pe_bench = 12
            
            intrinsic = eps * pe_bench
            safety = (intrinsic / price) - 1 if price > 0 else 0
            low_52, high_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0
            
            return {
                "price": price, "roe": roe, "eps": eps, "intrinsic": intrinsic, 
                "safety": safety, "pos_52": pos_52, "info": info, "df": hist, "pe_b": pe_bench
            }
        except: continue
    return None

# --- UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼").strip()

if code_input:
    data = get_stock_metrics(code_input)
    if data:
        stock_name = name_map.get(code_input, f"個股 {code_input}")
        st.title(f"📈 {stock_name} ({code_input}) 數據來源透明化報告")

        # 第一部分：獲利與估值
        st.subheader("🛡️ 核心數據 (原始來源 vs 公式換算)")
        c1, c2, c3, c4 = st.columns(4)
        
        c1.metric("目前股價", f"{round(data['price'], 1)} 元", help="[數據來源] Yahoo Finance 即時報價")
        c2.metric("實證合理價", f"{round(data['intrinsic'], 1)} 元", 
                  help=f"[公式換算] 近四季 EPS ({data['eps']}) × 基準 PE ({data['pe_b']})")
        c3.metric("安全邊際", f"{round(data['safety']*100, 1)}%", 
                  help="[公式換算] (合理價 ÷ 目前股價) - 1")
        c4.metric("52週位階", f"{round(data['pos_52']*100, 1)}%", 
                  help="[公式換算] (目前價 - 一年最低) ÷ (一年最高 - 一年最低)")

        # 第二部分：財務細項
        st.markdown("---")
        st.write("### 🔍 財務指標來源說明")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.write(f"**ROE:** {round(data['roe']*100, 2)}% `(來源: 財報公告)`")
            st.write(f"**毛利率:** {round(data['info'].get('grossMargins', 0)*100, 2)}% `(來源: 財報公告)`")
        with f2:
            st.write(f"**近四季 EPS:** {data['eps']} 元 `(來源: 財報累計)`")
            st.write(f"**現金殖利率:** {round(data['info'].get('dividendYield', 0)*100, 2)}% `(來源: 配息/股價)`")
        with f3:
            st.write(f"**負債比率:** {round(data['info'].get('debtToEquity', 0), 1)}% `(來源: 資產負債表)`")
            st.write(f"**營收年增率:** {round(data['info'].get('revenueGrowth', 0)*100, 2)}% `(來源: 營收月報)`")

        # 第三部分：技術指標
        st.markdown("---")
        st.write("### 📉 技術指標計算說明")
        t1, t2 = st.columns(2)
        df = data['df']
        df['MA20'] = df['Close'].rolling(20).mean()
        bias = (data['price'] / df['MA20'].iloc[-1] - 1) * 100
        
        with t1:
            st.write(f"**月線 (MA20):** {round(df['MA20'].iloc[-1], 1)} `(來源: 過去20日收盤均價)`")
        with t2:
            st.write(f"**月線乖離率:** {round(bias, 2)}% `(公式: (目前價 ÷ MA20) - 1)`")

        st.info("💡 **小撇步：** 將滑鼠移到上方數據的 **問號圖示**，可以看詳細的換算過程喔！")
