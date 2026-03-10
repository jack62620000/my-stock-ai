import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import numpy as np
import time

# ========= 頁面設定（必須放最前面） =========
st.set_page_config(page_title="台股深度分析", layout="wide")

# --- 1. 股票名稱抓取（加入市場別 suffix） ---
@st.cache_data(ttl=86400)
def get_all_names():
    names = {
        "2330": {"name": "台積電", "suffix": ".TW"},
        "3131": {"name": "弘塑", "suffix": ".TWO"},
        "2317": {"name": "鴻海", "suffix": ".TW"},
    }

    try:
        source_map = [
            ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", ".TW"),   # 上市
            ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", ".TWO"),  # 上櫃
        ]

        for url, suffix in source_map:
            df = pd.read_html(url)[0]
            for item in df[0]:
                text = str(item)
                if "　" in text:
                    p = text.split("　")
                    if len(p) >= 2:
                        code = p[0].strip()
                        name = p[1].strip()
                        if code.isdigit():
                            names[code] = {"name": name, "suffix": suffix}
    except Exception:
        pass

    return names


name_map = get_all_names()

st.sidebar.markdown("### 📈 **台股深度分析**")
st.sidebar.markdown("---")

# --- 2. 安全呼叫 Yahoo Finance（避免 429 限流直接炸掉） ---
def safe_yf_call(func, retries=3, base_sleep=2):
    last_err = None
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "too many requests" in msg or "rate limited" in msg or "429" in msg:
                time.sleep(base_sleep * (2 ** i))  # 2, 4, 8 秒退避
                continue
            raise
    raise last_err


# --- 3. 核心資料與指標計算 ---
@st.cache_data(ttl=21600)  # 6小時，減少重複打 API
def get_deep_analysis_data(code):
    stock_meta = name_map.get(code, {"name": code, "suffix": None})
    suffixes = [stock_meta["suffix"]] if stock_meta.get("suffix") else [".TW", ".TWO"]

    last_error = None

    for suffix in suffixes:
        if not suffix:
            continue

        try:
            ticker = yf.Ticker(f"{code}{suffix}")

            hist = safe_yf_call(lambda: ticker.history(period="1y", auto_adjust=False))
            if hist.empty:
                continue

            price = hist["Close"].iloc[-1]

            # 優先抓較輕量資料
            try:
                _ = safe_yf_call(lambda: ticker.fast_info)
            except Exception:
                pass

            # info 很容易被限流，所以抓不到就給空 dict，不中斷
            try:
                info = safe_yf_call(lambda: ticker.info) or {}
            except Exception:
                info = {}

            # 基本面指標（info 可用欄位）
            eps = info.get("trailingEps", np.nan)
            pb = info.get("priceToBook", np.nan)
            pe = info.get("trailingPE", np.nan)
            div_yield = info.get("dividendYield", np.nan)
            rev_growth = info.get("revenueGrowth", np.nan)
            eps_growth = info.get("earningsGrowth", np.nan)
            gross_profit = info.get("grossMargins", 0)
            net_margin = info.get("profitMargins", 0)
            op_margin = info.get("operatingMargins", 0)
            roe = info.get("returnOnEquity", 0)
            roa = info.get("returnOnAssets", 0)

            dte_raw = info.get("debtToEquity", np.nan)
            debt_to_equity = dte_raw / 100.0 if pd.notna(dte_raw) else np.nan

            current_ratio = info.get("currentRatio", np.nan)
            quick_ratio = info.get("quickRatio", np.nan)
            payout_ratio = info.get("payoutRatio", 0)
            peg_ratio = info.get("pegRatio", np.nan)
            div_per_share = info.get("dividendRate", np.nan)

            # 財務報表（收入、資產、負債、現金流）
            try:
                financials = safe_yf_call(lambda: ticker.financials)
                if financials is None or not isinstance(financials, pd.DataFrame):
                    financials = pd.DataFrame()
                income = financials.loc["Net Income"] if "Net Income" in financials.index else pd.Series([np.nan])
                revenue = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else pd.Series([np.nan])

                net_income = income.iloc[0] if not income.empty and not pd.isna(income.iloc[0]) else np.nan
                net_rev = revenue.iloc[0] if not revenue.empty and not pd.isna(revenue.iloc[0]) else np.nan

                if "Gross Profit" in financials.index:
                    gp = financials.loc["Gross Profit"]
                    if len(gp) >= 2 and gp.iloc[1] != 0:
                        gross_profit_growth = (gp.iloc[0] - gp.iloc[1]) / gp.iloc[1]
                    else:
                        gross_profit_growth = np.nan
                else:
                    gross_profit_growth = np.nan

                if "Operating Income" in financials.index:
                    oi = financials.loc["Operating Income"]
                    if len(oi) >= 2 and oi.iloc[1] != 0:
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
                balance_sheet = safe_yf_call(lambda: ticker.balance_sheet)
                if balance_sheet is None or not isinstance(balance_sheet, pd.DataFrame):
                    balance_sheet = pd.DataFrame()
                total_assets = balance_sheet.loc["Total Assets"].iloc[0] if "Total Assets" in balance_sheet.index else np.nan
                total_liabilities = (
                    balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[0]
                    if "Total Liabilities Net Minority Interest" in balance_sheet.index
                    else np.nan
                )
                equity = (
                    balance_sheet.loc["Total Equity Gross Minority Interest"].iloc[0]
                    if "Total Equity Gross Minority Interest" in balance_sheet.index
                    else np.nan
                )

                inventory = balance_sheet.loc["Total Inventory"].iloc[0] if "Total Inventory" in balance_sheet.index else np.nan
                cash = (
                    balance_sheet.loc["Cash And Cash Equivalents"].iloc[0]
                    if "Cash And Cash Equivalents" in balance_sheet.index
                    else np.nan
                )
                non_current_liabilities = (
                    balance_sheet.loc["Non-Current Liabilities"].iloc[0]
                    if "Non-Current Liabilities" in balance_sheet.index
                    else np.nan
                )

                assets_growth = np.nan
                equity_growth = np.nan

                if "Total Assets" in balance_sheet.index:
                    assets = balance_sheet.loc["Total Assets"]
                    if len(assets) >= 2 and assets.iloc[1] != 0:
                        assets_growth = (assets.iloc[0] - assets.iloc[1]) / assets.iloc[1]

                if "Total Equity Gross Minority Interest" in balance_sheet.index:
                    eq = balance_sheet.loc["Total Equity Gross Minority Interest"]
                    if len(eq) >= 2 and eq.iloc[1] != 0:
                        equity_growth = (eq.iloc[0] - eq.iloc[1]) / eq.iloc[1]

                inv_asset_ratio = (
                    inventory / total_assets
                    if pd.notna(total_assets) and total_assets != 0 and pd.notna(inventory)
                    else np.nan
                )
                cash_asset_ratio = (
                    cash / total_assets
                    if pd.notna(total_assets) and total_assets != 0 and pd.notna(cash)
                    else np.nan
                )
                ncd_liabilities_ratio = (
                    non_current_liabilities / total_liabilities
                    if pd.notna(total_liabilities) and total_liabilities != 0 and pd.notna(non_current_liabilities)
                    else np.nan
                )

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
                cashflow = safe_yf_call(lambda: ticker.cashflow)
                if cashflow is None or not isinstance(cashflow, pd.DataFrame):
                    cashflow = pd.DataFrame()
                operating_cashflow = (
                    cashflow.loc["Operating Cash Flow"].iloc[0]
                    if "Operating Cash Flow" in cashflow.index
                    else np.nan
                )
                capex = (
                    -cashflow.loc["Capital Expenditure"].iloc[0]
                    if "Capital Expenditure" in cashflow.index
                    else 0.0
                )
                free_cashflow = (
                    operating_cashflow - capex
                    if pd.notna(operating_cashflow) and pd.notna(capex)
                    else np.nan
                )
                capex_to_cashflow = (
                    capex / operating_cashflow
                    if pd.notna(operating_cashflow) and operating_cashflow != 0
                    else np.nan
                )
            except Exception:
                operating_cashflow = np.nan
                capex = np.nan
                free_cashflow = np.nan
                capex_to_cashflow = np.nan

            # 基本面指標計算
            debt_ratio = (
                total_liabilities / total_assets
                if pd.notna(total_assets) and total_assets != 0
                else np.nan
            )
            net_income_growth = eps_growth
            cashflow_profit_ratio = (
                operating_cashflow / net_income
                if pd.notna(net_income) and net_income != 0
                else np.nan
            )
            fcf_revenue_ratio = (
                free_cashflow / net_rev
                if pd.notna(net_rev) and net_rev != 0
                else np.nan
            )
            fcf_price_ratio = (
                free_cashflow / (price * 1e8)
                if pd.notna(price) and price != 0 and pd.notna(free_cashflow)
                else np.nan
            )
            fcf_growth = eps_growth
            cash_dividend_yield = (
                div_per_share / price
                if pd.notna(div_per_share) and pd.notna(price) and price != 0
                else np.nan
            )
            book_value_growth = equity_growth

            # 技術面指標（基於歷史股價）
            df = hist.copy()
            df["ma5"] = ta.sma(df["Close"], 5)
            df["ma20"] = ta.sma(df["Close"], 20)
            df["ma60"] = ta.sma(df["Close"], 60)
            df["偏差"] = (df["Close"] - df["ma20"]) / df["ma20"]
            df["rsi"] = ta.rsi(df["Close"], 14)

            try:
                macd_df = ta.macd(df["Close"])
                if isinstance(macd_df, pd.DataFrame) and not macd_df.empty:
                    df["macd"] = macd_df.iloc[:, 0]
                    df["macd_signal"] = macd_df.iloc[:, 1]
                else:
                    df["macd"] = np.nan
                    df["macd_signal"] = np.nan
            except Exception:
                df["macd"] = np.nan
                df["macd_signal"] = np.nan

            try:
                bb = ta.bbands(df["Close"])
                df["布林上"] = bb.iloc[:, 0]
                df["布林中"] = bb.iloc[:, 1]
                df["布林下"] = bb.iloc[:, 2]
            except Exception:
                df["布林上"] = np.nan
                df["布林中"] = np.nan
                df["布林下"] = np.nan

            df["high_52"] = df["High"].max()
            df["low_52"] = df["Low"].min()
            df["std"] = df["Close"].rolling(window=20).std()
            df["atr"] = ta.atr(df["High"], df["Low"], df["Close"], 14)

            latest = df.iloc[-1]
            prev_close = (
                df["Close"].iloc[-2]
                if len(df) >= 2 and not pd.isna(df["Close"].iloc[-2])
                else price
            )
            price_change = price - prev_close
            price_change_pct = price_change / prev_close * 100 if prev_close else 0

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
                "name": stock_meta.get("name", code),
                "suffix": suffix,
                "price_change": price_change,
                "price_change_pct": price_change_pct,

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
                "peg": peg_ratio,
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
                "high_52": df["High"].max(),
                "low_52": df["Low"].min(),

                # 財務與資本結構
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "equity": equity,
                "capex": capex,
                "capex_to_cashflow": capex_to_cashflow,

                # 成長性
                "gross_profit_growth": gross_profit_growth,
                "operating_income_growth": operating_income_growth,
                "assets_growth": assets_growth,
                "equity_growth": equity_growth,

                # 財務結構
                "inv_asset_ratio": inv_asset_ratio,
                "cash_asset_ratio": cash_asset_ratio,
                "ncd_liabilities_ratio": ncd_liabilities_ratio,

                # 現金流與股利
                "fcf_revenue_ratio": fcf_revenue_ratio,
                "fcf_price_ratio": fcf_price_ratio,
                "fcf_growth": fcf_growth,
                "cash_dividend_yield": cash_dividend_yield,
                "book_value_growth": book_value_growth,
            }

        except Exception as e:
            last_error = e
            continue

    st.info("⚠️ Yahoo Finance 目前可能限流（429 / Too Many Requests），請稍後再試。")
    if last_error:
        st.caption(f"最後錯誤：{str(last_error)[:120]}")
    return None


# --- 4. AI 會話 ---
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

        eps_val = round(float(eps), 2) if pd.notna(eps) else 0
        pe_val = round(float(pe), 1) if pd.notna(pe) else 0
        roe_val = round(float(roe) * 100, 1) if pd.notna(roe) else 0
        rsi_val = round(float(rsi), 1) if pd.notna(rsi) else 50
        price_val = round(float(price), 1) if pd.notna(price) else 0

        prompt = f"""針對 {d['name']} ({code})：
        現價 {price_val} 元，EPS {eps_val}，本益比 {pe_val}，ROE {roe_val}%
        RSI {rsi_val}，技術面多空由 MA5 / MA20 / MA60 趨勢判斷。
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


# --- 5. UI 主畫面 ---
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip().upper()
search_btn = st.sidebar.button("開始分析", use_container_width=True)

st.markdown("""
<style>
/* 1. 股票名稱大標題（用 st.title，會是 h1） */
h1 {
    color: #34495E !important;
    font-size: 1.9rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;
    margin-top: 0.1rem !important;
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    letter-spacing: -0.02em !important;
}
/* 2. 一、基本面、二、技術面、三、財務、四、現金流、五、AI診斷（用 st.header，會是 h2） */
h2 {
    color: #0095FF !important;
    font-size: 1.7rem !important;
    font-weight: 600 !important;
    margin-top: 0.7rem !important;
    margin-bottom: 0.3rem !important;
    padding-top: 0.2rem !important;
    padding-bottom: 0.2rem !important;
}
/* 3. 盈利能力、成長性、財務結構、現金流品質、估值水準（用 st.subheader，會是 h3） */
h3 {
    color: #E67E22 !important;
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.2rem !important;
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    border-left: 4px solid #E67E22 !important;
    padding-left: 0.5rem !important;
}
/* metric 數字 */
.metric-value {
    color: #2ECC71 !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.1rem !important;
    line-height: 1.2 !important;
}
/* metric 標籤 */
.metric-label {
    color: #555555 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    margin-top: 0.1rem !important;
    line-height: 1.3 !important;
}
/* 一般段落文字 */
.element-container p {
    color: #333333 !important;
    font-size: 0.95rem !important;
    line-height: 1.4 !important;
    margin: 0.2rem 0 !important;
}
/* 壓緊 header 間距 */
.st-emotion-cache-gi0tri {
    margin-bottom: 0.05rem !important;
    margin-top: 0.1rem !important;
    padding-top: 0.05rem !important;
    padding-bottom: 0.05rem !important;
    line-height: 1.1 !important;
}
</style>
""", unsafe_allow_html=True)

if search_btn and code_input:
    with st.spinner(f"🔄 分析 {code_input} 資料中..."):
        d = get_deep_analysis_data(code_input)

    if d:
        col1, col2 = st.columns([1, 2])

        with col1:
            stock_name = d.get("name") or code_input
            st.title(f"📊 {stock_name} ({code_input})")

        with col2:
            price = d.get("price", 0)
            hist = d.get("df", pd.DataFrame())

            prev_close = (
                hist["Close"].iloc[-2]
                if len(hist) >= 2 and not pd.isna(hist["Close"].iloc[-2])
                else price
            )
            change_price = price - prev_close
            change_percent = change_price / prev_close * 100 if prev_close else 0

            # 第一列：股價、漲跌、開盤、高點、低點
            t1, t2, t3, t4, t5, t6 = st.columns(6)
            t1.metric("即時股價：", f"{price:.1f}" if pd.notna(price) else "N/A")
            t2.metric("漲跌額：", f"{change_price:+.1f}" if pd.notna(change_price) else "N/A")
            t3.metric("漲跌幅：", f"{change_percent:+.1f}%" if pd.notna(change_percent) else "N/A")

            if not hist.empty:
                open_val = hist["Open"].iloc[-1] if "Open" in hist.columns else np.nan
                high_val = hist["High"].iloc[-1] if "High" in hist.columns else np.nan
                low_val = hist["Low"].iloc[-1] if "Low" in hist.columns else np.nan

                t4.metric("今日開盤：", f"{open_val:.1f}" if pd.notna(open_val) else "N/A")
                t5.metric("今日高點：", f"{high_val:.1f}" if pd.notna(high_val) else "N/A")
                t6.metric("今日低點：", f"{low_val:.1f}" if pd.notna(low_val) else "N/A")
            else:
                t4.metric("今日開盤：", "N/A")
                t5.metric("今日高點：", "N/A")
                t6.metric("今日低點：", "N/A")

            st.markdown("---", unsafe_allow_html=True)

            # 第二列：RSI、MACD、成交量、量價
            r1, r2, r3, r4, r5, r6 = st.columns(6)

            rsi_now = d.get("rsi", 50)
            if pd.notna(rsi_now):
                rsi_trend = ":red[偏高⭐️]" if rsi_now > 70 else ":green[偏低⚠️]" if rsi_now < 30 else "中間"
                r1.metric("RSI 趨勢：", rsi_trend)
                r2.metric("即時 RSI：", f"{rsi_now:.1f}")
            else:
                r1.metric("RSI 趨勢：", "N/A")
                r2.metric("即時 RSI：", "N/A")

            df = d.get("df", pd.DataFrame())
            macd_line = df["macd"].iloc[-1] if "macd" in df.columns and len(df) > 0 else np.nan
            macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns and len(df) > 0 else np.nan

            r3.metric("即時 MACD：", f"{macd_line:+.2f}" if pd.notna(macd_line) else "N/A")
            r4.metric("MACD 信號線：", f"{macd_signal:+.2f}" if pd.notna(macd_signal) else "N/A")

            volume = (
                df["Volume"].iloc[-1]
                if "Volume" in df.columns and len(df) > 0 and not pd.isna(df["Volume"].iloc[-1])
                else 0
            )
            r5.metric("成交量(張)：", f"{int(volume / 1000):,}")

            volume_trend = "量價資訊不足"
            if len(df) >= 2:
                latest_vol = df["Volume"].iloc[-1]
                prev_vol = df["Volume"].iloc[-2]

                if price > prev_close and latest_vol > prev_vol:
                    volume_trend = "價漲量增"
                elif price > prev_close and latest_vol <= prev_vol:
                    volume_trend = "價漲量縮"
                elif price < prev_close and latest_vol > prev_vol:
                    volume_trend = "價跌量增"
                else:
                    volume_trend = "價跌量縮"

            r6.metric("盤中量價：", volume_trend)

        #  ========== 一、基本面（公司賺不賺錢）==========
        st.header("📌 一、基本面：公司賺不賺錢")
        with st.container(border=True):
            # 盈利能力
            st.subheader("盈利能力")
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

            gp = d.get("gross_profit", np.nan)
            gp_pct = gp * 100 if pd.notna(gp) else np.nan
            gp_text = ":red[偏高⭐️]" if pd.notna(gp_pct) and gp_pct > 30 else ":orange[合理🟡]" if pd.notna(gp_pct) and gp_pct >= 20 else ":green[偏低⚠️]"
            c1.metric("毛利率", f"{gp_pct:.1f}% ({gp_text})" if pd.notna(gp_pct) else "N/A", help=f"毛利率：{gp_pct:.1f}% ({gp_text})\n毛利率高代表公司定價能力與成本控管較強。" if pd.notna(gp_pct) else "毛利率資料不足")

            nm = d.get("net_margin", np.nan)
            nm_pct = nm * 100 if pd.notna(nm) else np.nan
            nm_text = ":red[偏高⭐️]" if pd.notna(nm_pct) and nm_pct > 8 else ":orange[合理🟡]" if pd.notna(nm_pct) and nm_pct >= 4 else ":green[偏低⚠️]"
            c2.metric("淨利率", f"{nm_pct:.1f}% ({nm_text})" if pd.notna(nm_pct) else "N/A", help=f"淨利率：{nm_pct:.1f}% ({nm_text})\n淨利率高代表公司整體賺錢效率較佳。" if pd.notna(nm_pct) else "淨利率資料不足")

            om = d.get("op_margin", np.nan)
            om_pct = om * 100 if pd.notna(om) else np.nan
            om_text = ":red[偏高⭐️]" if pd.notna(om_pct) and om_pct > 10 else ":orange[合理🟡]" if pd.notna(om_pct) and om_pct >= 5 else ":green[偏低⚠️]"
            c3.metric("營業利益率", f"{om_pct:.1f}% ({om_text})" if pd.notna(om_pct) else "N/A", help=f"營業利益率：{om_pct:.1f}% ({om_text})\n主要反映本業的獲利穩定度。" if pd.notna(om_pct) else "營業利益率資料不足")

            eps = d.get("eps", np.nan)
            eps_text = ":red[偏高⭐️]" if pd.notna(eps) and eps > 3 else ":orange[合理🟡]" if pd.notna(eps) and eps >= 1.5 else ":green[偏低⚠️]"
            c4.metric("EPS", f"{eps:.2f} ({eps_text})" if pd.notna(eps) else "N/A", help=f"EPS：{eps:.2f} ({eps_text})\n每股盈餘，代表公司為股東賺多少錢。" if pd.notna(eps) else "EPS資料不足")

            roe = d.get("roe", np.nan)
            roe_pct = roe * 100 if pd.notna(roe) else np.nan
            roe_text = ":red[偏高⭐️]" if pd.notna(roe_pct) and roe_pct > 15 else ":orange[合理🟡]" if pd.notna(roe_pct) and roe_pct >= 10 else ":green[偏低⚠️]"
            c5.metric("ROE", f"{roe_pct:.1f}% ({roe_text})" if pd.notna(roe_pct) else "N/A", help=f"ROE：{roe_pct:.1f}% ({roe_text})\n權益報酬率，衡量股東資本的獲利效率。" if pd.notna(roe_pct) else "ROE資料不足")

            roa = d.get("roa", np.nan)
            roa_pct = roa * 100 if pd.notna(roa) else np.nan
            roa_text = ":red[偏高⭐️]" if pd.notna(roa_pct) and roa_pct > 8 else ":orange[合理🟡]" if pd.notna(roa_pct) and roa_pct >= 4 else ":green[偏低⚠️]"
            c6.metric("ROA", f"{roa_pct:.1f}% ({roa_text})" if pd.notna(roa_pct) else "N/A", help=f"ROA：{roa_pct:.1f}% ({roa_text})\n資產報酬率，衡量整體資產賺錢能力。" if pd.notna(roa_pct) else "ROA資料不足")

            eps_growth = d.get("eps_growth", np.nan)
            eps_growth_pct = eps_growth * 100 if pd.notna(eps_growth) else np.nan
            eps_growth_text = ":red[偏高⭐️]" if pd.notna(eps_growth_pct) and eps_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(eps_growth_pct) and eps_growth_pct >= 0 else ":green[偏低⚠️]"
            c7.metric("EPS 成長率", f"{eps_growth_pct:.1f}% ({eps_growth_text})" if pd.notna(eps_growth_pct) else "N/A", help=f"EPS 成長率：{eps_growth_pct:.1f}% ({eps_growth_text})\nEPS 的成長趨勢，看未來盈餘是否逐季／逐年增長。" if pd.notna(eps_growth_pct) else "EPS成長率資料不足")

            # 成長性
            st.subheader("成長性")
            g1, g2, g3, g4, g5, g6, g7 = st.columns(7)

            rev_growth = d.get("rev_growth", np.nan)
            rev_growth_pct = rev_growth * 100 if pd.notna(rev_growth) else np.nan
            rev_text = ":red[偏高⭐️]" if pd.notna(rev_growth_pct) and rev_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(rev_growth_pct) and rev_growth_pct >= 0 else ":green[偏低⚠️]"
            g1.metric("營收成長率", f"{rev_growth_pct:.1f}% ({rev_text})" if pd.notna(rev_growth_pct) else "N/A", help=f"營收成長率：{rev_growth_pct:.1f}% ({rev_text})\n衡量公司業務規模是否在擴張。" if pd.notna(rev_growth_pct) else "營收成長率資料不足")

            g2.metric("EPS 成長率", f"{eps_growth_pct:.1f}% ({eps_growth_text})" if pd.notna(eps_growth_pct) else "N/A", help=f"EPS 成長率：{eps_growth_pct:.1f}% ({eps_growth_text})\n每股盈餘的成長是否穩定。" if pd.notna(eps_growth_pct) else "EPS成長率資料不足")

            net_income_growth = d.get("net_income_growth", np.nan)
            net_income_growth_pct = net_income_growth * 100 if pd.notna(net_income_growth) else np.nan
            net_income_text = ":red[偏高⭐️]" if pd.notna(net_income_growth_pct) and net_income_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(net_income_growth_pct) and net_income_growth_pct >= 0 else ":green[偏低⚠️]"
            g3.metric("淨利成長率", f"{net_income_growth_pct:.1f}% ({net_income_text})" if pd.notna(net_income_growth_pct) else "N/A", help=f"淨利成長率：{net_income_growth_pct:.1f}% ({net_income_text})\n淨利的成長趨勢，代表獲利品質的穩定度。" if pd.notna(net_income_growth_pct) else "淨利成長率資料不足")

            gross_profit_growth = d.get("gross_profit_growth", np.nan)
            gross_profit_growth_pct = gross_profit_growth * 100 if pd.notna(gross_profit_growth) else np.nan
            gross_profit_text = ":red[偏高⭐️]" if pd.notna(gross_profit_growth_pct) and gross_profit_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(gross_profit_growth_pct) and gross_profit_growth_pct >= 0 else ":green[偏低⚠️]"
            g4.metric("毛利成長率", f"{gross_profit_growth_pct:.1f}% ({gross_profit_text})" if pd.notna(gross_profit_growth_pct) else "N/A", help=f"毛利成長率：{gross_profit_growth_pct:.1f}% ({gross_profit_text})\n毛利的成長，是淨利成長的先行指標。" if pd.notna(gross_profit_growth_pct) else "毛利成長率資料不足")

            op_income_growth = d.get("operating_income_growth", np.nan)
            op_income_growth_pct = op_income_growth * 100 if pd.notna(op_income_growth) else np.nan
            op_income_text = ":red[偏高⭐️]" if pd.notna(op_income_growth_pct) and op_income_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(op_income_growth_pct) and op_income_growth_pct >= 0 else ":green[偏低⚠️]"
            g5.metric("營業利益成長率", f"{op_income_growth_pct:.1f}% ({op_income_text})" if pd.notna(op_income_growth_pct) else "N/A", help=f"營業利益成長率：{op_income_growth_pct:.1f}% ({op_income_text})\n本業利潤的成長狀況。" if pd.notna(op_income_growth_pct) else "營業利益成長率資料不足")

            assets_growth = d.get("assets_growth", np.nan)
            assets_growth_pct = assets_growth * 100 if pd.notna(assets_growth) else np.nan
            assets_text = ":red[偏高⭐️]" if pd.notna(assets_growth_pct) and assets_growth_pct > 5 else ":orange[合理🟡]" if pd.notna(assets_growth_pct) and assets_growth_pct >= 0 else ":green[偏低⚠️]"
            g6.metric("資產成長率", f"{assets_growth_pct:.1f}% ({assets_text})" if pd.notna(assets_growth_pct) else "N/A", help=f"資產成長率：{assets_growth_pct:.1f}% ({assets_text})\n公司資產規模是否在擴張。" if pd.notna(assets_growth_pct) else "資產成長率資料不足")

            equity_growth = d.get("equity_growth", np.nan)
            equity_growth_pct = equity_growth * 100 if pd.notna(equity_growth) else np.nan
            equity_text = ":red[偏高⭐️]" if pd.notna(equity_growth_pct) and equity_growth_pct > 8 else ":orange[合理🟡]" if pd.notna(equity_growth_pct) and equity_growth_pct >= 0 else ":green[偏低⚠️]"
            g7.metric("權益成長率", f"{equity_growth_pct:.1f}% ({equity_text})" if pd.notna(equity_growth_pct) else "N/A", help=f"權益成長率：{equity_growth_pct:.1f}% ({equity_text})\n股東權益的成長，代表公司累積盈餘是否在增加。" if pd.notna(equity_growth_pct) else "權益成長率資料不足")

            # 財務結構
            st.subheader("財務結構")
            f1, f2, f3, f4, f5, f6, f7 = st.columns(7)

            debt_ratio = d.get("debt_ratio", np.nan)
            debt_ratio_pct = debt_ratio * 100 if pd.notna(debt_ratio) else np.nan
            debt_text = ":red[低風險⭐️]" if pd.notna(debt_ratio_pct) and debt_ratio_pct < 50 else ":orange[中等🟡]" if pd.notna(debt_ratio_pct) and debt_ratio_pct <= 70 else ":green[高風險⚠️]"
            f1.metric("負債比率", f"{debt_ratio_pct:.1f}% ({debt_text})" if pd.notna(debt_ratio_pct) else "N/A", help=f"負債比率：{debt_ratio_pct:.1f}% ({debt_text})\n越高代表公司負債壓力越大。" if pd.notna(debt_ratio_pct) else "負債比率資料不足")

            debt_to_equity = d.get("debt_to_equity", np.nan)
            debt_to_equity_pct = debt_to_equity * 100 if pd.notna(debt_to_equity) else np.nan
            dte_text = ":red[低風險⭐️]" if pd.notna(debt_to_equity_pct) and debt_to_equity_pct < 50 else ":orange[中等🟡]" if pd.notna(debt_to_equity_pct) and debt_to_equity_pct <= 100 else ":green[高風險⚠️]"
            f2.metric("負債/股東權益", f"{debt_to_equity_pct:.1f}% ({dte_text})" if pd.notna(debt_to_equity_pct) else "N/A", help=f"負債/股東權益：{debt_to_equity_pct:.1f}% ({dte_text})\n衡量公司使用借貸槓桿的程度。" if pd.notna(debt_to_equity_pct) else "負債/股東權益資料不足")

            current_ratio = d.get("current_ratio", np.nan)
            current_text = ":red[偏高⭐️]" if pd.notna(current_ratio) and current_ratio > 2 else ":orange[合理🟡]" if pd.notna(current_ratio) and current_ratio >= 1 else ":green[偏低⚠️]"
            f3.metric("流動比率", f"{current_ratio:.2f} ({current_text})" if pd.notna(current_ratio) else "N/A", help=f"流動比率：{current_ratio:.2f} ({current_text})\n衡量公司短期償債能力，一般以 1.5～2 倍為佳。" if pd.notna(current_ratio) else "流動比率資料不足")

            quick_ratio = d.get("quick_ratio", np.nan)
            quick_text = ":red[偏高⭐️]" if pd.notna(quick_ratio) and quick_ratio > 1.5 else ":orange[合理🟡]" if pd.notna(quick_ratio) and quick_ratio >= 0.7 else ":green[偏低⚠️]"
            f4.metric("速動比率", f"{quick_ratio:.2f} ({quick_text})" if pd.notna(quick_ratio) else "N/A", help=f"速動比率：{quick_ratio:.2f} ({quick_text})\n扣除存貨後的短期償債能力指標，愈高愈好。" if pd.notna(quick_ratio) else "速動比率資料不足")

            inv_asset_ratio = d.get("inv_asset_ratio", np.nan)
            inv_text = ":green[偏高⚠️]" if pd.notna(inv_asset_ratio) and inv_asset_ratio > 0.5 else ":orange[合理🟡]" if pd.notna(inv_asset_ratio) and inv_asset_ratio >= 0.2 else ":red[偏低⭐️]"
            f5.metric("存貨佔資產比", f"{inv_asset_ratio:.1%} ({inv_text})" if pd.notna(inv_asset_ratio) else "N/A", help=f"存貨佔資產比：{inv_asset_ratio:.1%} ({inv_text})\n存貨過高可能有跌價與庫存風險。" if pd.notna(inv_asset_ratio) else "存貨佔資產比資料不足")

            cash_asset_ratio = d.get("cash_asset_ratio", np.nan)
            cash_text = ":red[偏高⭐️]" if pd.notna(cash_asset_ratio) and cash_asset_ratio > 0.1 else ":orange[合理🟡]" if pd.notna(cash_asset_ratio) and cash_asset_ratio >= 0.05 else ":green[偏低⚠️]"
            f6.metric("現金佔資產比", f"{cash_asset_ratio:.1%} ({cash_text})" if pd.notna(cash_asset_ratio) else "N/A", help=f"現金佔資產比：{cash_asset_ratio:.1%} ({cash_text})\n愈高代表公司現金儲備愈充裕。" if pd.notna(cash_asset_ratio) else "現金佔資產比資料不足")

            ncd_liabilities_ratio = d.get("ncd_liabilities_ratio", np.nan)
            ncd_text = ":green[偏高⚠️]" if pd.notna(ncd_liabilities_ratio) and ncd_liabilities_ratio > 0.8 else ":orange[合理🟡]" if pd.notna(ncd_liabilities_ratio) and ncd_liabilities_ratio >= 0.5 else ":red[偏低⭐️]"
            f7.metric("非流動負債占負債比", f"{ncd_liabilities_ratio:.1%} ({ncd_text})" if pd.notna(ncd_liabilities_ratio) else "N/A", help=f"非流動負債占負債比：{ncd_liabilities_ratio:.1%} ({ncd_text})\n長期負債佔比愈高，財務結構愈偏長期化，但也可能增加利息支出壓力。" if pd.notna(ncd_liabilities_ratio) else "非流動負債占負債比資料不足")

            # 現金流品質
            st.subheader("現金流品質")
            ca1, ca2, ca3, ca4, ca5, ca6, ca7 = st.columns(7)

            operating_cashflow = d.get("operating_cashflow", np.nan)
            ca1.metric("營業現金流：", f"{operating_cashflow / 1e8:.1f}億" if pd.notna(operating_cashflow) else "N/A")

            free_cashflow = d.get("free_cashflow", np.nan)
            ca2.metric("自由現金流(FCF)：", f"{free_cashflow / 1e8:.1f}億" if pd.notna(free_cashflow) else "N/A")

            cashflow_profit_ratio = d.get("cashflow_profit_ratio", np.nan)
            cfp_text = ":red[偏高⭐️]" if pd.notna(cashflow_profit_ratio) and cashflow_profit_ratio > 1 else ":orange[合理🟡]" if pd.notna(cashflow_profit_ratio) and cashflow_profit_ratio >= 0.7 else ":green[偏低⚠️]"
            ca3.metric("現金流/淨利", f"{cashflow_profit_ratio:.2f} ({cfp_text})" if pd.notna(cashflow_profit_ratio) else "N/A", help=f"現金流/淨利：{cashflow_profit_ratio:.2f} ({cfp_text})\n>1 代表現金流比淨利佳，公司獲利品質較好。" if pd.notna(cashflow_profit_ratio) else "現金流/淨利資料不足")

            fcf_revenue_ratio = d.get("fcf_revenue_ratio", np.nan)
            fcf_rev_text = ":red[偏高⭐️]" if pd.notna(fcf_revenue_ratio) and fcf_revenue_ratio > 0.15 else ":orange[合理🟡]" if pd.notna(fcf_revenue_ratio) and fcf_revenue_ratio >= 0.05 else ":green[偏低⚠️]"
            ca4.metric("FCF/營收", f"{fcf_revenue_ratio:.1%} ({fcf_rev_text})" if pd.notna(fcf_revenue_ratio) else "N/A", help=f"FCF/營收：{fcf_revenue_ratio:.1%} ({fcf_rev_text})\n自由現金流佔營收的比例，愈高代表現金生成力愈強。" if pd.notna(fcf_revenue_ratio) else "FCF/營收資料不足")

            fcf_price_ratio = d.get("fcf_price_ratio", np.nan)
            fcf_price_text = ":red[偏高⭐️]" if pd.notna(fcf_price_ratio) and fcf_price_ratio > 0.05 else ":orange[合理🟡]" if pd.notna(fcf_price_ratio) and fcf_price_ratio >= 0.01 else ":green[偏低⚠️]"
            ca5.metric("FCF/股價", f"{fcf_price_ratio:.1%} ({fcf_price_text})" if pd.notna(fcf_price_ratio) else "N/A", help=f"FCF/股價：{fcf_price_ratio:.1%} ({fcf_price_text})\n每單位股價背後有多少自由現金流支撐。" if pd.notna(fcf_price_ratio) else "FCF/股價資料不足")

            fcf_growth = d.get("fcf_growth", np.nan)
            fcf_growth_pct = fcf_growth * 100 if pd.notna(fcf_growth) else np.nan
            fcf_growth_text = ":red[偏高⭐️]" if pd.notna(fcf_growth_pct) and fcf_growth_pct > 10 else ":orange[合理🟡]" if pd.notna(fcf_growth_pct) and fcf_growth_pct >= 0 else ":green[偏低⚠️]"
            ca6.metric("FCF 成長率", f"{fcf_growth_pct:.1f}% ({fcf_growth_text})" if pd.notna(fcf_growth_pct) else "N/A", help=f"FCF 成長率：{fcf_growth_pct:.1f}% ({fcf_growth_text})\n自由現金流的年成長率，代表現金生成力是否在提升。" if pd.notna(fcf_growth_pct) else "FCF成長率資料不足")

            capex_to_cashflow = d.get("capex_to_cashflow", np.nan)
            capex_cf_text = ":red[偏高⭐️]" if pd.notna(capex_to_cashflow) and capex_to_cashflow > 1.0 else ":orange[合理🟡]" if pd.notna(capex_to_cashflow) and capex_to_cashflow >= 0.5 else ":green[偏低⚠️]"
            ca7.metric("資本支出/營業現金流", f"{capex_to_cashflow:.2f} ({capex_cf_text})" if pd.notna(capex_to_cashflow) else "N/A", help=f"資本支出/營業現金流：{capex_to_cashflow:.2f} ({capex_cf_text})\n>1 代表資本支出比營業現金流還多，可能有現金流壓力。" if pd.notna(capex_to_cashflow) else "資本支出/營業現金流資料不足")

            # 估值水準
            st.subheader("估值水準")
            v1, v2, v3, v4, v5, v6, v7 = st.columns(7)

            pe = d.get("pe", np.nan)
            pe_text = ":green[偏高估⚠️]" if pd.notna(pe) and pe > 20 else ":orange[合理🟡]" if pd.notna(pe) and pe >= 10 else ":red[偏低估⭐️]"
            v1.metric("本益比(P/E)", f"{pe:.1f}x ({pe_text})" if pd.notna(pe) else "N/A", help=f"本益比(P/E)：{pe:.1f}x ({pe_text})\n偏高代表可能較貴，偏低代表可能較便宜。" if pd.notna(pe) else "本益比資料不足")

            pb = d.get("pb", np.nan)
            pb_text = ":green[偏高估⚠️]" if pd.notna(pb) and pb > 3 else ":orange[合理🟡]" if pd.notna(pb) and pb >= 1 else ":red[偏低估⭐️]"
            v2.metric("股價淨值比(P/B)", f"{pb:.1f}x ({pb_text})" if pd.notna(pb) else "N/A", help=f"股價淨值比(P/B)：{pb:.1f}x ({pb_text})\n偏高代表可能高估，偏低代表可能低估，但與產業特性有關。" if pd.notna(pb) else "股價淨值比資料不足")

            peg = d.get("peg", np.nan)
            peg_text = ":green[偏高估⚠️]" if pd.notna(peg) and peg > 1.5 else ":orange[合理🟡]" if pd.notna(peg) and peg >= 1.0 else ":red[偏低估⭐️]"
            v3.metric("PEG", f"{peg:.1f} ({peg_text})" if pd.notna(peg) else "N/A", help=f"PEG：{peg:.1f} ({peg_text})\nPEG 用成長率調整本益比，愈接近 1 愈合理。" if pd.notna(peg) else "PEG資料不足")

            div_yield = d.get("dividend_yield", np.nan)
            div_yield_pct = div_yield * 100 if pd.notna(div_yield) else np.nan
            div_text = ":red[偏高⭐️]" if pd.notna(div_yield_pct) and div_yield_pct > 5 else ":orange[合理🟡]" if pd.notna(div_yield_pct) and div_yield_pct >= 2 else ":green[偏低⚠️]"
            v4.metric("股利殖利率", f"{div_yield_pct:.1f}% ({div_text})" if pd.notna(div_yield_pct) else "N/A", help=f"股利殖利率：{div_yield_pct:.1f}% ({div_text})\n偏高代表現金回報較高，但要注意是否可持續。" if pd.notna(div_yield_pct) else "股利殖利率資料不足")

            payout_ratio = d.get("payout_ratio", np.nan)
            payout_ratio_pct = payout_ratio * 100 if pd.notna(payout_ratio) else np.nan
            payout_text = ":red[偏高⭐️]" if pd.notna(payout_ratio_pct) and payout_ratio_pct > 70 else ":orange[合理🟡]" if pd.notna(payout_ratio_pct) and payout_ratio_pct >= 30 else ":green[偏低⚠️]"
            v5.metric("盈餘配發率", f"{payout_ratio_pct:.1f}% ({payout_text})" if pd.notna(payout_ratio_pct) else "N/A", help=f"盈餘配發率：{payout_ratio_pct:.1f}% ({payout_text})\n偏高代表多數盈餘用於配股，偏低則代表多數盈餘用於再投資。" if pd.notna(payout_ratio_pct) else "盈餘配發率資料不足")

            cash_dividend_yield = d.get("cash_dividend_yield", np.nan)
            cash_dividend_yield_pct = cash_dividend_yield * 100 if pd.notna(cash_dividend_yield) else np.nan
            cd_text = ":red[偏高⭐️]" if pd.notna(cash_dividend_yield_pct) and cash_dividend_yield_pct > 5 else ":orange[合理🟡]" if pd.notna(cash_dividend_yield_pct) and cash_dividend_yield_pct >= 2 else ":green[偏低⚠️]"
            v6.metric("現金股利報酬率", f"{cash_dividend_yield_pct:.1f}% ({cd_text})" if pd.notna(cash_dividend_yield_pct) else "N/A", help=f"現金股利報酬率：{cash_dividend_yield_pct:.1f}% ({cd_text})\n多少現金股利相對於股價的比例。" if pd.notna(cash_dividend_yield_pct) else "現金股利報酬率資料不足")

            book_value_growth = d.get("book_value_growth", np.nan)
            book_value_growth_pct = book_value_growth * 100 if pd.notna(book_value_growth) else np.nan
            bv_text = ":red[偏高⭐️]" if pd.notna(book_value_growth_pct) and book_value_growth_pct > 8 else ":orange[合理🟡]" if pd.notna(book_value_growth_pct) and book_value_growth_pct >= 0 else ":green[偏低⚠️]"
            v7.metric("帳面價值成長率", f"{book_value_growth_pct:.1f}% ({bv_text})" if pd.notna(book_value_growth_pct) else "N/A", help=f"帳面價值成長率：{book_value_growth_pct:.1f}% ({bv_text})\n代表公司帳面資產與淨值的成長速度。" if pd.notna(book_value_growth_pct) else "帳面價值成長率資料不足")

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
                ma5 = latest.get("ma5", price)
                ma5_text = ":red[多頭]" if pd.notna(ma5) and price > ma5 else ":green[空頭]"
                t1.metric("MA5", f"{ma5:.1f} ({ma5_text})" if pd.notna(ma5) else "N/A", help=f"MA5：{ma5:.1f} ({ma5_text})\n5日均線，股價在均線上方為多頭。" if pd.notna(ma5) else "MA5資料不足")

                ma20 = latest.get("ma20", price)
                ma20_text = ":red[多頭]" if pd.notna(ma20) and price > ma20 else ":green[空頭]"
                t1.metric("MA20", f"{ma20:.1f} ({ma20_text})" if pd.notna(ma20) else "N/A", help=f"MA20：{ma20:.1f} ({ma20_text})\n20日均線，中期趨勢判斷。" if pd.notna(ma20) else "MA20資料不足")

                ma60 = latest.get("ma60", price)
                ma60_text = ":red[多頭]" if pd.notna(ma60) and price > ma60 else ":green[空頭]"
                t1.metric("MA60", f"{ma60:.1f} ({ma60_text})" if pd.notna(ma60) else "N/A", help=f"MA60：{ma60:.1f} ({ma60_text})\n60日均線，長期趨勢判斷。" if pd.notna(ma60) else "MA60資料不足")

                bias = d.get("bias", np.nan)
                bias_text = ":red[偏離太大⚠️]" if pd.notna(bias) and bias > 10 else ":green[偏離太小⭐️]" if pd.notna(bias) and bias < -10 else ":orange[合理🟡]"
                t1.metric("乖離率", f"{bias:.1f}% ({bias_text})" if pd.notna(bias) else "N/A", help=f"乖離率：{bias:.1f}% ({bias_text})\n股價偏離20日均線的百分比，±10%內為合理範圍。" if pd.notna(bias) else "乖離率資料不足")

                # 動能與強度
                t2.subheader("動能與強度")
                rsi = d.get("rsi", np.nan)
                if pd.notna(rsi):
                    rsi_text = "過熱🔴" if rsi > 70 else "過冷🟢" if rsi < 30 else "中性🟡"
                    t2.metric("RSI", f"{rsi:.1f} ({rsi_text})", help=f"RSI：{rsi:.1f} ({rsi_text})\n相對強弱指標，>70過熱、<30過冷。")
                else:
                    t2.metric("RSI", "N/A", help="RSI資料不足")

                macd_line = df["macd"].iloc[-1] if "macd" in df.columns else np.nan
                macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else np.nan

                macd_text = ":red[多頭]" if pd.notna(macd_line) and pd.notna(macd_signal) and macd_line > macd_signal else ":green[空頭]"
                t2.metric("MACD 本體", f"{macd_line:+.2f} ({macd_text})" if pd.notna(macd_line) else "N/A", help=f"MACD 本體：{macd_line:+.2f} ({macd_text})\nMACD線高於信號線為多頭訊號。" if pd.notna(macd_line) else "MACD本體資料不足")

                signal_text = ":red[多頭]" if pd.notna(macd_signal) and macd_signal > 0 else ":green[空頭]"
                t2.metric("MACD 信號線", f"{macd_signal:+.2f} ({signal_text})" if pd.notna(macd_signal) else "N/A", help=f"MACD 信號線：{macd_signal:+.2f} ({signal_text})\n信號線>0為多頭趨勢。" if pd.notna(macd_signal) else "MACD信號線資料不足")

                # 波動與區間
                t3.subheader("波動與區間")
                bb_upper = d.get("bb_upper", np.nan)
                bb_mid = d.get("bb_mid", np.nan)
                bb_lower = d.get("bb_lower", np.nan)

                if pd.notna(bb_upper) and price > bb_upper:
                    bb_upper_text = ":green[多頭強、偏積極🟢]"
                elif pd.notna(bb_lower) and price < bb_lower:
                    bb_upper_text = ":red[多頭弱、偏保守🔴]"
                else:
                    bb_upper_text = ":orange[合理🟡]"

                t3.metric("布林上軌", f"{bb_upper:.1f} ({bb_upper_text})" if pd.notna(bb_upper) else "N/A", help=f"布林上軌：{bb_upper:.1f} ({bb_upper_text})\n股價突破上軌代表強勢。" if pd.notna(bb_upper) else "布林上軌資料不足")
                t3.metric("布林中軌", f"{bb_mid:.1f}" if pd.notna(bb_mid) else "N/A", help=f"布林中軌 {bb_mid:.1f} - 20日移動平均線" if pd.notna(bb_mid) else "布林中軌資料不足")

                if pd.notna(bb_lower) and price < bb_lower:
                    bb_lower_text = ":red[多頭弱、偏保守🔴]"
                else:
                    bb_lower_text = ":orange[偏中風險🟡]"

                t3.metric("布林下軌", f"{bb_lower:.1f} ({bb_lower_text})" if pd.notna(bb_lower) else "N/A", help=f"布林下軌：{bb_lower:.1f} ({bb_lower_text})\n股價跌破下軌代表弱勢。" if pd.notna(bb_lower) else "布林下軌資料不足")

                high_52 = d.get("high_52", np.nan)
                low_52 = d.get("low_52", np.nan)

                high_text = ":green[52週新高(多頭強、但也偏貴)]" if pd.notna(high_52) and price > high_52 else ":orange[未新高🟡]"
                t3.metric("52週高價", f"{high_52:.1f} ({high_text})" if pd.notna(high_52) else "N/A", help=f"52週高價：{high_52:.1f} ({high_text})\n過去52週最高價。" if pd.notna(high_52) else "52週高價資料不足")

                low_text = ":red[52週新低(多頭弱、但也偏便宜)]" if pd.notna(low_52) and price < low_52 else ":orange[未新低🟡]"
                t3.metric("52週低價", f"{low_52:.1f} ({low_text})" if pd.notna(low_52) else "N/A", help=f"52週低價：{low_52:.1f} ({low_text})\n過去52週最低價。" if pd.notna(low_52) else "52週低價資料不足")

                std_20 = df["std"].iloc[-1] if "std" in df.columns else np.nan
                std_text = ":green[波動大、風險高]" if pd.notna(std_20) and std_20 > 3 else ":orange[合理🟡]" if pd.notna(std_20) and std_20 > 1 else ":red[波動小、風險低]"
                t3.metric("標準差(20日)", f"{std_20:.2f} ({std_text})" if pd.notna(std_20) else "N/A", help=f"標準差(20日)：{std_20:.2f} ({std_text})\n衡量股價波動程度。" if pd.notna(std_20) else "標準差資料不足")

                atr = d.get("atr", np.nan)
                atr_text = ":green[波動大、風險高]" if pd.notna(atr) and atr > 3 else ":orange[合理🟡]" if pd.notna(atr) and atr > 1 else ":red[波動小、風險低]"
                t3.metric("ATR(14日)", f"{atr:.2f} ({atr_text})" if pd.notna(atr) else "N/A", help=f"ATR(14日)：{atr:.2f} ({atr_text})\n平均真實波幅，衡量每日波動範圍。" if pd.notna(atr) else "ATR資料不足")

                # 成交量與量價關係
                t4.subheader("成交量與量價關係")
                latest_volume = latest["Volume"] if "Volume" in latest.index and pd.notna(latest["Volume"]) else 0
                t4.metric("今日成交量", f"{int(latest_volume / 1000):,} 張", help=f"今日成交量：{int(latest_volume / 1000):,} 張\n成交量放大代表市場關注度高。")

                price_change_pct = d.get("price_change_pct", 0)
                volume = latest_volume
                avg_volume = df["Volume"][-30:].mean() if "Volume" in df.columns and len(df) >= 30 else 0

                if price_change_pct > 0 and volume > avg_volume * 1.2:
                    vol_price_text = "🟢 價漲量增 - 多頭強，但偏高風險（高檔追高要小心）"
                elif price_change_pct < 0 and volume > avg_volume * 1.2:
                    vol_price_text = "🔴 價跌量增 - 多頭出場、拋售，偏壞"
                elif price_change_pct > 0 and volume < avg_volume * 0.8:
                    vol_price_text = "🔴 價漲量縮 - 動能不足，偏高風險"
                elif price_change_pct < 0 and volume < avg_volume * 0.8:
                    vol_price_text = "🟡 價跌量縮 - 市場觀望，偏中性"
                else:
                    vol_price_text = "⚪ 價量正常 - 偏中性"

                t4.metric("量價關係", vol_price_text, help=f"量價關係：{vol_price_text}\n價漲量增最健康，價跌量增最危險。")

        #  ========== 三、財務與資本結構（公司資本是否健康）==========
        st.header("🏦 三、財務與資本結構：公司資本是否健康")
        with st.container(border=True):
            s1, s2, s3, s4 = st.columns(4)

            total_assets = d.get("total_assets", np.nan)
            if pd.notna(total_assets):
                total_assets_text = ":red[資產偏高，公司規模大]" if total_assets / 1e9 > 100 else ":orange[資產合理]" if total_assets / 1e9 > 20 else ":green[資產偏小，規模較小]"
                s1.metric("總資產", f"{total_assets / 1e9:.1f} 億", help=f"總資產：{total_assets / 1e9:.1f} 億 元，{total_assets_text}")
            else:
                s1.metric("總資產", "N/A")

            total_liabilities = d.get("total_liabilities", np.nan)
            if pd.notna(total_liabilities):
                total_liabilities_text = ":red[負債偏高]" if total_liabilities / 1e9 > 60 else ":orange[負債合理]" if total_liabilities / 1e9 > 10 else ":green[負債偏低]"
                s2.metric("總負債", f"{total_liabilities / 1e9:.1f} 億", help=f"總負債：{total_liabilities / 1e9:.1f} 億 元，{total_liabilities_text}")
            else:
                s2.metric("總負債", "N/A")

            equity = d.get("equity", np.nan)
            if pd.notna(equity):
                equity_text = ":red[權益偏高]" if equity / 1e9 > 40 else ":orange[權益合理]" if equity / 1e9 > 5 else ":green[權益偏低]"
                s3.metric("股東權益", f"{equity / 1e9:.1f} 億", help=f"股東權益：{equity / 1e9:.1f} 億 元，{equity_text}")
            else:
                s3.metric("股東權益", "N/A")

            capex = d.get("capex", np.nan)
            if pd.notna(capex):
                capex_text = ":red[資本支出偏高]" if capex / 1e8 > 20 else ":orange[資本支出合理]" if capex / 1e8 > 3 else ":green[資本支出偏低]"
                s4.metric("資本支出(Capex)", f"{capex / 1e8:.1f} 億", help=f"資本支出：{capex / 1e8:.1f} 億 元，{capex_text}")
            else:
                s4.metric("資本支出(Capex)", "N/A")

            capex_to_cashflow = d.get("capex_to_cashflow", np.nan)
            if pd.notna(capex_to_cashflow):
                ctc_text = ":red[偏高，資本支出占營業現金流過高]" if capex_to_cashflow > 1.0 else ":orange[合理，資本支出適中]" if capex_to_cashflow > 0.5 else ":green[偏低，資本支出偏小]"
                st.metric("資本支出/營業現金流", f"{capex_to_cashflow:.2f}", help=f"資本支出佔營業現金流比例：{capex_to_cashflow:.2%}，{ctc_text}")
            else:
                st.metric("資本支出/營業現金流", "N/A")

        #  ========== 四、現金流與股利（現金能不能穩定入袋）==========
        st.header("💵 四、現金流與股利：現金能不能穩定入袋")
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns(4)

            fcf_revenue_ratio = d.get("fcf_revenue_ratio", np.nan)
            if pd.notna(fcf_revenue_ratio):
                fcf_revenue_text = ":red[偏高，每單位營收有高現金]" if fcf_revenue_ratio > 0.20 else ":orange[合理]" if fcf_revenue_ratio > 0.05 else ":green[偏低，營收現金化能力較弱]"
                f1.metric("自由現金流/營收", f"{fcf_revenue_ratio:.1%}", help=f"自由現金流佔營收比例：{fcf_revenue_ratio:.1%}，{fcf_revenue_text}")
            else:
                f1.metric("自由現金流/營收", "N/A")

            fcf_price_ratio = d.get("fcf_price_ratio", np.nan)
            if pd.notna(fcf_price_ratio):
                fcf_price_text = ":red[偏高，股價背後有強現金支撐]" if fcf_price_ratio > 0.08 else ":orange[合理]" if fcf_price_ratio > 0.02 else ":green[偏低，股價現金支撐較弱]"
                f2.metric("自由現金流/股價", f"{fcf_price_ratio:.1%}", help=f"自由現金流佔股價比例：{fcf_price_ratio:.1%}，{fcf_price_text}")
            else:
                f2.metric("自由現金流/股價", "N/A")

            fcf_growth = d.get("fcf_growth", np.nan)
            fcf_growth_pct = fcf_growth * 100 if pd.notna(fcf_growth) else np.nan
            if pd.notna(fcf_growth_pct):
                fcf_growth_text = ":red[高成長]" if fcf_growth_pct > 15 else ":orange[有成長]" if fcf_growth_pct > 0 else ":green[成長偏弱或衰退]"
                f3.metric("FCF成長率", f"{fcf_growth_pct:.1f}%", help=f"自由現金流年成長率：{fcf_growth_pct:.1f}%，{fcf_growth_text}")
            else:
                f3.metric("FCF成長率", "N/A")

            payout_ratio = d.get("payout_ratio", np.nan)
            payout_ratio_pct = payout_ratio * 100 if pd.notna(payout_ratio) else np.nan
            if pd.notna(payout_ratio_pct):
                payout_text = ":red[配發偏高，留存較少]" if payout_ratio_pct > 70 else ":orange[配發合理]" if payout_ratio_pct > 30 else ":green[配發偏低，留存較高]"
                f4.metric("盈餘配發率", f"{payout_ratio_pct:.1f}%", help=f"盈餘配發率：{payout_ratio_pct:.1f}%，{payout_text}")
            else:
                f4.metric("盈餘配發率", "N/A")

            st.write("說明：")
            st.write("• 若「自由現金流/股價」為正，表示每單位股價背後有實質現金支撐。")
            st.write("• 若「盈餘配發率」接近 100%，代表公司多數盈餘用於配股，現金流留存較少。")

        #  ========== 五、AI診斷 ==========
        st.markdown("---")
        st.header("🤖 五、AI診斷")
        api_status = st.secrets.get("GEMINI_API_KEY", "")
        col1, col2 = st.columns([1, 4])

        with col1:
            status_icon = "🟢 已連線" if api_status else "🔴 未連線"
            st.caption(f"**{status_icon}**")

        with col2:
            st.caption("**Gemini 2.5 Flash**")

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
        st.write("✅這是Raymond的台股深度分析，請輸入正確的股票代碼")
else:
    st.write("✅這是Raymond的台股深度分析，請輸入股票代碼後點擊左側『開始分析』")


