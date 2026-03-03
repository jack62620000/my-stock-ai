import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 頁面配置
st.set_page_config(page_title="台股 AI 終極戰情室", layout="wide")

# --- 1. 名稱抓取 (省略重複代碼，保持原本邏輯) ---
@st.cache_data(ttl=86400)
def get_all_names():
    # ... (維持原本爬蟲邏輯) ...
    return {"2330": "台積電", "3131": "弘塑"}

name_map = get_all_names()

# --- 2. 核心數據抓取與全面計算 ---
def get_comprehensive_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: continue
            info = ticker.info
            price = hist['Close'].iloc[-1]
            
            # --- [台股分析數據] ---
            eps = info.get('trailingEps', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            gp_m = info.get('grossMargins', 0) or 0
            debt_e = (info.get('debtToEquity', 0) or 0) / 100
            rev_g = (info.get('revenueGrowth', 0) or 0)
            ind = info.get('industry', '')
            pe_b = 22.5 if "Semiconductor" in ind else 14 if "Financial" in ind else 12
            intrinsic = eps * pe_b
            safety = (intrinsic / price) - 1 if price > 0 else 0
            l_52, h_52 = hist['Low'].min(), hist['High'].max()
            pos_52 = (price - l_52) / (h_52 - l_52) if h_52 > l_52 else 0
            
            # --- [股價走勢數據] ---
            df = hist.copy()
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
            
            return {
                "p": price, "roe": roe, "eps": eps, "gp": gp_m, "debt": debt_e,
                "rev": rev_g, "pe_b": pe_b, "intrinsic": intrinsic, "safety": safety, "pos_52": pos_52,
                "df": df, "stoch": stoch, "name": name_map.get(code, code)
            }
        except: continue
    return None

# --- 3. UI 介面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="3131").strip()

if code_input:
    d = get_comprehensive_data(code_input)
    if d:
        st.title(f"📊 {d['name']} ({code_input}) 投資全方位報告")

        # --- 第一部分與第二部分維持原本的表格數據 ---
        # (此處省略中間顯示程式碼，請保留妳原本的顯示區塊)

        # --- 第三部分：AI 全方位決策分析 (還原試算表邏輯) ---
        st.divider()
        st.header("🤖 AI 全方位決策分析 (T欄邏輯實作)")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("### 💎 價值指標檢查")
                st.write(f"1. **ROE 狀態:** {round(d['roe']*100,1)}% ({'符合 > 15%' if d['roe'] > 0.15 else '未達標'})")
                st.write(f"2. **安全邊際:** {round(d['safety']*100,1)}% ({'空間充足' if d['safety'] > 0.1 else '空間較小'})")
                st.write(f"3. **52週位階:** {round(d['pos_52']*100,1)}% ({'低檔安全' if d['pos_52'] < 0.4 else '位階偏高'})")
                
                # 技術面連動判斷
                k, dv = d['stoch'].iloc[-1, 0], d['stoch'].iloc[-1, 1]
                st.write(f"4. **KD 動能:** {'多頭金叉' if k > dv else '空頭死叉'}")

            with col2:
                st.write("### 📝 AI 深度診斷報告")
                
                # 最終邏輯判斷 (對齊試算表 T 欄)
                if d['roe'] > 0.15 and d['safety'] > 0.1 and d['pos_52'] < 0.5:
                    st.success(f"✅ **【強烈建議：價值與成長兼具】**\n\n{d['name']} 目前 ROE 表現優異，且股價處於實證合理價下方。安全邊際高達 {round(d['safety']*100,1)}%，且位階中低，適合價值投資者進行佈局。")
                
                elif d['pos_52'] > 0.8:
                    st.error(f"🚨 **【警示：股價已處於高位階】**\n\n目前 52 週位階已達 {round(d['pos_52']*100,1)}%，雖然基本面良好，但短期追高風險極大。建議等待乖離率修正，或回到合理價區間再行考慮。")
                
                elif d['roe'] < 0.1:
                    st.warning(f"⚠️ **【注意：獲利品質轉弱】**\n\n該股 ROE 僅 {round(d['roe']*100,1)}%，未達巴菲特 15% 的選股標準。建議觀察其營收年增率是否能在下一季回升，目前應持保守態度。")
                
                else:
                    st.info(f"⏳ **【中性判斷：靜待訊號趨於一致】**\n\n目前各項指標互有勝負。雖然股價可能合理，但技術指標（如 KD）尚未出現明確攻擊訊號。建議將其加入追蹤清單，分批觀察量能變化。")

                # 綜合策略
                st.markdown("---")
                st.write(f"**💡 綜合執行策略：** " + 
                         ("建議分批進場" if d['safety'] > 0.05 and d['pos_52'] < 0.6 else "暫緩加碼，觀望回檔"))

    else:
        st.error("❌ 無法取得數據。")
