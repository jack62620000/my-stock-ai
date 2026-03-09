import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np


@st.cache_data(ttl=86400)
def get_all_names():
    names = {"2330": "台積電", "3131": "弘塑", "2317": "鴻海"}
    try:
        for url in [
            "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
            "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4",
        ]:
            df = pd.read_html(url)[0]
            for item in df[0]:
                if "　" in str(item):
                    p = str(item).split("　")
                    if len(p) >= 2:
                        names[p[0].strip()] = p[1].strip()
    except Exception:
        pass
    return names


@st.cache_data(ttl=6400)
def get_deep_analysis_data(code, name_map=None):
    if name_map is None:
        name_map = {}

    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period="1y")
            if hist.empty:
                continue

            info = ticker.info
            price = hist["Close"].iloc[-1]

            prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else price
            price_change = price - prev_close
            price_change_pct = (price_change / prev_close * 100) if prev_close else 0

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
            debt_to_equity = info.get("debtToEquity", 0) / 100.0
            current_ratio = info.get("currentRatio", np.nan)
            quick_ratio = info.get("quickRatio", np.nan)
            payout_ratio = info.get("payoutRatio", 0)

            try:
                financials = ticker.financials
                income = financials.loc["Net Income"] if "Net Income" in financials.index else pd.Series([np.nan])
                revenue = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else pd.Series([np.nan])

                net_income = income.iloc[0] if not income.empty and not pd.isna(income.iloc[0]) else np.nan
                net_rev = revenue.iloc[0] if not revenue.empty and not pd.isna(revenue.iloc[0]) else np.nan

                if "Gross Profit" in financials.index:
                    gp = financials.loc["Gross Profit"]
                    gross_profit_growth = (gp.iloc[0] - gp.iloc[1]) / gp.iloc[1] if len(gp) >= 2 and gp.iloc[1] else np.nan
                else:
                    gross_profit_growth = np.nan

                if "Operating Income" in financials.index:
                    oi = financials.loc["Operating Income"]
                    operating_income_growth = (oi.iloc[0] - oi.iloc[1]) / oi.iloc[1] if len(oi) >= 2 and oi.iloc[1] else np.nan
                else:
                    operating_income_growth = np.nan
            except Exception:
                financials = pd.DataFrame()
                net_income = np.nan
                net_rev = np.nan
                gross_profit_growth = np.nan
                operating_income_growth = np.nan

            try:
                balance_sheet = ticker.balance_sheet
                total_assets = balance_sheet.loc["Total Assets"].iloc[0] if "Total Assets" in balance_sheet.index else np.nan
                total_liabilities = balance_sheet.loc["Total Liabilities Net Minority Interest"].iloc[0] if "Total Liabilities Net Minority Interest" in balance_sheet.index else np.nan
                equity = balance_sheet.loc["Total Equity Gross Minority Interest"].iloc[0] if "Total Equity Gross Minority Interest" in balance_sheet.index else np.nan
                inventory = balance_sheet.loc["Total Inventory"].iloc[0] if "Total Inventory" in balance_sheet.index else np.nan
                cash = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0] if "Cash And Cash Equivalents" in balance_sheet.index else np.nan
                non_current_liabilities = balance_sheet.loc["Non-Current Liabilities"].iloc[0] if "Non-Current Liabilities" in balance_sheet.index else np.nan

                assets_growth = np.nan
                equity_growth = np.nan

                if "Total Assets" in balance_sheet.index:
                    assets = balance_sheet.loc["Total Assets"]
                    if len(assets) >= 2 and assets.iloc[1]:
                        assets_growth = (assets.iloc[0] - assets.iloc[1]) / assets.iloc[1]

                if "Total Equity Gross Minority Interest" in balance_sheet.index:
                    eq = balance_sheet.loc["Total Equity Gross Minority Interest"]
                    if len(eq) >= 2 and eq.iloc[1]:
                        equity_growth = (eq.iloc[0] - eq.iloc[1]) / eq.iloc[1]

                inv_asset_ratio = inventory / total_assets if pd.notna(total_assets) and total_assets not in [0, None] and pd.notna(inventory) else np.nan
                cash_asset_ratio = cash / total_assets if pd.notna(total_assets) and total_assets not in [0, None] and pd.notna(cash) else np.nan
                ncd_liabilities_ratio = (
                    non_current_liabilities / total_liabilities
                    if pd.notna(total_liabilities) and total_liabilities not in [0, None] and pd.notna(non_current_liabilities)
                    else np.nan
                )
            except Exception:
                balance_sheet = pd.DataFrame()
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
                free_cashflow = operating_cashflow - capex if pd.notna(operating_cashflow) else np.nan
                capex_to_cashflow = capex / operating_cashflow if pd.notna(operating_cashflow) and operating_cashflow not in [0, None] else np.nan
            except Exception:
                cashflow = pd.DataFrame()
                operating_cashflow = np.nan
                capex = np.nan
                free_cashflow = np.nan
                capex_to_cashflow = np.nan

            debt_ratio = total_liabilities / total_assets if pd.notna(total_assets) and total_assets not in [0, None] else np.nan
            net_income_growth = eps_growth
            cashflow_profit_ratio = operating_cashflow / net_income if pd.notna(net_income) and net_income not in [0, None] else np.nan
            fcf_revenue_ratio = free_cashflow / net_rev if pd.notna(net_rev) and net_rev not in [0, None] else np.nan
            fcf_price_ratio = free_cashflow / (price * 1e8) if pd.notna(free_cashflow) and pd.notna(price) and price not in [0, None] else np.nan
            fcf_growth = eps_growth

            div_per_share = info.get("dividendRate", np.nan)
            cash_dividend_yield = div_per_share / price if pd.notna(price) and price not in [0, None] and pd.notna(div_per_share) else np.nan
            book_value_growth = equity_growth

            # ===== 技術面 =====
            df = hist.copy()
            df["ma5"] = ta.sma(df["Close"], 5)
            df["ma10"] = ta.sma(df["Close"], 10)
            df["ma20"] = ta.sma(df["Close"], 20)
            df["ma60"] = ta.sma(df["Close"], 60)
            df["mv5"] = ta.sma(df["Volume"], 5)
            df["mv20"] = ta.sma(df["Volume"], 20)

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
            rsi = latest.get("rsi", 50)
            ma5 = latest.get("ma5", price)
            ma10 = latest.get("ma10", price)
            ma20 = latest.get("ma20", price)
            ma60 = latest.get("ma60", price)
            bb_upper = latest.get("布林上", np.nan)
            bb_lower = latest.get("布林下", np.nan)
            bb_mid = latest.get("布林中", np.nan)
            bias = latest.get("偏差", 0) * 100
            atr = latest.get("atr", 0)

            high_52 = df["High"].max()
            low_52 = df["Low"].min()
            position_52 = (price - low_52) / (high_52 - low_52) if pd.notna(high_52) and pd.notna(low_52) and high_52 != low_52 else np.nan

            return {
                "price": price,
                "price_change": price_change_pct,
                "price_change_amount": price_change,
                "name": name_map.get(code, code),
                "info": info,
                "ticker_symbol": f"{code}{suffix}",

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

                "df": df,
                "rsi": rsi,
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "ma60": ma60,
                "bias": bias,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "bb_mid": bb_mid,
                "atr": atr,
                "high_52": high_52,
                "low_52": low_52,
                "position_52": position_52,

                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "equity": equity,
                "capex": capex,
                "capex_to_cashflow": capex_to_cashflow,

                "gross_profit_growth": gross_profit_growth,
                "operating_income_growth": operating_income_growth,
                "assets_growth": assets_growth,
                "equity_growth": equity_growth,

                "inv_asset_ratio": inv_asset_ratio,
                "cash_asset_ratio": cash_asset_ratio,
                "ncd_liabilities_ratio": ncd_liabilities_ratio,

                "fcf_revenue_ratio": fcf_revenue_ratio,
                "fcf_price_ratio": fcf_price_ratio,
                "fcf_growth": fcf_growth,
                "cash_dividend_yield": cash_dividend_yield,
                "book_value_growth": book_value_growth,

                "financials": financials,
                "balance_sheet": balance_sheet,
                "cashflow": cashflow,
            }

        except Exception as e:
            st.warning(f"代碼 {code}{suffix} 錯誤：{e}")
            continue

    return None
