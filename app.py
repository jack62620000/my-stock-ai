import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# 頁面基本設定
st.set_page_config(page_title="台股五星級 AI 戰情室", layout="wide")

# --- 1. 自動名稱抓取 (證交所官網) ---
@st.cache_data(ttl=86400)
def get_stock_names_map():
    names = {}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
                    "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    parts = str(item).split('　')
                    if len(parts) >= 2: names[parts[0].strip()] = parts[1].strip()
        return names
    except:
        return {"2330": "台積電", "2317": "鴻海"}

name_map = get_stock_names_map()

# --- 2. 核心數據抓取與計算 (對齊試算表所有公式) ---
def fetch_full_analysis(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="250d") # 抓一年的數據計算 52 週與均線
            if hist.empty: continue
            
            info = ticker.info
            # 基本資訊
            price = hist['Close'].iloc[-1]
            eps = info.get('trailingEps', 0) or 0
            
            # 獲利品質邏輯 (B-F 欄)
            roe = info.get('returnOnEquity', 0)
            gp_m = info.get('grossMargins', 0)
            op_m = info.get('operatingMargins', 0)
            debt_e = info.get('debtToEquity', 0) / 100 # 轉換為 %
            
            # 估值邏輯 (G-L 欄)
            m_pe = info.get('trailingPE', 0)
            ind = str(info.get('industry', ''))
            # 基準 PE 邏輯
            if any(k in ind for k in ["Semiconductor", "Computer"]): b_pe = 22.5 
            elif "Financial" in ind: b_pe = 14
            else: b_pe = 12
            
            intrinsic = eps * b_pe
            low_52, high_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0
            
            # 進階風險 (M-Q 欄)
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            quick_r = info.get('quickRatio', 0)
            curr_r = info.get('currentRatio', 0)
            div_y = info.get('dividendYield', 0)
            rev_g = info.get('revenueGrowth', 0)
            
            # 技術指標 (走勢分析表)
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            kd = ta.stoch(df['High'], df['Low'], df['Close'])
            macd = ta.macd(df['Close'])
            
            # 布林通道
            bol = ta.bbands(df['Close'], length=20, std=2)
            
            return {
                "price": price, "roe": roe, "gp": gp_m, "op": op_m, "debt": debt_e,
                "m_pe": m_pe, "b_pe": b_pe, "eps": eps, "intrinsic": intrinsic, "pos_52": pos_52,
                "fcf": fcf, "quick": quick_r, "curr": curr_r, "div": div_y, "rev": rev_g,
                "df": df, "kd": kd, "macd": macd, "bol": bol, "industry": ind
            }
        except: continue
    return None

# --- 3. UI 渲染 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼 (例: 3131, 2330)", "").strip()

if code_input:
    d = fetch_full_analysis(code_input)
    if d:
        name = name_map.get(code_input, "未知個股")
        st.title(f"📊 {name} ({code_input}) 投資與走勢全診斷")
        
        # --- 第一部分：台股分析 (B-T 欄) ---
        st.header("📌 台股基本面分析 (第 1-4 列指標)")
        
        with st.container(border=True):
            # 第一排：獲利品質
            t1, t2, t3, t4, t5 = st.columns(5)
            t1.metric("ROE (賺錢效率)", f"{round(d['roe']*100, 2)}%", "卓越" if d['roe']>0.15 else "警戒")
            t2.metric("毛利率 (競爭力)", f"{round(d['gp']*100, 1)}%")
            t3.metric("營業利益率", f"{round(d['op']*100, 1)}%")
            t4.metric("負債比 (財務壓力)", f"{round(d['debt']*100, 1)}%", delta_color="inverse")
            t5.metric("自由現金流", f"{round(d['fcf'],1)} 億")

            # 第二排：估值與位階
            t6, t7, t8, t9, t10 = st.columns(5)
            t6.metric("市場 P/E", f"{round(d['m_pe'],1)} 倍")
            t7.metric("基準 P/E", f"{d['b_pe']} 倍")
            t8.metric("實證合理價", f"{round(d['intrinsic'],1)} 元")
            safety = (d['intrinsic']/d['price'])-1
            t9.metric("安全邊際", f"{round(safety*100, 1)}%", f"{'具補漲空間' if safety > 0.1 else '溢價'}")
            t10.metric("52週位階", f"{round(d['pos_52']*100, 1)}%", "過熱" if d['pos_52']>0.75 else "低位階")

            # 第三排：財務過濾
            t11, t12, t13, t14, t15 = st.columns(5)
            t11.metric("速動比率", f"{round(d['quick']*100,1)}%")
            t12.metric("流動比率", f"{round(d['curr']*100,1)}%")
            t13.metric("現金殖利率", f"{round(d['div']*100,2)}%")
            t14.metric("營收年增率", f"{round(d['rev']*100,1)}%")
            t15.metric("近四季 EPS", f"{d['eps']} 元")

        # AI 診斷 (T 欄)
        if d['roe'] > 0.18 and d['pos_52'] < 0.35: decision, color = "🌟 卓越成長：高獲利、低位階標的", "success"
        elif safety > 0.1: decision, color = "🟢 安全邊際：價值低估，適合佈局", "success"
        elif d['pos_52'] > 0.8: decision, color = "🟠 高度警戒：位階過高，暫不加倉", "warning"
        elif d['roe'] < 0.08: decision, color = "🚫 暫不考慮：獲利品質未達標", "error"
        else: decision, color = "⏳ 中性觀望：各項數據處於盤整區", "info"
        
        st.toast(decision)
        getattr(st, color)(f"**🤖 AI 全方位決策洞察：** {decision}")

        st.divider()

        # --- 第二部分：股價走勢分析 ---
        st.header("📉 股價走勢分析 (均線、量能、籌碼)")
        
        with st.container(border=True):
            g1, g2, g3, g4 = st.columns(4)
            # 均線區
            with g1:
                st.write("**【 均線與乖離 】**")
                st.write(f"MA5 (週線): {round(d['df']['MA5'].iloc[-1],1)}")
                st.write(f"MA20 (月線): {round(d['df']['MA20'].iloc[-1],1)}")
                st.write(f"MA60 (季線): {round(d['df']['MA60'].iloc[-1],1)}")
                bias = (d['price'] - d['df']['MA20'].iloc[-1]) / d['df']['MA20'].iloc[-1]
                st.write(f"乖離率: {round(bias*100, 1)}% ({'過熱' if bias>0.1 else '超跌' if bias<-0.1 else '正常'})")

            # 量能指標
            with g2:
                st.write("**【 量能與強弱 】**")
                vol = d['df']['Volume'].iloc[-1]
                avg_vol = d['df']['Volume'].tail(5).mean()
                st.write(f"今日成交量: {int(vol/1000)} 張")
                st.write(f"5日均量: {int(avg_vol/1000)} 張")
                st.write(f"量能噴發比: {round(vol/avg_vol, 2)}x")
            
            # 動能指標
            with g3:
                st.write("**【 動能與指標 】**")
                rsi = d['df']['RSI'].iloc[-1]
                st.write(f"RSI(14): {round(rsi, 1)} ({'過熱' if rsi>70 else '超賣' if rsi<30 else '持平'})")
                k = d['kd']['STOCHk_9_3_3'].iloc[-1]
                d_val = d['kd']['STOCHd_9_3_3'].iloc[-1]
                st.write(f"KD值: K {round(k,1)} / D {round(d_val,1)}")
                st.write(f"KD狀態: {'多頭交叉' if k>d_val else '空頭交叉'}")

            # 籌碼區與布林
            with g4:
                st.write("**【 籌碼與區間 】**")
                st.write(f"布林上軌: {round(d['bol']['BBU_20_2.0'].iloc[-1], 1)}")
                st.write(f"布林下軌: {round(d['bol']['BBL_20_2.0'].iloc[-1], 1)}")
                st.write(f"走勢評等: {'🌕 強勢' if d['price'] > d['df']['MA20'].iloc[-1] else '🌑 弱勢'}")

        # 技術診斷建議
        st.subheader("💡 技術診斷與策略建議")
        macd_val = d['macd']['MACD_12_26_9'].iloc[-1]
        sig_val = d['macd']['MACDs_12_26_9'].iloc[-1]
        
        tech_advice = f"目前的 RSI 為 {round(rsi,1)}，"
        if macd_val > sig_val: tech_advice += "MACD 柱狀體翻紅，趨勢偏多。"
        else: tech_advice += "MACD 仍處於弱勢區間。"
        
        if bias > 0.08: tech_advice += " 乖離率過大，不建議在此時追高。"
        elif rsi < 35: tech_advice += " 已進入超賣區，可觀察止跌訊號。"
        
        st.success(tech_advice)

    else:
        st.error("無法抓取數據，請確認代碼是否正確。")
