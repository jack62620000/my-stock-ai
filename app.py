import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import numpy as np

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

# 這一段 CSS 要貼在這裡，UI 開始之後、任何 st.header 之前
st.markdown("""
<style>
/* 1. 股票名稱大標題（用 st.title，會是 h1） */
h1 {
    color: #34495E !important;              /* 深灰 */
    font-size: 1.9rem !important;           /* 稍大一點 */
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;       /* 下方間距 */
    margin-top: 0.1rem !important;          /* 上方間距 */
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    letter-spacing: -0.02em !important;     /* 字距稍微縮緊 */
}

/* 2. 一、基本面、二、技術面、三、財務、四、現金流、五、AI診斷（用 st.header，會是 h2） */
h2 {
    color: #0095FF !important;              /* 藍色 */
    font-size: 1.7rem !important;
    font-weight: 600 !important;
    margin-top: 0.7rem !important;          /* 這一區塊往上多一點空 */
    margin-bottom: 0.3rem !important;       /* 下方空不要太大 */
    padding-top: 0.2rem !important;
    padding-bottom: 0.2rem !important;
}

/* 3. 盈利能力、成長性、財務結構、現金流品質、估值水準（用 st.subheader，會是 h3） */
h3 {
    color: #E67E22 !important;              /* 橘色 */
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    margin-top: 0.5rem !important;          /* 小區塊上緣空一點 */
    margin-bottom: 0.2rem !important;       /* 下緣緊一點 */
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    border-left: 4px solid #E67E22 !important;  /* 左側一條細色條，視覺上突顯 */
    padding-left: 0.5rem !important;
}

/* 4. 小數據（metrics 的數字與標籤、你用的 col1/col2 內容） */
/* 所有 metric 的數字（例如：9.8%、0.5% 這類） */
.metric-value {
    color: #2ECC71 !important;          /* 綠色，可改為 #E74C3C（紅）、#F39C12（橙） */
    font-size: 1.6rem !important;       /* 稍大一點，更明顯 */
    font-weight: 600 !important;
    margin-bottom: 0.1rem !important;   /* 數字與標籤之間的空 */
    line-height: 1.2 !important;
}

/* 所有 metric 的標籤（例如：毛利率、淨利率、EPS） */
.metric-label {
    color: #555555 !important;          /* 深灰，可改為 #888（更淺灰）、#0066ff（藍） */
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    margin-top: 0.1rem !important;      /* 標籤與上面內容的空 */
    line-height: 1.3 !important;
}

/* 一般段落文字（例如：你用的 st.write / st.markdown 說明文字） */
.element-container p {
    color: #333333 !important;          /* 深黑，可改成 #444444 */
    font-size: 0.95rem !important;
    line-height: 1.4 !important;
    margin: 0.2rem 0 !important;        /* 每個段落上下的空 */
}

/* 4. 你原本的「壓緊 header 間距」設定，保留在這，不會影響顏色 */
.st-emotion-cache-gi0tri {
    margin-bottom: 0.05rem !important;
    margin-top: 0.1rem !important;
    padding-top: 0.05rem !important;
    padding-bottom: 0.05rem !important;
    line-height: 1.1 !important;
}

</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="台股深度分析", layout="wide")
if code_input:
    with st.spinner(f"🔄 分析 {code_input} 資料中..."):
        d = get_deep_analysis_data(code_input)

    if d:
        col1, col2 = st.columns([1, 2])  # 左邊窄、右邊寬

        with col1:
            st.title(f"📊 {d.get('name', code_input)} ({code_input})")

        with col2:
            # 定義變數（放在 col2 內，避免縮排錯誤）
            price = d.get("price", 0)
            hist = d.get("df", pd.DataFrame())  # 用你已經有 df 這筆資料即可
            prev_close = (
                hist["Close"].iloc[-2] if len(hist) >= 2 and not pd.isna(hist["Close"].iloc[-2]) else price
            )
            change_price = price - prev_close
            change_percent = change_price / prev_close * 100 if prev_close else 0

            # 第一列：股價、漲跌、開盤、高點、低點
            t1, t2, t3, t4, t5, t6 = st.columns(6)
            t1.metric("即時股價：", f"{price:.1f}")
            t2.metric("漲跌額：", f"{change_price:+.1f}")
            t3.metric("漲跌幅：", f"{change_percent:+.1f}%")

            if not hist.empty:
                t4.metric("今日開盤：", f"{hist['Open'].iloc[-1]:.1f}")
                t5.metric("今日高點：", f"{hist['High'].iloc[-1]:.1f}")
                t6.metric("今日低點：", f"{hist['Low'].iloc[-1]:.1f}")

            st.markdown("---", unsafe_allow_html=True)

            # 第二列：RSI、MACD、成交量、量價
            r1, r2, r3, r4, r5, r6 = st.columns(6)
            rsi_now = d.get("rsi", 50)
            rsi_trend = ":red[偏高⭐️]" if rsi_now > 70 else":green[偏低⚠️]" if rsi_now < 30 else "中間"
            r1.metric("RSI 趨勢：", rsi_trend)
            r2.metric("即時 RSI：", f"{rsi_now:.1f}")

            df = d.get("df", pd.DataFrame())
            macd_line = df["macd"].iloc[-1] if "macd" in df.columns else 0.0
            macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else 0.0
            r3.metric("即時 MACD：", f"{macd_line:+.2f}")
            r4.metric("MACD 信號線：", f"{macd_signal:+.2f}")

            volume = df["Volume"].iloc[-1] if "Volume" in df.columns and not pd.isna(df["Volume"].iloc[-1]) else 0
            r5.metric("成交量(張)：", f"{int(volume / 1000):,}")

            # 量價判斷（只在有前一期資料時）
            volume_trend = "量價資訊不足"
            if len(df) >= 2:
                latest_vol = df["Volume"].iloc[-1]
                prev_vol = df["Volume"].iloc[-2]
                if price > prev_close and latest_vol > prev_vol:
                    volume_trend = "價漲量增"
                else:
                    volume_trend = "價漲量縮"
            r6.metric("盤中量價：", volume_trend)

#  ========== 一、基本面（公司賺不賺錢）==========
        st.header("📌 一、基本面：公司賺不賺錢")
        with st.container(border=True):
            # 盈利能力
            st.subheader("盈利能力")
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            # 毛利率
            gp = d.get("gross_profit", 0) * 100
            if gp > 30:
                gp_text = ":red[偏高⭐️]"
            elif gp >= 20:
                gp_text = ":orange[合理🟡]"
            else:
                gp_text = ":green[偏低⚠️]"
            c1.metric("毛利率", f"{gp:.1f}% ({gp_text})",
              help=f"毛利率：{gp:.1f}% ({gp_text})\n毛利率高代表公司定價能力與成本控管較強。")
            # 淨利率
            nm = d.get("net_margin", 0) * 100
            if nm > 8:
                nm_text = ":red[偏高⭐️]"
            elif nm >= 4:
                nm_text = ":orange[合理🟡]"
            else:
                nm_text = ":green[偏低⚠️]"
            c2.metric("淨利率", f"{nm:.1f}% ({nm_text})",
              help=f"淨利率：{nm:.1f}% ({nm_text})\n淨利率高代表公司整體賺錢效率較佳。")
            # 營業利益率
            om = d.get("op_margin", 0) * 100
            if om > 10:
                om_text = ":red[偏高⭐️]"
            elif om >= 5:
                om_text = ":orange[合理🟡]"
            else:
                om_text = ":green[偏低⚠️]"
            c3.metric("營業利益率", f"{om:.1f}% ({om_text})",
              help=f"營業利益率：{om:.1f}% ({om_text})\n主要反映本業的獲利穩定度。")
            # EPS
            eps = d.get("eps", 0)
            if eps > 3:
                eps_text = ":red[偏高⭐️]"
            elif eps >= 1.5:
                eps_text = ":orange[合理🟡]"
            else:
                eps_text = ":green[偏低⚠️]"
            c4.metric("EPS", f"{eps:.2f} ({eps_text})",
              help=f"EPS：{eps:.2f} ({eps_text})\n每股盈餘，代表公司為股東賺多少錢。")
            # ROE
            roe = d.get("roe", 0) * 100
            if roe > 15:
                roe_text = ":red[偏高⭐️]"
            elif roe >= 10:
                roe_text = ":orange[合理🟡]"
            else:
                roe_text =":green[偏低⚠️]"
            c5.metric("ROE", f"{roe:.1f}% ({roe_text})",
              help=f"ROE：{roe:.1f}% ({roe_text})\n權益報酬率，衡量股東資本的獲利效率。")
            # ROA
            roa = d.get("roa", 0) * 100
            if roa > 8:
                roa_text = ":red[偏高⭐️]"
            elif roa >= 4:
                roa_text = ":orange[合理🟡]"
            else:
                roa_text =":green[偏低⚠️]"
            c6.metric("ROA", f"{roa:.1f}% ({roa_text})",
              help=f"ROA：{roa:.1f}% ({roa_text})\n資產報酬率，衡量整體資產賺錢能力。")
            # EPS 成長率
            eps_growth = d.get("eps_growth", 0) * 100
            if eps_growth > 10:
                eps_growth_text = ":red[偏高⭐️]"
            elif eps_growth >= 0:
                eps_growth_text = ":orange[合理🟡]"
            else:
                eps_growth_text =":green[偏低⚠️]"
            c7.metric("EPS 成長率", f"{eps_growth:.1f}% ({eps_growth_text})",
              help=f"EPS 成長率：{eps_growth:.1f}% ({eps_growth_text})\nEPS 的成長趨勢，看未來盈餘是否逐季／逐年增長。")
     
            # 成長性
            st.subheader("成長性")
            g1, g2, g3, g4, g5, g6, g7 = st.columns(7)
            # 營收成長率
            rev_growth = d.get("rev_growth", 0) * 100
            if rev_growth > 10:
                rev_text = ":red[偏高⭐️]"
            elif rev_growth >= 0:
                rev_text = ":orange[合理🟡]"
            else:
                rev_text =":green[偏低⚠️]"
            g1.metric("營收成長率", f"{rev_growth:.1f}% ({rev_text})",
              help=f"營收成長率：{rev_growth:.1f}% ({rev_text})\n衡量公司業務規模是否在擴張。")
            # EPS 成長率
            eps_growth = d.get("eps_growth", 0) * 100
            if eps_growth > 10:
                eps_growth_text = ":red[偏高⭐️]"
            elif eps_growth >= 0:
                eps_growth_text = ":orange[合理🟡]"
            else:
                eps_growth_text =":green[偏低⚠️]"
            g2.metric("EPS 成長率", f"{eps_growth:.1f}% ({eps_growth_text})",
              help=f"EPS 成長率：{eps_growth:.1f}% ({eps_growth_text})\n每股盈餘的成長是否穩定。")
            # 淨利成長率
            net_income_growth = d.get("net_income_growth", 0) * 100
            if net_income_growth > 10:
                net_income_text = ":red[偏高⭐️]"
            elif net_income_growth >= 0:
                net_income_text = ":orange[合理🟡]"
            else:
                net_income_text =":green[偏低⚠️]"
            g3.metric("淨利成長率", f"{net_income_growth:.1f}% ({net_income_text})",
              help=f"淨利成長率：{net_income_growth:.1f}% ({net_income_text})\n淨利的成長趨勢，代表獲利品質的穩定度。")
            # 毛利成長率
            gross_profit_growth = d.get("gross_profit_growth", 0) * 100
            if gross_profit_growth > 10:
                gross_profit_text = ":red[偏高⭐️]"
            elif gross_profit_growth >= 0:
                gross_profit_text = ":orange[合理🟡]"
            else:
                gross_profit_text =":green[偏低⚠️]"
            g4.metric("毛利成長率", f"{gross_profit_growth:.1f}% ({gross_profit_text})",
              help=f"毛利成長率：{gross_profit_growth:.1f}% ({gross_profit_text})\n毛利的成長，是淨利成長的先行指標。")
            # 營業利益成長率
            op_income_growth = d.get("operating_income_growth", 0) * 100
            if op_income_growth > 10:
                op_income_text = ":red[偏高⭐️]"
            elif op_income_growth >= 0:
                op_income_text = ":orange[合理🟡]"
            else:
                op_income_text =":green[偏低⚠️]"
            g5.metric("營業利益成長率", f"{op_income_growth:.1f}% ({op_income_text})",
              help=f"營業利益成長率：{op_income_growth:.1f}% ({op_income_text})\n本業利潤的成長狀況。")
            # 資產成長率
            assets_growth = d.get("assets_growth", 0) * 100
            if assets_growth > 5:
                assets_text = ":red[偏高⭐️]"
            elif assets_growth >= 0:
                assets_text = ":orange[合理🟡]"
            else:
                assets_text =":green[偏低⚠️]"
            g6.metric("資產成長率", f"{assets_growth:.1f}% ({assets_text})",
              help=f"資產成長率：{assets_growth:.1f}% ({assets_text})\n公司資產規模是否在擴張。")
            # 權益成長率
            equity_growth = d.get("equity_growth", 0) * 100
            if equity_growth > 8:
                equity_text = ":red[偏高⭐️]"
            elif equity_growth >= 0:
                equity_text = ":orange[合理🟡]"
            else:
                equity_text =":green[偏低⚠️]"
            g7.metric("權益成長率", f"{equity_growth:.1f}% ({equity_text})",
              help=f"權益成長率：{equity_growth:.1f}% ({equity_text})\n股東權益的成長，代表公司累積盈餘是否在增加。")

            # 財務結構
            st.subheader("財務結構")
            f1, f2, f3, f4, f5, f6, f7 = st.columns(7)
            # 負債比率
            debt_ratio = d.get("debt_ratio", 0) * 100
            if debt_ratio < 50:
                debt_text =":red[低風險⭐️]"
            elif debt_ratio <= 70:
                debt_text = ":orange[中等🟡]"
            else:
                debt_text = ":green[高風險⚠️]"
            f1.metric("負債比率", f"{debt_ratio:.1f}% ({debt_text})",
              help=f"負債比率：{debt_ratio:.1f}% ({debt_text})\n越高代表公司負債壓力越大。")
            # 負債／股東權益
            debt_to_equity = d.get("debt_to_equity", 0) * 100
            if debt_to_equity < 50:
                dte_text =":red[低風險⭐️]"
            elif debt_to_equity <= 100:
                dte_text = ":orange[中等🟡]"
            else:
                dte_text = ":green[高風險⚠️]"
            f2.metric("負債/股東權益", f"{debt_to_equity:.1f}% ({dte_text})",
              help=f"負債/股東權益：{debt_to_equity:.1f}% ({dte_text})\n衡量公司使用借貸槓桿的程度。")
            # 流動比率
            current_ratio = d.get("current_ratio", 0)
            if current_ratio > 2:
                current_text = ":red[偏高⭐️]"
            elif current_ratio >= 1:
                current_text = ":orange[合理🟡]"
            else:
                current_text =":green[偏低⚠️]"
            f3.metric("流動比率", f"{current_ratio:.2f} ({current_text})",
              help=f"流動比率：{current_ratio:.2f} ({current_text})\n衡量公司短期償債能力，一般以 1.5～2 倍為佳。")
            # 速動比率
            quick_ratio = d.get("quick_ratio", 0)
            if quick_ratio > 1.5:
                quick_text = ":red[偏高⭐️]"
            elif quick_ratio >= 0.7:
                quick_text = ":orange[合理🟡]"
            else:
                quick_text =":green[偏低⚠️]"
            f4.metric("速動比率", f"{quick_ratio:.2f} ({quick_text})",
              help=f"速動比率：{quick_ratio:.2f} ({quick_text})\n扣除存貨後的短期償債能力指標，愈高愈好。")
            # 存貨佔資產比
            inv_asset_ratio = d.get("inv_asset_ratio", 0)
            if inv_asset_ratio > 0.5:
                inv_text =":green[偏高⚠️]"
            elif inv_asset_ratio >= 0.2:
                inv_text = ":orange[合理🟡]"
            else:
                inv_text = ":red[偏低⭐️]"
            f5.metric("存貨佔資產比", f"{inv_asset_ratio:.1%} ({inv_text})",
              help=f"存貨佔資產比：{inv_asset_ratio:.1%} ({inv_text})\n存貨過高可能有跌價與庫存風險。")
            # 現金佔資產比
            cash_asset_ratio = d.get("cash_asset_ratio", 0)
            if cash_asset_ratio > 0.1:
                cash_text = ":red[偏高⭐️]"
            elif cash_asset_ratio >= 0.05:
                cash_text = ":orange[合理🟡]"
            else:
                cash_text =":green[偏低⚠️]"
            f6.metric("現金佔資產比", f"{cash_asset_ratio:.1%} ({cash_text})",
              help=f"現金佔資產比：{cash_asset_ratio:.1%} ({cash_text})\n愈高代表公司現金儲備愈充裕。")
            # 非流動負債占負債比
            ncd_liabilities_ratio = d.get("ncd_liabilities_ratio", 0)
            if ncd_liabilities_ratio >0.8:
                ncd_text =":green[偏高⚠️]"
            elif ncd_liabilities_ratio >= 0.5:
                ncd_text = ":orange[合理🟡]"
            else:
                ncd_text = ":red[偏低⭐️]"
            f7.metric("非流動負債占負債比", f"{ncd_liabilities_ratio:.1%} ({ncd_text})",
              help=f"非流動負債占負債比：{ncd_liabilities_ratio:.1%} ({ncd_text})\n長期負債佔比愈高，財務結構愈偏長期化，但也可能增加利息支出壓力。")

            # 現金流品質
            st.subheader("現金流品質")
            ca1, ca2, ca3, ca4, ca5, ca6, ca7 = st.columns(7)
            ca1.metric("營業現金流：", f"{d.get('operating_cashflow', 0) / 1e8:.1f}億")
            ca2.metric("自由現金流(FCF)：", f"{d.get('free_cashflow', 0) / 1e8:.1f}億")
            # 現金流／淨利
            cashflow_profit_ratio = d.get("cashflow_profit_ratio", 0)
            if cashflow_profit_ratio > 1:
                cfp_text = ":red[偏高⭐️]"
            elif cashflow_profit_ratio >= 0.7:
                cfp_text = ":orange[合理🟡]"
            else:
                cfp_text =":green[偏低⚠️]"
            ca3.metric("現金流/淨利", f"{cashflow_profit_ratio:.2f} ({cfp_text})",
              help=f"現金流/淨利：{cashflow_profit_ratio:.2f} ({cfp_text})\n>1 代表現金流比淨利佳，公司獲利品質較好。")
            # FCF/營收
            fcf_revenue_ratio = d.get("fcf_revenue_ratio", 0)
            if fcf_revenue_ratio > 0.15:
                fcf_rev_text = ":red[偏高⭐️]"
            elif fcf_revenue_ratio >= 0.05:
                fcf_rev_text = ":orange[合理🟡]"
            else:
                fcf_rev_text =":green[偏低⚠️]"
            ca4.metric("FCF/營收", f"{fcf_revenue_ratio:.1%} ({fcf_rev_text})",
              help=f"FCF/營收：{fcf_revenue_ratio:.1%} ({fcf_rev_text})\n自由現金流佔營收的比例，愈高代表現金生成力愈強。")
            # FCF/股價
            fcf_price_ratio = d.get("fcf_price_ratio", 0)
            if fcf_price_ratio > 0.05:
                fcf_price_text = ":red[偏高⭐️]"
            elif fcf_price_ratio >= 0.01:
                fcf_price_text = ":orange[合理🟡]"
            else:
                fcf_price_text =":green[偏低⚠️]"
            ca5.metric("FCF/股價", f"{fcf_price_ratio:.1%} ({fcf_price_text})",
              help=f"FCF/股價：{fcf_price_ratio:.1%} ({fcf_price_text})\n每單位股價背後有多少自由現金流支撐。")
            # FCF 成長率
            fcf_growth = d.get("fcf_growth", 0) * 100
            if fcf_growth > 10:
                fcf_growth_text = ":red[偏高⭐️]"
            elif fcf_growth >= 0:
                fcf_growth_text = ":orange[合理🟡]"
            else:
                fcf_growth_text =":green[偏低⚠️]"
            ca6.metric("FCF 成長率", f"{fcf_growth:.1f}% ({fcf_growth_text})",
               help=f"FCF 成長率：{fcf_growth:.1f}% ({fcf_growth_text})\n自由現金流的年成長率，代表現金生成力是否在提升。")
            # 資本支出／營業現金流
            capex_to_cashflow = d.get("capex_to_cashflow", 0)
            if capex_to_cashflow > 1.0:
                capex_cf_text = ":red[偏高⭐️]"
            elif capex_to_cashflow >= 0.5:
                capex_cf_text = ":orange[合理🟡]"
            else:
                capex_cf_text =":green[偏低⚠️]"
            ca7.metric("資本支出/營業現金流", f"{capex_to_cashflow:.2f} ({capex_cf_text})",
               help=f"資本支出/營業現金流：{capex_to_cashflow:.2f} ({capex_cf_text})\n>1 代表資本支出比營業現金流還多，可能有現金流壓力。")

            # 估值水準
            st.subheader("估值水準")
            v1, v2, v3, v4, v5, v6, v7 = st.columns(7)
            # 本益比(P/E)
            pe = d.get("pe", 0)
            if pe > 20:
                pe_text =":green[偏高估⚠️]"
            elif pe >= 10:
                pe_text = ":orange[合理🟡]"
            else:
                pe_text = ":red[偏低估⭐️]"
            v1.metric("本益比(P/E)", f"{pe:.1f}x ({pe_text})",
              help=f"本益比(P/E)：{pe:.1f}x ({pe_text})\n偏高代表可能較貴，偏低代表可能較便宜。")
            # 股價淨值比(P/B)
            pb = d.get("pb", 0)
            if pb > 3:
                pb_text =":green[偏高估⚠️]"
            elif pb >= 1:
                pb_text = ":orange[合理🟡]"
            else:
                pb_text = ":red[偏低估⭐️]"
            v2.metric("股價淨值比(P/B)", f"{pb:.1f}x ({pb_text})",
              help=f"股價淨值比(P/B)：{pb:.1f}x ({pb_text})\n偏高代表可能高估，偏低代表可能低估，但與產業特性有關。")
            # PEG
            peg = d.get("peg", 0)
            if peg > 1.5:
                peg_text =":green[偏高估⚠️]"
            elif peg >= 1.0:
                peg_text = ":orange[合理🟡]"
            else:
                peg_text = ":red[偏低估⭐️]"
            v3.metric("PEG", f"{peg:.1f} ({peg_text})",
              help=f"PEG：{peg:.1f} ({peg_text})\nPEG 用成長率調整本益比，愈接近 1 愈合理。")
            # 股利殖利率
            div_yield = d.get("dividend_yield", 0) * 100
            if div_yield > 5:
                div_text = ":red[偏高⭐️]"
            elif div_yield >= 2:
                div_text = ":orange[合理🟡]"
            else:
                div_text =":green[偏低⚠️]"
            v4.metric("股利殖利率", f"{div_yield:.1f}% ({div_text})",
              help=f"股利殖利率：{div_yield:.1f}% ({div_text})\n偏高代表現金回報較高，但要注意是否可持續。")
            # 盈餘配發率
            payout_ratio = d.get("payout_ratio", 0) * 100
            if payout_ratio > 70:
                payout_text = ":red[偏高⭐️]"
            elif payout_ratio >= 30:
                payout_text = ":orange[合理🟡]"
            else:
                payout_text =":green[偏低⚠️]"
            v5.metric("盈餘配發率", f"{payout_ratio:.1f}% ({payout_text})",
              help=f"盈餘配發率：{payout_ratio:.1f}% ({payout_text})\n偏高代表多數盈餘用於配股，偏低則代表多數盈餘用於再投資。")
            # 現金股利報酬率
            cash_dividend_yield = d.get("cash_dividend_yield", 0) * 100
            if cash_dividend_yield > 5:
                cd_text = ":red[偏高⭐️]"
            elif cash_dividend_yield >= 2:
                cd_text = ":orange[合理🟡]"
            else:
                cd_text =":green[偏低⚠️]"
            v6.metric("現金股利報酬率", f"{cash_dividend_yield:.1f}% ({cd_text})",
              help=f"現金股利報酬率：{cash_dividend_yield:.1f}% ({cd_text})\n多少現金股利相對於股價的比例。")
            # 帳面價值成長率
            book_value_growth = d.get("book_value_growth", 0) * 100
            if book_value_growth > 8:
                bv_text = ":red[偏高⭐️]"
            elif book_value_growth >= 0:
                bv_text = ":orange[合理🟡]"
            else:
                bv_text =":green[偏低⚠️]"
            v7.metric("帳面價值成長率", f"{book_value_growth:.1f}% ({bv_text})",
              help=f"帳面價值成長率：{book_value_growth:.1f}% ({bv_text})\n代表公司帳面資產與淨值的成長速度。")
            

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
                price = d.get("price", price)
                # MA5
                ma5 = latest.get("ma5", price)
                if price > ma5:
                    ma5_text = ":red[多頭]"
                else:
                    ma5_text = ":green[空頭]"
                t1.metric("MA5", f"{ma5:.1f} ({ma5_text})",
                  help=f"MA5：{ma5:.1f} ({ma5_text})\n5日均線，股價在均線上方為多頭。")
                # MA20
                ma20 = latest.get("ma20", price)
                if price > ma20:
                    ma20_text = ":red[多頭]"
                else:
                    ma20_text = ":green[空頭]"
                t1.metric("MA20", f"{ma20:.1f} ({ma20_text})",
                  help=f"MA20：{ma20:.1f} ({ma20_text})\n20日均線，中期趨勢判斷。")
                # MA60
                ma60 = latest.get("ma60", price)
                if price > ma60:
                    ma60_text = ":red[多頭]"
                else:
                    ma60_text = ":green[空頭]"
                t1.metric("MA60", f"{ma60:.1f} ({ma60_text})",
                  help=f"MA60：{ma60:.1f} ({ma60_text})\n60日均線，長期趨勢判斷。")
                bias = d.get("bias", 0)
                if bias > 10:
                    bias_text = ":red[偏離太大⚠️]"
                elif bias < -10:
                    bias_text =":green[偏離太小⭐️]"
                else:
                    bias_text = ":orange[合理🟡]"
                t1.metric("乖離率", f"{bias:.1f}% ({bias_text})",
                  help=f"乖離率：{bias:.1f}% ({bias_text})\n股價偏離20日均線的百分比，±10%內為合理範圍。")

                # 動能與強度
                t2.subheader("動能與強度")
                rsi = d.get("rsi", 50)
                if rsi > 70:
                    rsi_text = "過熱🔴"
                elif rsi < 30:
                    rsi_text = "過冷🟢"
                else:
                    rsi_text = "中性🟡"
                t2.metric("RSI", f"{rsi:.1f} ({rsi_text})",
                  help=f"RSI：{rsi:.1f} ({rsi_text})\n相對強弱指標，>70過熱、<30過冷。")
                macd_line = df["macd"].iloc[-1] if "macd" in df.columns else 0.0
                macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else 0.0
                if macd_line > macd_signal:
                    macd_text = ":red[多頭]"
                else:
                    macd_text = ":green[空頭]"
                t2.metric("MACD 本體", f"{macd_line:+.2f} ({macd_text})",
                            help="MACD 本體：{macd_line:+.2f} ({macd_text})\nMACD線高於信號線為多頭訊號。")
                if macd_signal > 0:
                    signal_text = ":red[多頭]"
                else:
                    signal_text = ":green[空頭]"
                t2.metric("MACD 信號線", f"{macd_signal:+.2f} ({signal_text})",
                            help="MACD 信號線：{macd_signal:+.2f} ({signal_text})\n信號線>0為多頭趨勢。")
                # 波動與區間
                t3.subheader("波動與區間")
                bb_upper = d.get("bb_upper", 0)
                bb_mid = d.get("bb_mid", 0)
                bb_lower = d.get("bb_lower", 0)
                if price > bb_upper:
                    bb_upper_text = ":green[多頭強、偏積極🟢]"
                elif price < bb_lower:
                    bb_upper_text =":red[多頭弱、偏保守🔴]"
                else:
                    bb_upper_text = ":orange[合理🟡]"
                t3.metric("布林上軌", f"{bb_upper:.1f} ({bb_upper_text})",
                          help="布林上軌：{bb_upper:.1f} ({bb_upper_text})\n股價突破上軌代表強勢。")
                t3.metric("布林中軌", f"{bb_mid:.1f}",
                          help="布林中軌：{bb_mid:.1f}\n20日移動平均線。")
                if price < bb_lower:
                    bb_lower_text =":red[多頭弱、偏保守🔴]"
                else:
                    bb_lower_text = ":orange[偏中風險🟡]"
                t3.metric("布林下軌", f"{bb_lower:.1f} ({bb_lower_text})",
                  help=f"布林下軌：{bb_lower:.1f} ({bb_lower_text})\n股價跌破下軌代表弱勢。")
                # （52週高/低）
                high_52 = d.get("52高", 0)
                low_52 = d.get("52低", 0)
                if price > high_52:
                    high_text = ":green[52週新高(多頭強、但也偏貴)]"
                else:
                    high_text = ":orange[未新高🟡]"
                t3.metric("52週高價", f"{high_52:.1f} ({high_text})",
                  help=f"52週高價：{high_52:.1f} ({high_text})\n過去52週最高價。")
                if price < low_52:
                    low_text = ":red[52週新低(多頭弱、但也偏便宜)]"
                else:
                    low_text = ":orange[未新低🟡]"
                t3.metric("52週低價", f"{low_52:.1f} ({low_text})",
                  help=f"52週低價：{low_52:.1f} ({low_text})\n過去52週最低價。")
                std_20 = df["std"].iloc[-1] if "std" in df.columns else 0.0
                if std_20 > 3:
                    std_text = ":green[波動大、風險高]"
                elif std_20 > 1:
                    std_text = ":orange[合理🟡]"
                else:
                    std_text =":red[波動小、風險低]"
                t3.metric("標準差(20日)", f"{std_20:.2f} ({std_text})",
                  help=f"標準差(20日)：{std_20:.2f} ({std_text})\n衡量股價波動程度。")
                atr = d.get("atr", 0)
                if atr > 3:
                    atr_text = ":green[波動大、風險高]"
                elif atr > 1:
                    atr_text = ":orange[合理🟡]"
                else:
                    atr_text =":red[波動小、風險低]"
                t3.metric("ATR(14日)", f"{atr:.2f} ({atr_text})",
                  help=f"ATR(14日)：{atr:.2f} ({atr_text})\n平均真實波幅，衡量每日波動範圍。")

                # 成交量與量價關係
                # 成交量與量價關係
                t4.subheader("成交量與量價關係")
                t4.metric("今日成交量", f"{int(latest['Volume'] / 1000):,} 張",
                  help=f"今日成交量：{int(latest['Volume'] / 1000):,} 張\n成交量放大代表市場關注度高。")
                price_change_pct = d.get("price_change", 0)   # 今日漲跌幅 (%)
                volume = latest['Volume']
                avg_volume = df["Volume"][-30:].mean() if len(df) >= 30 else 0   # 用 30 日平均量
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
                t4.metric("量價關係", vol_price_text,
                  help=f"量價關係：{vol_price_text}\n價漲量增最健康，價跌量增最危險。")


        #  ========== 三、財務與資本結構（公司資本是否健康）==========
        st.header("🏦 三、財務與資本結構：公司資本是否健康")
        with st.container(border=True):
            s1, s2, s3, s4 = st.columns(4)
            total_assets = d.get("total_assets", 0)
            if total_assets / 1e9 > 100:
                total_assets_text = ":red[資產偏高，公司規模大]"
            elif total_assets / 1e9 > 20:
                total_assets_text = ":orange[資產合理]"
            else:
                total_assets_text = ":green[資產偏小，規模較小]"
            s1.metric("總資產", f"{total_assets / 1e9:.1f} 億", help=f"總資產：{total_assets / 1e9:.1f} 億 元，{total_assets_text}")
            total_liabilities = d.get("total_liabilities", 0)
            if total_liabilities / 1e9 > 60:
                total_liabilities_text = ":red[負債偏高]"
            elif total_liabilities / 1e9 > 10:
                total_liabilities_text = ":orange[負債合理]"
            else:
                total_liabilities_text = ":green[負債偏低]"
            s2.metric("總負債", f"{total_liabilities / 1e9:.1f} 億", help=f"總負債：{total_liabilities / 1e9:.1f} 億 元，{total_liabilities_text}")
            equity = d.get("equity", 0)
            if equity / 1e9 > 40:
                equity_text = ":red[權益偏高]"
            elif equity / 1e9 > 5:
                equity_text = ":orange[權益合理]"
            else:
                equity_text = ":green[權益偏低]"
            s3.metric("股東權益", f"{equity / 1e9:.1f} 億", help=f"股東權益：{equity / 1e9:.1f} 億 元，{equity_text}")
            capex = d.get("capex", 0)
            if capex / 1e8 > 20:
                capex_text = ":red[資本支出偏高]"
            elif capex / 1e8 > 3:
                capex_text = ":orange[資本支出合理]"
            else:
                capex_text = ":green[資本支出偏低]"
            s4.metric("資本支出(Capex)", f"{capex / 1e8:.1f} 億", help=f"資本支出：{capex / 1e8:.1f} 億 元，{capex_text}")
            capex_to_cashflow = d.get("capex_to_cashflow", 0)
            if capex_to_cashflow > 1.0:
                ctc_text = ":red[偏高，資本支出占營業現金流過高]"
            elif capex_to_cashflow > 0.5:
                ctc_text = ":orange[合理，資本支出適中]"
            else:
                ctc_text = ":green[偏低，資本支出偏小]"
            st.metric("資本支出/營業現金流", f"{capex_to_cashflow:.2f}", help=f"資本支出佔營業現金流比例：{capex_to_cashflow:.2%}，{ctc_text}")

        #  ========== 四、現金流與股利（現金能不能穩定入袋）==========
        st.header("💵 四、現金流與股利：現金能不能穩定入袋")
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns(4)
            fcf_revenue_ratio = d.get("fcf_revenue_ratio", 0)
            if fcf_revenue_ratio > 0.20:
                fcf_revenue_text = ":red[偏高，每單位營收有高現金]"
            elif fcf_revenue_ratio > 0.05:
                fcf_revenue_text = ":orange[合理]"
            else:
                fcf_revenue_text = ":green[偏低，營收現金化能力較弱]"
            f1.metric("自由現金流/營收", f"{fcf_revenue_ratio:.1%}", help=f"自由現金流佔營收比例：{fcf_revenue_ratio:.1%}，{fcf_revenue_text}")
            fcf_price_ratio = d.get("fcf_price_ratio", 0)
            if fcf_price_ratio > 0.08:
                fcf_price_text = ":red[偏高，股價背後有強現金支撐]"
            elif fcf_price_ratio > 0.02:
                fcf_price_text = ":orange[合理]"
            else:
                fcf_price_text = ":green[偏低，股價現金支撐較弱]"
            f2.metric("自由現金流/股價", f"{fcf_price_ratio:.1%}", help=f"自由現金流佔股價比例：{fcf_price_ratio:.1%}，{fcf_price_text}")
            fcf_growth = d.get("fcf_growth", 0) * 100
            if fcf_growth > 15:
                fcf_growth_text = ":red[高成長]"
            elif fcf_growth > 0:
                fcf_growth_text = ":orange[有成長]"
            else:
                fcf_growth_text = ":green[成長偏弱或衰退]"
            f3.metric("FCF成長率", f"{fcf_growth:.1f}%", help=f"自由現金流年成長率：{fcf_growth:.1f}%，{fcf_growth_text}")
            payout_ratio = d.get("payout_ratio", 0) * 100
            if payout_ratio > 70:
                payout_text = ":red[配發偏高，留存較少]"
            elif payout_ratio > 30:
                payout_text = ":orange[配發合理]"
            else:
                payout_text = ":green[配發偏低，留存較高]"
            f4.metric("盈餘配發率", f"{payout_ratio:.1f}%", help=f"盈餘配發率：{payout_ratio:.1f}%，{payout_text}")
            st.write("說明：")
            st.write("• 若「自由現金流/股價」為正，表示每單位股價背後有實質現金支撐。")
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
        st.write("✅這是Raymond的台股深度分析，請輸入正確的股票代碼")



































