import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai

# ========= 🎨 完美樣式：緊湊版+統一字體 =========
st.markdown("""
<style>
/* 標題統一大小 */
h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
h2, h3 { font-size: 1.6rem !important; margin-top: 0.3rem !important; margin-bottom: 0.5rem !important; }

/* 緊湊容器間距 */
.st-emotion-cache-1r4fnda { padding: 0.5rem 1rem !important; margin-bottom: 0.3rem !important; }

/* Metric優化 */
.metric-container { margin-bottom: 0.2rem !important; }
.metric-value { font-size: 1.3rem !important; }

/* 側邊欄美化 */
.sidebar .stTextInput > div > div > input { font-size: 1rem !important; }

/* 按鈕滿寬 */
.stButton > button { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# 頁面配置
st.set_page_config(page_title="台股分析", layout="wide")

# --- 1. 名稱抓取 ---
@st.cache_data(ttl=86400)
def get_all_names():
    names = {"2330": "台積電", "3131": "弘塑", "2317": "鴻海"}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    p = str(item).split('　')
                    if len(p) >= 2: names[p[0].strip()] = p[1].strip()
    except Exception as e:
        st.warning(f"名稱更新失敗：{str(e)}")
    return names

name_map = get_all_names()

# 側邊欄美化
st.sidebar.markdown("### 📈 **台股AI診斷系統**")
st.sidebar.markdown("---")

# --- 2. 核心數據抓取與計算 ---
@st.cache_data(ttl=300)  # 5分鐘更新
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            op_m = info.get('operatingMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            fcf = (info.get('freeCashflow', 0) or 0) / 100000000
            div_y = info.get('dividendYield', 0) or 0
            rev_g = info.get('revenueGrowth', 0) or 0
            
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 15
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            df = hist.copy()
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA60'] = ta.sma(df['Close'], length=60)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            macd = ta.macd(df['Close'])
            bol = ta.bbands(df['Close'], length=20, std=2)
            
            return {
                "p": price, "roe": roe, "eps": eps, "gp": gp_m, "op": op_m, "debt": debt_e,
                "fcf": fcf, "div": div_y, "rev": rev_g, "pe_b": pe_b, 
                "intrinsic": intrinsic, "target_mean": intrinsic,
                "safety": safety, "pos_52": pos_52, "df": df, "stoch": stoch, "macd": macd, 
                "bol": bol, "name": name_map.get(code, code), "industry": ind
            }
        except Exception as e:
            st.warning(f"⚠️ {code}{suffix} 抓取失敗：{str(e)[:50]}")
            continue
    return None

# --- 3. AI 診斷報告函式 ---
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        lt = d['df'].iloc[-1]
        k_val = d['stoch'].iloc[-1, 0]
        d_val = d['stoch'].iloc[-1, 1]
        
        prompt = f"""你現在是融合「巴菲特價值眼光」與「高盛首席策略分析師」的頂尖 AI 顧問。
請針對股票：{d['name']} ({code}) 進行精確且多方面的專業分析報告。

【⚠️ 執行指令】：請直接從第 1 點開始輸出報告，嚴禁任何開場白。

【當前關鍵數據】
- 財務：現價 {round(d['p'], 1)}元, ROE {round(d['roe']*100, 2)}%, 毛利 {round(d['gp']*100, 2)}%
- 技術：K值 {round(k_val, 1)}, D值 {round(d_val, 1)}, RSI {round(lt['RSI'], 1)}
- 預估：合理價 {round(d['intrinsic'], 1)}元 (安全邊際 {round(d['safety']*100, 1)}%)

請嚴格依照以下5點結構：

1. 🌍【全球局勢與宏觀風險分析】
2. 💎【巴菲特的內在價值審查】
3. 📉【股價走勢與動能判斷】
4. 🎯【法人目標價與達成時間預估】
5. 📈【終極投資策略建議】"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI連線錯誤：{str(e)[:80]}\n\n🔧 請確認Cloud Secrets中的GEMINI_API_KEY"

# --- 4. UI 介面（緊湊優化版）---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 全方位診斷")
        
        # 第一部分：緊湊版
        st.header("📋 第一部分：基本面、估值與財務過濾")
        with st.container(border=True):
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("目前價格", f"{round(d['p'], 1)} 元")
            v2.metric("實證合理價", f"{round(d['intrinsic'], 1)} 元", f"PE: {d['pe_b']}")
            v3.metric("安全邊際", f"{round(d['safety']*100, 1)}%", "🟢低估" if d['safety']>0.1 else "🔴溢價")
            v4.metric("52週位階", f"{round(d['pos_52']*100, 1)}%", "🔥過熱" if d['pos_52']>0.75 else "🟢低檔")
            
            # ✅ 緊湊財務區（無大間距）
            st.markdown(" ")
            f1, f2, f3, f4 = st.columns(4)
            with f1: st.metric("ROE", f"{round(d['roe']*100,1)}%", text_color="green" if d['roe']>0.15 else "red")
            with f2: st.metric("現金流", f"{round(d['fcf'],1)}億", text_color="green" if d['fcf']>0 else "red")
            with f3: st.metric("營收年增", f"{round(d['rev']*100,1)}%")
            with f4:
                if d['roe'] > 0.18 and d['pos_52'] < 0.35: st.success("🌟 卓越成長")
                elif d['safety'] > 0.1: st.success("🟢 價值低估")
                else: st.info("⏳ 持有觀望")
        
        # ✅ 第二部分：零間距銜接
        st.markdown(" ")
        st.header("📉 第二部分：股價走勢與動能分析")
        df, latest = d['df'], d['df'].iloc[-1]
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                st.write("**均線**")
                st.write(f"MA20: {round(latest['MA20'], 1)}")
                bias = (d['p'] / latest['MA20'] - 1) * 100
                st.write(f"乖離: {round(bias, 1)}%")
            with t2:
                st.write("**量能**")
                st.write(f"成交: {int(latest['Volume']/1000)}張")
                st.write(f"RSI: {round(latest['RSI'], 1)}")
            with t3:
                k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
                st.write("**KD**")
                st.write(f"K{round(k,1)}/D{round(dv,1)}")
                st.write(f"{'🔥金叉' if k>dv else '❄️死叉'}")
            with t4:
                st.write("**趨勢**")
                st.write(f"{'🌕強勢' if d['p'] > latest['MA20'] else '🌑弱勢'}")
                st.write(f"{'持股' if d['p'] > latest['MA20'] else '等待'}")
        
        # ✅ 第三部分：完美AI按鈕
        st.markdown(" ")
        st.header("🤖 第三部分：AI 終極戰情診斷")
        
        api_status = st.secrets.get("GEMINI_API_KEY")
        col1, col2 = st.columns([1, 4])
        with col1:
            status_icon = "🟢 已連線" if api_status else "🔴 未連線"
            st.caption(f"**{status_icon}**")
        with col2:
            st.caption(f"**Gemini 2.5 Flash**")
        
        if st.button("🚀 啟動 AI 深度診斷", type="primary", use_container_width=True):
            if api_status:
                with st.spinner(f"🤖 AI 分析 {d['name']}..."):
                    report = get_ai_analysis_report(d, code_input, api_status)
                    st.markdown("### 📋 **AI 終極投資報告**")
                    st.markdown("---")
                    st.markdown(report)
                    st.balloons()
                    st.success("✅ AI診斷完成！")
            else:
                st.error("🔧 App Settings → Secrets → 設定 GEMINI_API_KEY")
    else:
        st.error("❌ 無數據，請確認代碼（如2330）")
