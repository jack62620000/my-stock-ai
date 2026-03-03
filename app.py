import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="巴菲特台股戰情室", layout="wide")

# --- 1. 自動化名稱抓取 (從證交所/櫃買中心官網) ---
@st.cache_data(ttl=86400) # 一天只抓一次，節省效能
def get_all_stock_names():
    names_dict = {}
    try:
        # 抓取上市清單
        tw_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        df_tw = pd.read_html(tw_url)[0]
        
        # 抓取上櫃清單
        two_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        df_two = pd.read_html(two_url)[0]
        
        # 合併並整理數據
        full_df = pd.concat([df_tw, df_two])
        for item in full_df[0]:
            # 格式通常是 "2330　台積電" (中間是全型空白)
            if '　' in str(item):
                parts = str(item).split('　')
                if len(parts) >= 2:
                    names_dict[parts[0].strip()] = parts[1].strip()
        return names_dict
    except Exception as e:
        # 萬一網路抓取失敗的備案
        return {"2330": "台積電", "2317": "鴻海", "2357": "華碩", "3131": "弘塑"}

# 初始化名稱對照表
name_map = get_all_stock_names()

# --- 2. 核心數據抓取與計算 ---
def get_stock_metrics(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            # 使用 history 抓取，最穩定
            hist = ticker.history(period="150d")
            if hist.empty: continue
            
            info = ticker.info
            price = hist['Close'].iloc[-1]
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            
            # 產業 PE 基準判斷
            ind = info.get('industry', '')
            pe_bench = 25 if any(k in ind for k in ["Semiconductors", "Computer"]) else 15
            intrinsic = eps * pe_bench
            safety_margin = (intrinsic / price) - 1 if price > 0 else 0
            
            # 52週位階
            low_52 = hist['Low'].min()
            high_52 = hist['High'].max()
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0.5

            return {
                "price": price, "roe": roe, "eps": eps, 
                "intrinsic": intrinsic, "safety": safety_margin, 
                "pos_52": pos_52, "info": info, "df": hist
            }
        except: continue
    return None

# --- 3. UI 介面 ---
st.sidebar.header("📊 投資控制台")
code_input = st.sidebar.text_input("輸入台股代碼", placeholder="例如: 2317").strip()

if code_input:
    with st.spinner('從證交所同步名稱中...'):
        data = get_stock_metrics(code_input)
        
        if data:
            # 這裡就是關鍵！直接從網上抓到的對照表找名稱
            stock_name = name_map.get(code_input, f"個股 {code_input}")
            st.title(f"📈 {stock_name} ({code_input}) 戰情報告")
            
            # 排版：基本面
            st.subheader("🛡️ 獲利品質與核心估值")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("目前股價", f"{round(data['price'], 1)} 元")
            c2.metric("實證合理價", f"{round(data['intrinsic'], 1)} 元")
            c3.metric("安全邊際", f"{round(data['safety']*100, 1)}%")
            c4.metric("52週位階", f"{round(data['pos_52']*100, 1)}%")
            
            # 財務指標區 (對齊妳的台股分析表)
            st.markdown("---")
            f1, f2, f3 = st.columns(3)
            with f1:
                st.write(f"**ROE:** {round(data['roe']*100, 2)}%")
                st.write(f"**毛利率:** {round(data['info'].get('grossMargins', 0)*100, 2)}%")
            with f2:
                st.write(f"**EPS:** {data['eps']}")
                st.write(f"**現金殖利率:** {round(data['info'].get('dividendYield', 0)*100, 2)}%")
            with f3:
                st.write(f"**負債比率:** {round(data['info'].get('debtToEquity', 0), 1)}%")
                st.write(f"**營收成長:** {round(data['info'].get('revenueGrowth', 0)*100, 2)}%")

            # T欄決策洞察
            st.divider()
            if data['roe'] > 0.15 and data['safety'] > 0.1:
                st.success(f"🤖 **AI 全方位決策：** {stock_name} 屬於【優質低估】標的，具備長線保護短線優勢。")
            elif data['pos_52'] > 0.8:
                st.warning(f"🤖 **AI 全方位決策：** {stock_name} 股價處於高位階，建議不加新倉。")
            else:
                st.info(f"🤖 **AI 全方位決策：** {stock_name} 目前各項指標中性，建議分批觀察。")
        else:
            st.error("❌ 找不到數據，請確認代碼是否正確（例如 2330 或 3131）。")
else:
    st.info("👈 請在左側輸入台股代碼開始分析")
