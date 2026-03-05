import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import numpy as np

# ========= 🎨 統一文字大小 =========
st.markdown("""
<style>
/* 標題 */
h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
h2, h3 { font-size: 1.6rem !important; margin: 0.3rem 0 0.5rem 0 !important; }

/* 容器內文字統一 */
.metric-container { 
    font-size: 1.0rem !important; 
    margin-bottom: 0.3rem !important; 
}
.metric-value { 
    font-size: 1.4rem !important; 
}
.metric-label { 
    font-size: 0.85rem !important; 
}

/* 一般文字統一 */
div[data-testid="column"] p, div[data-testid="column"] div {
    font-size: 0.95rem !important;
    line-height: 1.3 !important;
}

/* 解決 st.write 大小 */
.element-container p {
    font-size: 0.95rem !important;
    margin: 0.2rem 0 !important;
}
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="台股深度分析", layout="wide")

# --- 1. 股票名稱抓取 ---
@st.cache_data(ttl=86400)
def get_all_names():
    names = {"2330": "台積電", "3131": "弘塑", "2317": "鴻海"}
    try:
        for url in ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if '　' in str(item):
                    p = str(item).split('　')
                    if len(p) >= 2: 
                        names[p[0].strip()] = p[1].strip()
    except Exception: 
        pass
    return names

name_map = get_all_names()

st.sidebar.markdown("### 📈 **台股深度分析**")
st.sidebar.markdown("---")

# --- 2. 核心資料與指標計算 ---
@st.cache_data(ttl=300)
@st.cache_data(ttl=86400)
def get_deep_analysis_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty: 
                continue
            info = ticker.info
            price = hist["Close"].iloc[-1]

            # 基本面指標（info 可用欄位）
            eps = info.get("trailingEps", np.nan)
            pb = info.get("priceToBook", np.nan)
            pe = info.get("trailingPE", np.nan)
            div_yield = info.get("dividendYield", np.nan)
            rev_growth = info.get("revenueGrowth", np.nan)
            eps_growth = info.get("earningsGrowth", np.nan)

            gross_profit = info.get("grossMargins", 0)      # 毛利率
            net_margin = info.get("profitMargins", 0)       # 淨利率
            op_margin = info.get("operatingMargins", 0)     # 營業利益率
            roe = info.get("returnOnEquity", 0)
            roa = info.get("returnOnAssets", 0)
            debt_to_equity = info.get("debtToEquity", 0) / 100.0
            current_ratio = info.get("currentRatio", np.nan)
            quick_ratio = info.get("quickRatio", np.nan)
            payout_ratio = info.get("payoutRatio", 0)

            # 財務報表（收入、資產、負債、現金流）
            try:
                financials = ticker.financials
                income = financials.loc["Net Income"] if "Net Income" in financials.index else pd.Series([np.nan])
                revenue = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else pd.Series([np.nan])
                net_income = income.iloc[0] if not income.empty and not pd.isna(income.iloc[0]) else np.nan
                net_rev = revenue.iloc[0] if not revenue.empty and not pd.isna(revenue.iloc[0]) else np.nan

                # ----- 新增：毛利、營業利益成長率（年增） -----
                if "Gross Profit" in financials.index:
                    gp = financials.loc["Gross Profit"]
                    if len(gp) >= 2:
                        gross_profit_growth = (gp.iloc[0] - gp.iloc[1]) / gp.iloc[1]
                    else:
                        gross_profit_growth = np.nan
                else:
                    gross_profit_growth = np.nan

                if "Operating Income" in financials.index:
                    oi = financials.loc["Operating Income"]
                    if len(oi) >= 2:
                        operating_income_growth = (oi.iloc[0] - oi.iloc[1]) / oi.iloc[1]
                    else:
                        operating_income_growth = np.nan
                else:
                    operating_income_growth = np.nan
            except Exception:
                net_income = np.nan
                net_rev = np.nan
                gross_profit_growth = np.nan
                operating_income_growth = np.nan

            try:
                balance_sheet = ticker.balance_sheet
                total_assets = balance_sheet.loc["Total Assets"].iloc[0] if "Total Assets" in balance_sheet.index else np.nan
                total_liabilities = balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[0] if "Total Liabilities Net Minority Interest" in balance_sheet.index else np.nan
                equity = balance_sheet.loc["Total Equity Gross Minority Interest"].iloc[0] if "Total Equity Gross Minority Interest" in balance_sheet.index else np.nan

                # 存貨、現金、非流動負債（用來算結構比）
                inventory = balance_sheet.loc["Total Inventory"].iloc[0] if "Total Inventory" in balance_sheet.index else np.nan
                cash = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0] if "Cash And Cash Equivalents" in balance_sheet.index else np.nan
                non_current_liabilities = balance_sheet.loc["Non-Current Liabilities"].iloc[0] if "Non-Current Liabilities" in balance_sheet.index else np.nan

                # ----- 新增：資產成長率、權益成長率、結構比 -----
                assets_growth = np.nan
                equity_growth = np.nan
                if "Total Assets" in balance_sheet.index:
                    assets = balance_sheet.loc["Total Assets"]
                    if len(assets) >= 2:
                        assets_growth = (assets.iloc[0] - assets.iloc[1]) / assets.iloc[1]

                if "Total Equity Gross Minority Interest" in balance_sheet.index:
                    eq = balance_sheet.loc["Total Equity Gross Minority Interest"]
                    if len(eq) >= 2:
                        equity_growth = (eq.iloc[0] - eq.iloc[1]) / eq.iloc[1]

                # 結構比：存貨、現金、非流動負債占資產或負債比
                inv_asset_ratio = inventory / total_assets if total_assets and not pd.isna(inventory) else np.nan
                cash_asset_ratio = cash / total_assets if total_assets and not pd.isna(cash) else np.nan
                ncd_liabilities_ratio = non_current_liabilities / total_liabilities if total_liabilities and not pd.isna(non_current_liabilities) else np.nan
            except Exception:
                total_assets = np.nan
                total_liabilities = np.nan
                equity = np.nan
                inventory = np.nan
                cash = np.nan
                non_current_liabilities = np.nan
                inv_asset_ratio = np.nan
                cash_asset_ratio = np.nan
                ncd_liabilities_ratio = np.nan
                assets_growth = np.nan
                equity_growth = np.nan

            try:
                cashflow = ticker.cashflow
                operating_cashflow = cashflow.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cashflow.index else np.nan
                capex = -cashflow.loc["Capital Expenditure"].iloc[0] if "Capital Expenditure" in cashflow.index else 0.0
                free_cashflow = operating_cashflow - capex

                capex_to_cashflow = capex / operating_cashflow if operating_cashflow else np.nan
            except Exception:
                operating_cashflow = np.nan
                capex = np.nan
                free_cashflow = np.nan
                capex_to_cashflow = np.nan

            # 基本面指標計算
            debt_ratio = total_liabilities / total_assets if total_assets else np.nan
            net_income_growth = eps_growth  # 用 earningsGrowth 代表盈餘成長率
            cashflow_profit_ratio = operating_cashflow / net_income if net_income else np.nan
            fcf_revenue_ratio = free_cashflow / net_rev if net_rev else np.nan
            fcf_price_ratio = free_cashflow / (price * 1e8) if price and free_cashflow else np.nan
            fcf_growth = eps_growth  # 用盈餘成長率近似 FCF 成長

            # ----- 新增：現金股利報酬率、帳面價值成長率（BVG） -----
            div_per_share = info.get("dividendRate", np.nan)
            cash_dividend_yield = div_per_share / price if price and div_per_share else np.nan
            book_value_growth = equity_growth  # 帳面價值成長率 = 權益成長率

            # 技術面指標（基於歷史股價）
            df = hist.copy()
            df["ma5"] = ta.sma(df["Close"], 5)
            df["ma20"] = ta.sma(df["Close"], 20)
            df["ma60"] = ta.sma(df["Close"], 60)
            df["偏差"] = (df["Close"] - df["ma20"]) / df["ma20"]
            df["rsi"] = ta.rsi(df["Close"], 14)

            # MACD 安全寫法
            try:
                macd_df = ta.macd(df["Close"])
                if isinstance(macd_df, pd.DataFrame) and not macd_df.empty:
                    df["macd"] = macd_df.iloc[:, 0]          # MACD line
                    df["macd_signal"] = macd_df.iloc[:, 1]   # Signal line
                else:
                    df["macd"] = np.nan
                    df["macd_signal"] = np.nan
            except Exception as e:
                df["macd"] = np.nan
                df["macd_signal"] = np.nan

            df["布林上"], df["布林中"], df["布林下"] = ta.bbands(df["Close"]).iloc[:, 0], ta.bbands(df["Close"]).iloc[:, 1], ta.bbands(df["Close"]).iloc[:, 2]
            df["52高"] = df["High"].max()
            df["52低"] = df["Low"].min()
            df["std"] = df["Close"].rolling(window=20).std()
            df["atr"] = ta.atr(df["High"], df["Low"], df["Close"], 14)

            latest = df.iloc[-1]
            rsi = latest.get("rsi", 50)
            ma5 = latest.get("ma5", price)
            ma20 = latest.get("ma20", price)
            ma60 = latest.get("ma60", price)
            bb_upper = latest.get("布林上", np.nan)
            bb_lower = latest.get("布林下", np.nan)
            bb_mid = latest.get("布林中", np.nan)
            bias = latest.get("偏差", 0) * 100
            atr = latest.get("atr", 0)

            return {
                "price": price,
                "name": name_map.get(code, code),
                "info": info,

                # 基本面
                "gross_profit": gross_profit,
                "net_margin": net_margin,
                "op_margin": op_margin,
                "eps": eps,
                "roe": roe,
                "roa": roa,
                "rev_growth": rev_growth,
                "eps_growth": eps_growth,
                "net_income_growth": net_income_growth,
                "debt_ratio": debt_ratio,
                "debt_to_equity": debt_to_equity,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,
                "operating_cashflow": operating_cashflow,
                "free_cashflow": free_cashflow,
                "cashflow_profit_ratio": cashflow_profit_ratio,
                "pe": pe,
                "pb": pb,
                "peg": info.get("pegRatio", np.nan),
                "dividend_yield": div_yield,
                "payout_ratio": payout_ratio,

                # 技術面
                "df": df,
                "rsi": rsi,
                "ma5": ma5,
                "ma20": ma20,
                "ma60": ma60,
                "bias": bias,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "bb_mid": bb_mid,
                "atr": atr,

                # 財務與資本結構
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "equity": equity,
                "capex": capex,
                "capex_to_cashflow": capex_to_cashflow,

                # 成長性（新增）
                "gross_profit_growth": gross_profit_growth,
                "operating_income_growth": operating_income_growth,
                "assets_growth": assets_growth,
                "equity_growth": equity_growth,

                # 財務結構（結構比）
                "inv_asset_ratio": inv_asset_ratio,
                "cash_asset_ratio": cash_asset_ratio,
                "ncd_liabilities_ratio": ncd_liabilities_ratio,

                # 現金流與股利（新增）
                "fcf_revenue_ratio": fcf_revenue_ratio,
                "fcf_price_ratio": fcf_price_ratio,
                "fcf_growth": fcf_growth,
                "cash_dividend_yield": cash_dividend_yield,
                "book_value_growth": book_value_growth,
            }
        except Exception as e:
            st.warning(f"代碼 {code}{suffix} 錯誤：{e}")
            continue
    return None


# --- 3. AI 會話（保留第三部分）---
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-2.5-flash")

        eps = d.get("eps", 0)
        pe = d.get("pe", 0)
        roe = d.get("roe", 0)
        rsi = d.get("rsi", 50)
        price = d.get("price", 0)

        prompt = f"""針對 {d['name']} ({code})：
        現價 {round(price, 1)} 元，EPS {round(eps, 2)}，本益比 {round(pe, 1)}，ROE {round(roe*100, 1)}%
        RSI {round(rsi, 1)}，技術面多空由 MA5 / MA20 / MA60 趨勢判斷。

        請依序回答：
        1. 🌍 全球與產業局勢影響
        2. 💎 公司護城河與基本面健康度
        3. 📉 基本面與技術面綜合判斷
        4. 🎯 合理價與目標價區間
        5. 📈 投資建議與風險提示"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 錯誤：{str(e)[:80]}"
# --- 4. UI 主畫面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip().upper()

if code_input:
    with st.spinner(f"🔄 分析 {code_input} 資料中..."):
        d = get_deep_analysis_data(code_input)

    if d:
        st.title(f"📊 {d.get('name', code_input)} ({code_input})")

        st.markdown(
    """
    <style>
    /* 縮小 subheader 與下方 metrics 的間距 */
    .stSubheader { 
        margin-bottom: 0.1rem;
    }
    /* 縮小 metric 之間的行距 */
    .stMetric, .stMetricLabel, .stMetricValue {
        margin: 0.1rem 0 0.1rem 0;
    }
    /* 整個基本面區塊整體不要太寬 */
    div[data-testid="stContainer"] {
        padding-top: 0.2rem;
        padding-bottom: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
        #  ========== 一、基本面（公司賺不賺錢）==========
        st.header("📌 一、基本面：公司賺不賺錢")
        with st.container(border=True):
            # 盈利能力
            st.subheader("盈利能力")
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            c1.metric("毛利率", f"{d.get('gross_profit', 0) * 100:.1f}%")
            c2.metric("淨利率", f"{d.get('net_margin', 0) * 100:.1f}%")
            c3.metric("營業利益率", f"{d.get('op_margin', 0) * 100:.1f}%")
            c4.metric("EPS", f"{d.get('eps', 0):.2f}")
            c5.metric("ROE", f"{d.get('roe', 0) * 100:.1f}%")
            c6.metric("ROA", f"{d.get('roa', 0) * 100:.1f}%")
            c7.metric("EPS 成長率", f"{d.get('eps_growth', 0) * 100:.1f}%")
                   
            # 成長性
            st.subheader("成長性")
            g1, g2, g3, g4, g5, g6, g7 = st.columns(7)
            g1.metric("營收成長率", f"{d.get('rev_growth', 0) * 100:.1f}%")
            g2.metric("EPS 成長率", f"{d.get('eps_growth', 0) * 100:.1f}%")
            g3.metric("淨利成長率", f"{d.get('net_income_growth', 0) * 100:.1f}%")
            g4.metric("毛利成長率", f"{d.get('gross_profit_growth', 0) * 100:.1f}%")
            g5.metric("營業利益成長率", f"{d.get('operating_income_growth', 0) * 100:.1f}%")
            g6.metric("資產成長率", f"{d.get('assets_growth', 0) * 100:.1f}%")
            g7.metric("權益成長率", f"{d.get('equity_growth', 0) * 100:.1f}%")

            # 財務結構
            st.subheader("財務結構")
            f1, f2, f3, f4, f5, f6, f7 = st.columns(7)
            f1.metric("負債比率", f"{d.get('debt_ratio', 0) * 100:.1f}%")
            f2.metric("負債／股東權益", f"{d.get('debt_to_equity', 0) * 100:.1f}%")
            f3.metric("流動比率", f"{d.get('current_ratio', 0):.2f}")
            f4.metric("速動比率", f"{d.get('quick_ratio', 0):.2f}")
            f5.metric("存貨佔資產比", f"{d.get('inv_asset_ratio', 0):.1%}")
            f6.metric("現金佔資產比", f"{d.get('cash_asset_ratio', 0):.1%}")
            f7.metric("非流動負債占負債比", f"{d.get('ncd_liabilities_ratio', 0):.1%}")

            # 現金流品質
            st.subheader("現金流品質")
            ca1, ca2, ca3, ca4, ca5, ca6, ca7 = st.columns(7)
            ca1.metric("營業現金流", f"{d.get('operating_cashflow', 0) / 1e8:.1f}億")
            ca2.metric("自由現金流 (FCF)", f"{d.get('free_cashflow', 0) / 1e8:.1f}億")
            ca3.metric("現金流／淨利", f"{d.get('cashflow_profit_ratio', 0):.2f}")
            ca4.metric("FCF／營收", f"{d.get('fcf_revenue_ratio', 0):.1%}")
            ca5.metric("FCF／股價", f"{d.get('fcf_price_ratio', 0):.1%}")
            ca6.metric("FCF 成長率", f"{d.get('fcf_growth', 0) * 100:.1f}%")
            ca7.metric("資本支出／營業現金流", f"{d.get('capex_to_cashflow', 0):.2f}")

            # 估值水準
            st.subheader("估值水準")
            v1, v2, v3, v4, v5, v6, v7 = st.columns(7)
            v1.metric("本益比 (P/E)", f"{d.get('pe', 0):.1f}x")
            v2.metric("股價淨值比 (P/B)", f"{d.get('pb', 0):.1f}x")
            v3.metric("PEG", f"{d.get('peg', 0):.1f}")
            v4.metric("股利殖利率", f"{d.get('dividend_yield', 0) * 100:.1f}%")
            v5.metric("盈餘配發率", f"{d.get('payout_ratio', 0) * 100:.1f}%")
            v6.metric("現金股利報酬率", f"{d.get('cash_dividend_yield', 0) * 100:.1f}%")
            v7.metric("帳面價值成長率", f"{d.get('book_value_growth', 0) * 100:.1f}%")
            

        #  ========== 二、技術面（趨勢、動能、波動、量價）==========
        st.header("📉 二、技術面：股價趨勢與強度")
        df = d.get("df", pd.DataFrame())
        if not df.empty:
            latest = df.iloc[-1]
            price = d.get("price", 0)

            with st.container(border=True):
                t1, t2, t3, t4 = st.columns(4)

                # 趨勢與均線
                t1.subheader("趨勢與均線")
                t1.write(f"MA5: {latest.get('ma5', price):.1f}")
                t1.write(f"MA20: {latest.get('ma20', price):.1f}")
                t1.write(f"MA60: {latest.get('ma60', price):.1f}")
                t1.write(f"乖離率: {d.get('bias', 0):.1f}%")

                # 動能與強度
                t2.subheader("動能與強度")
                t2.write(f"RSI: {d.get('rsi', 50):.1f}")
                macd_line = df["macd"].iloc[-1] if "macd" in df.columns else 0.0
                macd_line = df["macd"].iloc[-1] if "macd" in df.columns else 0.0
                macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else 0.0

                t2.write(f"MACD 本體: {macd_line:+.2f}")
                t2.write(f"MACD 信號線: {macd_signal:+.2f}")

                # 波動與區間
                t3.subheader("波動與區間")
                t3.write(f"布林上: {d.get('bb_upper', 0):.1f}")
                t3.write(f"布林中: {d.get('bb_mid', 0):.1f}")
                t3.write(f"布林下: {d.get('bb_lower', 0):.1f}")
                t3.write(f"52週高價: {d.get('52高', 0):.1f}")
                t3.write(f"52週低價: {d.get('52低', 0):.1f}")
                t3.write(f"標準差 (20日): {df['std'].iloc[-1]:.2f}")
                t3.write(f"ATR (14日): {d.get('atr', 0):.2f}")

                # 成交量與量價關係
                t4.subheader("成交量與量價關係")
                t4.write(f"今日成交量: {int(latest['Volume'] / 1000):,} 張")

                if len(df) >= 2:
                    prev = df.iloc[-2]
                    if latest['Close'] > prev['Close'] and latest['Volume'] > prev['Volume']:
                        volume_msg = "價漲量增"
                    else:
                        volume_msg = "價漲量縮"
                else:
                    volume_msg = "價量資訊不足"

                t4.write(f"量價：{volume_msg}")

                # 可選：OBV / MFI（若你有實作，可加 Metrics）


        #  ========== 三、財務與資本結構（公司資本是否健康）==========
        st.header("🏦 三、財務與資本結構：公司資本是否健康")
        with st.container(border=True):
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("總資產", f"{d.get('total_assets', 0) / 1e9:.1f} 億")
            s2.metric("總負債", f"{d.get('total_liabilities', 0) / 1e9:.1f} 億")
            s3.metric("股東權益", f"{d.get('equity', 0) / 1e9:.1f} 億")

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("資本支出 (Capex)", f"{d.get('capex', 0) / 1e8:.1f} 億")
            r2.metric("資本支出／營業現金流", f"{d.get('capex_to_cashflow', 0):.2f}")


        #  ========== 四、現金流與股利（現金能不能穩定入袋）==========
        st.header("💵 四、現金流與股利：現金能不能穩定入袋")
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("自由現金流／營收", f"{d.get('fcf_revenue_ratio', 0):.1%}")
            f2.metric("自由現金流／股價", f"{d.get('fcf_price_ratio', 0):.1%}")
            f3.metric("FCF 成長率", f"{d.get('fcf_growth', 0) * 100:.1f}%")
            f4.metric("盈餘配發率", f"{d.get('payout_ratio', 0) * 100:.1f}%")

            st.write("說明：")
            st.write("• 若「自由現金流／股價」為正，表示每單位股價背後有實質現金支撐。")
            st.write("• 若「盈餘配發率」接近 100%，代表公司多數盈餘用於配股，現金流留存較少。")


        #  ========== 五、AI診斷（保留你的第三部分）==========
        st.markdown("---")
        st.header("🤖 五、AI診斷")

        api_status = st.secrets.get("GEMINI_API_KEY", "")
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
                    st.success("✅ AI 診斷完成！")
            else:
                st.error("🔧 請先在 Streamlit Cloud 設定 Secrets：App Settings → Secrets → GEMINI_API_KEY")
    else:
        st.error("❌ 請確認輸入正確的股票代碼（例如 2330、2317）")
















