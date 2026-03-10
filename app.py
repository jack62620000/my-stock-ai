import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
import urllib3
import streamlit as st
import google.generativeai as genai
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================
# Streamlit 基本設定
# =========================
st.set_page_config(page_title="台股深度分析", layout="wide")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mops.twse.com.tw/",
}


# =========================
# 共用工具
# =========================
def safe_float(x):
    try:
        if x is None:
            return np.nan
        if isinstance(x, str):
            x = (
                x.replace(",", "")
                .replace("%", "")
                .replace("(", "-")
                .replace(")", "")
                .strip()
            )
            if x in ["", "-", "--", "N/A", "nan", "None"]:
                return np.nan
        return float(x)
    except Exception:
        return np.nan


def pct_text(v, digits=1):
    if pd.isna(v):
        return "N/A"
    return f"{v * 100:.{digits}f}%"


def num_text(v, digits=1):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def big_text(v, unit="億", divisor=1e8, digits=1):
    if pd.isna(v):
        return "N/A"
    return f"{v / divisor:.{digits}f}{unit}"


def calc_growth(cur, prev):
    if pd.notna(cur) and pd.notna(prev) and prev != 0:
        return (cur - prev) / prev
    return np.nan


def roc_to_ad_date(roc_date_str: str):
    yy, mm, dd = roc_date_str.split("/")
    return pd.Timestamp(f"{int(yy)+1911}-{int(mm):02d}-{int(dd):02d}")


def ad_to_roc(year: int):
    return year - 1911


def keyword_value(mapping: dict, keywords):
    for k, v in mapping.items():
        for kw in keywords:
            if kw in k:
                return v
    return np.nan


def map_from_statement_table(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}

    result = {}
    for _, row in df.iterrows():
        try:
            key = str(row.iloc[0]).strip()
            if not key or key == "nan":
                continue
            val = np.nan
            for item in row.iloc[1:].tolist():
                f = safe_float(item)
                if pd.notna(f):
                    val = f
                    break
            result[key] = val
        except Exception:
            continue
    return result


def pick_company_table(tables, code):
    code = str(code)
    for tb in tables:
        try:
            text = "\n".join(tb.astype(str).fillna("").stack().tolist())
            if code in text:
                return tb.copy()
        except Exception:
            continue
    return pd.DataFrame()


# =========================
# 股票基本清單
# =========================
@st.cache_data(ttl=86400)
def get_all_names():
    names = {
        "2330": {"name": "台積電", "market": "sii"},
        "2317": {"name": "鴻海", "market": "sii"},
        "3131": {"name": "弘塑", "market": "otc"},
    }

    source_map = [
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "sii"),
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", "otc"),
    ]

    for url, market in source_map:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            r.raise_for_status()
            tables = pd.read_html(r.text)
            if not tables:
                continue
            df = tables[0]
            for item in df.iloc[:, 0].astype(str):
                if "　" in item:
                    p = item.split("　")
                    if len(p) >= 2:
                        code = p[0].strip()
                        name = p[1].strip()
                        if code.isdigit():
                            names[code] = {"name": name, "market": market}
        except Exception:
            continue

    return names


NAME_MAP = get_all_names()


def get_stock_meta(code):
    return NAME_MAP.get(code, {"name": code, "market": None})


# =========================
# 股價：TWSE / TPEX
# =========================
def get_twse_month(code: str, yyyymm01: str) -> pd.DataFrame:
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    params = {
        "response": "json",
        "date": yyyymm01,
        "stockNo": code,
    }

    try:
        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20,
            verify=False
        )
        r.raise_for_status()

        text = r.text.strip()

        # 偵錯：看實際回了什麼
        st.caption(f"TWSE status={r.status_code}")
        st.caption(f"TWSE content-type={r.headers.get('Content-Type', '')}")
        st.caption(f"TWSE 前80字={text[:80]}")

        # 空內容
        if not text:
            return pd.DataFrame()

        # 不是 JSON 格式開頭
        if not (text.startswith("{") or text.startswith("[")):
            return pd.DataFrame()

        # 只有在看起來像 JSON 時才解析
        js = requests.models.complexjson.loads(text)

        if js.get("stat") != "OK":
            return pd.DataFrame()

        rows = []
        for row in js.get("data", []):
            try:
                rows.append({
                    "Date": roc_to_ad_date(row[0]),
                    "Open": safe_float(row[3]),
                    "High": safe_float(row[4]),
                    "Low": safe_float(row[5]),
                    "Close": safe_float(row[6]),
                    "Volume": safe_float(row[1]),
                })
            except Exception:
                continue

        return pd.DataFrame(rows)

    except Exception as e:
        st.caption(f"get_twse_month 例外：{str(e)}")
        return pd.DataFrame()


def get_tpex_month(code: str, roc_year_month: str) -> pd.DataFrame:
    # 例: 114/03
    url = "https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes"
    params = {
        "id": code,
        "date": roc_year_month,
        "response": "json",
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=20, verify=False)
    r.raise_for_status()
    js = r.json()

    tables = js.get("tables", [])
    if not tables:
        return pd.DataFrame()

    data = tables[0].get("data", [])
    rows = []
    for row in data:
        try:
            dt = roc_to_ad_date(row[0].strip())
            rows.append(
                {
                    "Date": dt,
                    "Open": safe_float(row[3]),
                    "High": safe_float(row[4]),
                    "Low": safe_float(row[5]),
                    "Close": safe_float(row[6]),
                    "Volume": safe_float(row[1]) * 1000,
                }
            )
        except Exception:
            continue

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_price_history(code: str, market: str, months: int = 12) -> pd.DataFrame:
    now = pd.Timestamp.today().normalize().replace(day=1)
    dfs = []
    debug_logs = []

    for i in range(months):
        dt = now - pd.DateOffset(months=i)
        try:
            if market == "sii":
                yyyymm01 = dt.strftime("%Y%m01")
                debug_logs.append(f"TWSE 查詢月份: {yyyymm01}")
                df = get_twse_month(code, yyyymm01)
            else:
                roc_ym = f"{ad_to_roc(dt.year)}/{dt.month:02d}"
                debug_logs.append(f"TPEX 查詢月份: {roc_ym}")
                df = get_tpex_month(code, roc_ym)

            debug_logs.append(f"這個月抓到 {len(df)} 筆")
            if not df.empty:
                dfs.append(df)

        except Exception as e:
            debug_logs.append(f"錯誤: {str(e)}")
            continue

    for msg in debug_logs[:30]:
        st.caption(msg)

    if not dfs:
        return pd.DataFrame()

    out = pd.concat(dfs, ignore_index=True)
    out = out.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return out


# =========================
# 財報：MOPS
# =========================
def fetch_mops_tables(form_id: str, market: str, roc_year: int, season: int):
    url = f"https://mops.twse.com.tw/mops/web/ajax_t163sb{form_id}"
    payload = {
        "encodeURIComponent": 1,
        "step": 1,
        "firstin": 1,
        "off": 1,
        "TYPEK": market,
        "year": str(roc_year),
        "season": str(season),
    }

    try:
        r = requests.post(
            url,
            data=payload,
            headers=HEADERS,
            timeout=30,
            verify=False
        )
        r.raise_for_status()
        return pd.read_html(r.text)
    except Exception:
        return []


def extract_income(mapping: dict):
    revenue = keyword_value(mapping, ["營業收入合計", "收入合計", "營業收入淨額", "營業收入"])
    gross_profit_amt = keyword_value(mapping, ["營業毛利", "毛利"])
    operating_income = keyword_value(mapping, ["營業利益", "營業淨利"])
    net_income = keyword_value(mapping, ["本期淨利", "本期稅後淨利", "歸屬於母公司業主淨利", "淨利"])
    eps = keyword_value(mapping, ["基本每股盈餘", "每股盈餘"])
    return {
        "revenue": revenue,
        "gross_profit_amt": gross_profit_amt,
        "operating_income": operating_income,
        "net_income": net_income,
        "eps": eps,
    }


def extract_balance(mapping: dict):
    total_assets = keyword_value(mapping, ["資產總計", "資產總額"])
    total_liabilities = keyword_value(mapping, ["負債總計", "負債總額"])
    equity = keyword_value(mapping, ["權益總計", "股東權益總計", "歸屬於母公司業主之權益合計"])
    inventory = keyword_value(mapping, ["存貨"])
    cash = keyword_value(mapping, ["現金及約當現金", "現金及約當現金合計"])
    current_assets = keyword_value(mapping, ["流動資產合計", "流動資產總計"])
    current_liabilities = keyword_value(mapping, ["流動負債合計", "流動負債總計"])
    non_current_liabilities = keyword_value(mapping, ["非流動負債合計", "非流動負債總計"])
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "equity": equity,
        "inventory": inventory,
        "cash": cash,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "non_current_liabilities": non_current_liabilities,
    }


def extract_cashflow(mapping: dict):
    operating_cf = keyword_value(mapping, ["營業活動之淨現金流入", "營業活動之淨現金流量", "營業活動之淨現金流出"])
    capex_raw = keyword_value(mapping, ["取得不動產、廠房及設備", "購置不動產、廠房及設備", "資本支出"])
    capex = abs(capex_raw) if pd.notna(capex_raw) else np.nan
    return {
        "operating_cashflow": operating_cf,
        "capex": capex,
    }


@st.cache_data(ttl=21600)
def get_financial_snapshots(code: str, market: str):
    today = datetime.today()
    roc_year = ad_to_roc(today.year)
    quarter = (today.month - 1) // 3 + 1

    periods = []
    y, q = roc_year, quarter
    for _ in range(6):
        periods.append((y, q))
        q -= 1
        if q == 0:
            y -= 1
            q = 4

    income_snaps = []
    balance_snaps = []
    cash_snaps = []

    for y, q in periods:
        income_tables = fetch_mops_tables("04", market, y, q)
        income_df = pick_company_table(income_tables, code)
        income_map = map_from_statement_table(income_df)
        income_snaps.append({"year": y, "season": q, "data": extract_income(income_map)})

        balance_tables = fetch_mops_tables("05", market, y, q)
        balance_df = pick_company_table(balance_tables, code)
        balance_map = map_from_statement_table(balance_df)
        balance_snaps.append({"year": y, "season": q, "data": extract_balance(balance_map)})

        cash_tables = fetch_mops_tables("20", market, y, q)
        cash_df = pick_company_table(cash_tables, code)
        cash_map = map_from_statement_table(cash_df)
        cash_snaps.append({"year": y, "season": q, "data": extract_cashflow(cash_map)})

    return {
        "income": income_snaps,
        "balance": balance_snaps,
        "cash": cash_snaps,
    }


# =========================
# AI 報告
# =========================
@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-2.5-flash")

        price = d.get("price", np.nan)
        eps = d.get("eps", np.nan)
        pe = d.get("pe", np.nan)
        roe = d.get("roe", np.nan)
        rsi = d.get("rsi", np.nan)

        prompt = f"""針對 {d['name']} ({code})：
現價 {num_text(price)} 元，EPS {num_text(eps, 2)}，本益比 {num_text(pe)}，ROE {pct_text(roe)}
RSI {num_text(rsi)}，技術面多空由 MA5 / MA20 / MA60 趨勢判斷。
請依序回答：
1. 全球與產業局勢影響
2. 公司護城河與基本面健康度
3. 基本面與技術面綜合判斷
4. 合理價與目標價區間
5. 投資建議與風險提示"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 錯誤：{str(e)[:120]}"


# =========================
# 核心：建立 UI 使用的 dict
# =========================
@st.cache_data(ttl=1800)
def build_metrics(code: str):
    meta = get_stock_meta(code)
    name = meta.get("name", code)
    market = meta.get("market")

    if market is None:
        market = "sii"

    # 股價
    hist = get_price_history(code, market, months=12)
    st.write("偵錯｜股票代碼：", code)
    st.write("偵錯｜市場別：", market)
    st.write("偵錯｜hist 是否為空：", hist is None or hist.empty)

    if hist is not None and not hist.empty:
        st.write("偵錯｜股價資料筆數：", len(hist))
        st.dataframe(hist.tail())

    if hist is None or hist.empty:
        st.error(f"抓不到股價資料：code={code}, market={market}")
        return None

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

    df["std"] = df["Close"].rolling(window=20).std()
    df["atr"] = ta.atr(df["High"], df["Low"], df["Close"], 14)

    latest = df.iloc[-1]
    price = latest["Close"]
    prev_close = df["Close"].iloc[-2] if len(df) >= 2 else price
    price_change = price - prev_close if pd.notna(price) and pd.notna(prev_close) else np.nan
    price_change_pct = (
        price_change / prev_close * 100
        if pd.notna(price_change) and pd.notna(prev_close) and prev_close != 0
        else np.nan
    )

    # 財報
    fin = get_financial_snapshots(code, market)

    i0 = fin["income"][0]["data"] if len(fin["income"]) > 0 else {}
    i1 = fin["income"][1]["data"] if len(fin["income"]) > 1 else {}

    b0 = fin["balance"][0]["data"] if len(fin["balance"]) > 0 else {}
    b1 = fin["balance"][1]["data"] if len(fin["balance"]) > 1 else {}

    c0 = fin["cash"][0]["data"] if len(fin["cash"]) > 0 else {}
    c1 = fin["cash"][1]["data"] if len(fin["cash"]) > 1 else {}

    revenue = i0.get("revenue", np.nan)
    gross_profit_amt = i0.get("gross_profit_amt", np.nan)
    operating_income = i0.get("operating_income", np.nan)
    net_income = i0.get("net_income", np.nan)
    eps = i0.get("eps", np.nan)

    revenue_prev = i1.get("revenue", np.nan)
    gross_profit_prev = i1.get("gross_profit_amt", np.nan)
    operating_income_prev = i1.get("operating_income", np.nan)
    net_income_prev = i1.get("net_income", np.nan)
    eps_prev = i1.get("eps", np.nan)

    total_assets = b0.get("total_assets", np.nan)
    total_liabilities = b0.get("total_liabilities", np.nan)
    equity = b0.get("equity", np.nan)
    inventory = b0.get("inventory", np.nan)
    cash = b0.get("cash", np.nan)
    current_assets = b0.get("current_assets", np.nan)
    current_liabilities = b0.get("current_liabilities", np.nan)
    non_current_liabilities = b0.get("non_current_liabilities", np.nan)

    total_assets_prev = b1.get("total_assets", np.nan)
    equity_prev = b1.get("equity", np.nan)

    operating_cashflow = c0.get("operating_cashflow", np.nan)
    capex = c0.get("capex", np.nan)
    free_cashflow = operating_cashflow - capex if pd.notna(operating_cashflow) and pd.notna(capex) else np.nan

    operating_cashflow_prev = c1.get("operating_cashflow", np.nan)
    capex_prev = c1.get("capex", np.nan)
    free_cashflow_prev = (
        operating_cashflow_prev - capex_prev
        if pd.notna(operating_cashflow_prev) and pd.notna(capex_prev)
        else np.nan
    )

    # 自行計算指標
    gross_profit = gross_profit_amt / revenue if pd.notna(gross_profit_amt) and pd.notna(revenue) and revenue != 0 else np.nan
    net_margin = net_income / revenue if pd.notna(net_income) and pd.notna(revenue) and revenue != 0 else np.nan
    op_margin = operating_income / revenue if pd.notna(operating_income) and pd.notna(revenue) and revenue != 0 else np.nan
    roe = net_income / equity if pd.notna(net_income) and pd.notna(equity) and equity != 0 else np.nan
    roa = net_income / total_assets if pd.notna(net_income) and pd.notna(total_assets) and total_assets != 0 else np.nan

    rev_growth = calc_growth(revenue, revenue_prev)
    eps_growth = calc_growth(eps, eps_prev)
    net_income_growth = calc_growth(net_income, net_income_prev)
    gross_profit_growth = calc_growth(gross_profit_amt, gross_profit_prev)
    operating_income_growth = calc_growth(operating_income, operating_income_prev)
    assets_growth = calc_growth(total_assets, total_assets_prev)
    equity_growth = calc_growth(equity, equity_prev)

    debt_ratio = total_liabilities / total_assets if pd.notna(total_liabilities) and pd.notna(total_assets) and total_assets != 0 else np.nan
    debt_to_equity = total_liabilities / equity if pd.notna(total_liabilities) and pd.notna(equity) and equity != 0 else np.nan
    current_ratio = current_assets / current_liabilities if pd.notna(current_assets) and pd.notna(current_liabilities) and current_liabilities != 0 else np.nan
    quick_ratio = (current_assets - inventory) / current_liabilities if pd.notna(current_assets) and pd.notna(inventory) and pd.notna(current_liabilities) and current_liabilities != 0 else np.nan
    inv_asset_ratio = inventory / total_assets if pd.notna(inventory) and pd.notna(total_assets) and total_assets != 0 else np.nan
    cash_asset_ratio = cash / total_assets if pd.notna(cash) and pd.notna(total_assets) and total_assets != 0 else np.nan
    ncd_liabilities_ratio = non_current_liabilities / total_liabilities if pd.notna(non_current_liabilities) and pd.notna(total_liabilities) and total_liabilities != 0 else np.nan

    cashflow_profit_ratio = operating_cashflow / net_income if pd.notna(operating_cashflow) and pd.notna(net_income) and net_income != 0 else np.nan
    fcf_revenue_ratio = free_cashflow / revenue if pd.notna(free_cashflow) and pd.notna(revenue) and revenue != 0 else np.nan
    capex_to_cashflow = capex / operating_cashflow if pd.notna(capex) and pd.notna(operating_cashflow) and operating_cashflow != 0 else np.nan
    fcf_growth = calc_growth(free_cashflow, free_cashflow_prev)

    # 先保留欄位，但官方免費不容易穩定取得的先顯示 N/A
    pe = np.nan
    pb = np.nan
    peg = np.nan
    dividend_yield = np.nan
    payout_ratio = np.nan
    cash_dividend_yield = np.nan
    fcf_price_ratio = np.nan
    book_value_growth = equity_growth

    return {
        "price": price,
        "name": name,
        "market": market,
        "price_change": price_change,
        "price_change_pct": price_change_pct,

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
        "peg": peg,
        "dividend_yield": dividend_yield,
        "payout_ratio": payout_ratio,

        "df": df,
        "rsi": latest.get("rsi", np.nan),
        "ma5": latest.get("ma5", np.nan),
        "ma20": latest.get("ma20", np.nan),
        "ma60": latest.get("ma60", np.nan),
        "bias": latest.get("偏差", np.nan) * 100 if pd.notna(latest.get("偏差", np.nan)) else np.nan,
        "bb_upper": latest.get("布林上", np.nan),
        "bb_lower": latest.get("布林下", np.nan),
        "bb_mid": latest.get("布林中", np.nan),
        "atr": latest.get("atr", np.nan),
        "high_52": df["High"].max() if "High" in df.columns else np.nan,
        "low_52": df["Low"].min() if "Low" in df.columns else np.nan,

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
    }


# =========================
# UI helpers
# =========================
def metric_with_status(col, label, value, status=None, help_text=None):
    if status:
        col.metric(label, f"{value} ({status})", help=help_text)
    else:
        col.metric(label, value, help=help_text)


st.sidebar.markdown("### 📈 **台股深度分析**")
st.sidebar.markdown("---")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip().upper()
search_btn = st.sidebar.button("開始分析", use_container_width=True)

st.markdown("""
<style>
h1 {
    color: #34495E !important;
    font-size: 1.9rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;
    margin-top: 0.1rem !important;
}
h2 {
    color: #0095FF !important;
    font-size: 1.7rem !important;
    font-weight: 600 !important;
    margin-top: 0.7rem !important;
    margin-bottom: 0.3rem !important;
}
h3 {
    color: #E67E22 !important;
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.2rem !important;
    border-left: 4px solid #E67E22 !important;
    padding-left: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

if search_btn and code_input:
    with st.spinner(f"🔄 分析 {code_input} 資料中..."):
        d = build_metrics(code_input)

    if not d:
        st.error("查不到資料，請確認股票代碼是否正確。")
        st.stop()

    df = d["df"]
    price = d["price"]
    prev_close = df["Close"].iloc[-2] if len(df) >= 2 else price
    change_price = d.get("price_change", np.nan)
    change_percent = d.get("price_change_pct", np.nan)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.title(f"📊 {d.get('name', code_input)} ({code_input})")

    with col2:
        t1, t2, t3, t4, t5, t6 = st.columns(6)
        t1.metric("即時股價", num_text(price))
        t2.metric("漲跌額", "N/A" if pd.isna(change_price) else f"{change_price:+.1f}")
        t3.metric("漲跌幅", "N/A" if pd.isna(change_percent) else f"{change_percent:+.1f}%")
        t4.metric("今日開盤", num_text(df["Open"].iloc[-1]))
        t5.metric("今日高點", num_text(df["High"].iloc[-1]))
        t6.metric("今日低點", num_text(df["Low"].iloc[-1]))

        st.markdown("---")

        r1, r2, r3, r4, r5, r6 = st.columns(6)
        rsi_now = d.get("rsi", np.nan)
        if pd.notna(rsi_now):
            rsi_trend = "偏高⭐️" if rsi_now > 70 else "偏低⚠️" if rsi_now < 30 else "中間"
        else:
            rsi_trend = "N/A"
        r1.metric("RSI 趨勢", rsi_trend)
        r2.metric("即時 RSI", num_text(rsi_now))

        macd_line = df["macd"].iloc[-1] if "macd" in df.columns else np.nan
        macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else np.nan
        r3.metric("即時 MACD", "N/A" if pd.isna(macd_line) else f"{macd_line:+.2f}")
        r4.metric("MACD 信號線", "N/A" if pd.isna(macd_signal) else f"{macd_signal:+.2f}")
        volume = df["Volume"].iloc[-1] if "Volume" in df.columns else np.nan
        r5.metric("成交量(股)", "N/A" if pd.isna(volume) else f"{int(volume):,}")

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
        r6.metric("盤中量價", volume_trend)

    # 一、基本面
    st.header("📌 一、基本面：公司賺不賺錢")
    with st.container(border=True):
        st.subheader("盈利能力")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

        gp = d.get("gross_profit", np.nan)
        nm = d.get("net_margin", np.nan)
        om = d.get("op_margin", np.nan)
        eps = d.get("eps", np.nan)
        roe = d.get("roe", np.nan)
        roa = d.get("roa", np.nan)
        eps_growth = d.get("eps_growth", np.nan)

        metric_with_status(c1, "毛利率", pct_text(gp), None if pd.isna(gp) else ("偏高⭐️" if gp > 0.3 else "合理🟡" if gp >= 0.2 else "偏低⚠️"))
        metric_with_status(c2, "淨利率", pct_text(nm), None if pd.isna(nm) else ("偏高⭐️" if nm > 0.08 else "合理🟡" if nm >= 0.04 else "偏低⚠️"))
        metric_with_status(c3, "營業利益率", pct_text(om), None if pd.isna(om) else ("偏高⭐️" if om > 0.10 else "合理🟡" if om >= 0.05 else "偏低⚠️"))
        metric_with_status(c4, "EPS", num_text(eps, 2), None if pd.isna(eps) else ("偏高⭐️" if eps > 3 else "合理🟡" if eps >= 1.5 else "偏低⚠️"))
        metric_with_status(c5, "ROE", pct_text(roe), None if pd.isna(roe) else ("偏高⭐️" if roe > 0.15 else "合理🟡" if roe >= 0.10 else "偏低⚠️"))
        metric_with_status(c6, "ROA", pct_text(roa), None if pd.isna(roa) else ("偏高⭐️" if roa > 0.08 else "合理🟡" if roa >= 0.04 else "偏低⚠️"))
        metric_with_status(c7, "EPS 成長率", pct_text(eps_growth), None if pd.isna(eps_growth) else ("偏高⭐️" if eps_growth > 0.10 else "合理🟡" if eps_growth >= 0 else "偏低⚠️"))

        st.subheader("成長性")
        g1, g2, g3, g4, g5, g6, g7 = st.columns(7)
        rev_growth = d.get("rev_growth", np.nan)
        net_income_growth = d.get("net_income_growth", np.nan)
        gross_profit_growth = d.get("gross_profit_growth", np.nan)
        op_income_growth = d.get("operating_income_growth", np.nan)
        assets_growth = d.get("assets_growth", np.nan)
        equity_growth = d.get("equity_growth", np.nan)

        metric_with_status(g1, "營收成長率", pct_text(rev_growth), None if pd.isna(rev_growth) else ("偏高⭐️" if rev_growth > 0.10 else "合理🟡" if rev_growth >= 0 else "偏低⚠️"))
        metric_with_status(g2, "EPS 成長率", pct_text(eps_growth), None if pd.isna(eps_growth) else ("偏高⭐️" if eps_growth > 0.10 else "合理🟡" if eps_growth >= 0 else "偏低⚠️"))
        metric_with_status(g3, "淨利成長率", pct_text(net_income_growth), None if pd.isna(net_income_growth) else ("偏高⭐️" if net_income_growth > 0.10 else "合理🟡" if net_income_growth >= 0 else "偏低⚠️"))
        metric_with_status(g4, "毛利成長率", pct_text(gross_profit_growth), None if pd.isna(gross_profit_growth) else ("偏高⭐️" if gross_profit_growth > 0.10 else "合理🟡" if gross_profit_growth >= 0 else "偏低⚠️"))
        metric_with_status(g5, "營業利益成長率", pct_text(op_income_growth), None if pd.isna(op_income_growth) else ("偏高⭐️" if op_income_growth > 0.10 else "合理🟡" if op_income_growth >= 0 else "偏低⚠️"))
        metric_with_status(g6, "資產成長率", pct_text(assets_growth), None if pd.isna(assets_growth) else ("偏高⭐️" if assets_growth > 0.05 else "合理🟡" if assets_growth >= 0 else "偏低⚠️"))
        metric_with_status(g7, "權益成長率", pct_text(equity_growth), None if pd.isna(equity_growth) else ("偏高⭐️" if equity_growth > 0.08 else "合理🟡" if equity_growth >= 0 else "偏低⚠️"))

        st.subheader("財務結構")
        f1, f2, f3, f4, f5, f6, f7 = st.columns(7)
        debt_ratio = d.get("debt_ratio", np.nan)
        debt_to_equity = d.get("debt_to_equity", np.nan)
        current_ratio = d.get("current_ratio", np.nan)
        quick_ratio = d.get("quick_ratio", np.nan)
        inv_asset_ratio = d.get("inv_asset_ratio", np.nan)
        cash_asset_ratio = d.get("cash_asset_ratio", np.nan)
        ncd_liabilities_ratio = d.get("ncd_liabilities_ratio", np.nan)

        metric_with_status(f1, "負債比率", pct_text(debt_ratio), None if pd.isna(debt_ratio) else ("低風險⭐️" if debt_ratio < 0.5 else "中等🟡" if debt_ratio <= 0.7 else "高風險⚠️"))
        metric_with_status(f2, "負債/股東權益", pct_text(debt_to_equity), None if pd.isna(debt_to_equity) else ("低風險⭐️" if debt_to_equity < 0.5 else "中等🟡" if debt_to_equity <= 1 else "高風險⚠️"))
        metric_with_status(f3, "流動比率", num_text(current_ratio, 2), None if pd.isna(current_ratio) else ("偏高⭐️" if current_ratio > 2 else "合理🟡" if current_ratio >= 1 else "偏低⚠️"))
        metric_with_status(f4, "速動比率", num_text(quick_ratio, 2), None if pd.isna(quick_ratio) else ("偏高⭐️" if quick_ratio > 1.5 else "合理🟡" if quick_ratio >= 0.7 else "偏低⚠️"))
        metric_with_status(f5, "存貨佔資產比", pct_text(inv_asset_ratio), None if pd.isna(inv_asset_ratio) else ("偏高⚠️" if inv_asset_ratio > 0.5 else "合理🟡" if inv_asset_ratio >= 0.2 else "偏低⭐️"))
        metric_with_status(f6, "現金佔資產比", pct_text(cash_asset_ratio), None if pd.isna(cash_asset_ratio) else ("偏高⭐️" if cash_asset_ratio > 0.1 else "合理🟡" if cash_asset_ratio >= 0.05 else "偏低⚠️"))
        metric_with_status(f7, "非流動負債占負債比", pct_text(ncd_liabilities_ratio), None if pd.isna(ncd_liabilities_ratio) else ("偏高⚠️" if ncd_liabilities_ratio > 0.8 else "合理🟡" if ncd_liabilities_ratio >= 0.5 else "偏低⭐️"))

        st.subheader("現金流品質")
        ca1, ca2, ca3, ca4, ca5, ca6, ca7 = st.columns(7)
        operating_cashflow = d.get("operating_cashflow", np.nan)
        free_cashflow = d.get("free_cashflow", np.nan)
        cashflow_profit_ratio = d.get("cashflow_profit_ratio", np.nan)
        fcf_revenue_ratio = d.get("fcf_revenue_ratio", np.nan)
        fcf_price_ratio = d.get("fcf_price_ratio", np.nan)
        fcf_growth = d.get("fcf_growth", np.nan)
        capex_to_cashflow = d.get("capex_to_cashflow", np.nan)

        ca1.metric("營業現金流", big_text(operating_cashflow))
        ca2.metric("自由現金流(FCF)", big_text(free_cashflow))
        metric_with_status(ca3, "現金流/淨利", num_text(cashflow_profit_ratio, 2), None if pd.isna(cashflow_profit_ratio) else ("偏高⭐️" if cashflow_profit_ratio > 1 else "合理🟡" if cashflow_profit_ratio >= 0.7 else "偏低⚠️"))
        metric_with_status(ca4, "FCF/營收", pct_text(fcf_revenue_ratio), None if pd.isna(fcf_revenue_ratio) else ("偏高⭐️" if fcf_revenue_ratio > 0.15 else "合理🟡" if fcf_revenue_ratio >= 0.05 else "偏低⚠️"))
        metric_with_status(ca5, "FCF/股價", pct_text(fcf_price_ratio), None)
        metric_with_status(ca6, "FCF 成長率", pct_text(fcf_growth), None if pd.isna(fcf_growth) else ("偏高⭐️" if fcf_growth > 0.10 else "合理🟡" if fcf_growth >= 0 else "偏低⚠️"))
        metric_with_status(ca7, "資本支出/營業現金流", num_text(capex_to_cashflow, 2), None if pd.isna(capex_to_cashflow) else ("偏高⭐️" if capex_to_cashflow > 1 else "合理🟡" if capex_to_cashflow >= 0.5 else "偏低⚠️"))

        st.subheader("估值水準")
        v1, v2, v3, v4, v5, v6, v7 = st.columns(7)
        pe = d.get("pe", np.nan)
        pb = d.get("pb", np.nan)
        peg = d.get("peg", np.nan)
        div_yield = d.get("dividend_yield", np.nan)
        payout_ratio = d.get("payout_ratio", np.nan)
        cash_dividend_yield = d.get("cash_dividend_yield", np.nan)
        book_value_growth = d.get("book_value_growth", np.nan)

        metric_with_status(v1, "本益比(P/E)", "N/A" if pd.isna(pe) else f"{pe:.1f}x", None if pd.isna(pe) else ("偏高估⚠️" if pe > 20 else "合理🟡" if pe >= 10 else "偏低估⭐️"))
        metric_with_status(v2, "股價淨值比(P/B)", "N/A" if pd.isna(pb) else f"{pb:.1f}x", None if pd.isna(pb) else ("偏高估⚠️" if pb > 3 else "合理🟡" if pb >= 1 else "偏低估⭐️"))
        metric_with_status(v3, "PEG", num_text(peg), None if pd.isna(peg) else ("偏高估⚠️" if peg > 1.5 else "合理🟡" if peg >= 1 else "偏低估⭐️"))
        metric_with_status(v4, "股利殖利率", pct_text(div_yield), None if pd.isna(div_yield) else ("偏高⭐️" if div_yield > 0.05 else "合理🟡" if div_yield >= 0.02 else "偏低⚠️"))
        metric_with_status(v5, "盈餘配發率", pct_text(payout_ratio), None if pd.isna(payout_ratio) else ("偏高⭐️" if payout_ratio > 0.7 else "合理🟡" if payout_ratio >= 0.3 else "偏低⚠️"))
        metric_with_status(v6, "現金股利報酬率", pct_text(cash_dividend_yield), None if pd.isna(cash_dividend_yield) else ("偏高⭐️" if cash_dividend_yield > 0.05 else "合理🟡" if cash_dividend_yield >= 0.02 else "偏低⚠️"))
        metric_with_status(v7, "帳面價值成長率", pct_text(book_value_growth), None if pd.isna(book_value_growth) else ("偏高⭐️" if book_value_growth > 0.08 else "合理🟡" if book_value_growth >= 0 else "偏低⚠️"))

    # 二、技術面
    st.header("📉 二、技術面：股價趨勢與強度")
    with st.container(border=True):
        t1, t2, t3, t4 = st.columns(4)

        t1.subheader("趨勢與均線")
        ma5 = d.get("ma5", np.nan)
        ma20 = d.get("ma20", np.nan)
        ma60 = d.get("ma60", np.nan)
        bias = d.get("bias", np.nan)

        t1.metric("MA5", "N/A" if pd.isna(ma5) else f"{ma5:.1f} ({'多頭' if price > ma5 else '空頭'})")
        t1.metric("MA20", "N/A" if pd.isna(ma20) else f"{ma20:.1f} ({'多頭' if price > ma20 else '空頭'})")
        t1.metric("MA60", "N/A" if pd.isna(ma60) else f"{ma60:.1f} ({'多頭' if price > ma60 else '空頭'})")
        t1.metric("乖離率", "N/A" if pd.isna(bias) else f"{bias:.1f}%")

        t2.subheader("動能與強度")
        t2.metric("RSI", "N/A" if pd.isna(rsi_now) else f"{rsi_now:.1f}")
        t2.metric("MACD 本體", "N/A" if pd.isna(macd_line) else f"{macd_line:+.2f}")
        t2.metric("MACD 信號線", "N/A" if pd.isna(macd_signal) else f"{macd_signal:+.2f}")

        t3.subheader("波動與區間")
        bb_upper = d.get("bb_upper", np.nan)
        bb_mid = d.get("bb_mid", np.nan)
        bb_lower = d.get("bb_lower", np.nan)
        high_52 = d.get("high_52", np.nan)
        low_52 = d.get("low_52", np.nan)
        std_20 = df["std"].iloc[-1] if "std" in df.columns else np.nan
        atr = d.get("atr", np.nan)

        t3.metric("布林上軌", num_text(bb_upper))
        t3.metric("布林中軌", num_text(bb_mid))
        t3.metric("布林下軌", num_text(bb_lower))
        t3.metric("52週高價", num_text(high_52))
        t3.metric("52週低價", num_text(low_52))
        t3.metric("標準差(20日)", num_text(std_20, 2))
        t3.metric("ATR(14日)", num_text(atr, 2))

        t4.subheader("成交量與量價關係")
        latest_vol = df["Volume"].iloc[-1] if "Volume" in df.columns else np.nan
        avg_vol = df["Volume"][-30:].mean() if "Volume" in df.columns and len(df) >= 30 else np.nan
        if pd.notna(change_percent) and pd.notna(latest_vol) and pd.notna(avg_vol):
            if change_percent > 0 and latest_vol > avg_vol * 1.2:
                vpt = "價漲量增"
            elif change_percent < 0 and latest_vol > avg_vol * 1.2:
                vpt = "價跌量增"
            elif change_percent > 0 and latest_vol < avg_vol * 0.8:
                vpt = "價漲量縮"
            elif change_percent < 0 and latest_vol < avg_vol * 0.8:
                vpt = "價跌量縮"
            else:
                vpt = "價量正常"
        else:
            vpt = "量價資訊不足"

        t4.metric("今日成交量", "N/A" if pd.isna(latest_vol) else f"{int(latest_vol):,}")
        t4.metric("量價關係", vpt)

    # 三、財務與資本結構
    st.header("🏦 三、財務與資本結構：公司資本是否健康")
    with st.container(border=True):
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("總資產", big_text(d.get("total_assets", np.nan), unit="億", divisor=1e8))
        s2.metric("總負債", big_text(d.get("total_liabilities", np.nan), unit="億", divisor=1e8))
        s3.metric("股東權益", big_text(d.get("equity", np.nan), unit="億", divisor=1e8))
        s4.metric("資本支出(Capex)", big_text(d.get("capex", np.nan), unit="億", divisor=1e8))
        st.metric("資本支出/營業現金流", num_text(d.get("capex_to_cashflow", np.nan), 2))

    # 四、現金流與股利
    st.header("💵 四、現金流與股利：現金能不能穩定入袋")
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("自由現金流/營收", pct_text(d.get("fcf_revenue_ratio", np.nan)))
        f2.metric("自由現金流/股價", pct_text(d.get("fcf_price_ratio", np.nan)))
        f3.metric("FCF成長率", pct_text(d.get("fcf_growth", np.nan)))
        f4.metric("盈餘配發率", pct_text(d.get("payout_ratio", np.nan)))
        st.write("說明：")
        st.write("• 若「自由現金流/股價」為正，代表每單位股價背後有現金流支撐。")
        st.write("• 若「盈餘配發率」接近 100%，代表大多數盈餘已配出。")

    # 五、AI 診斷
    st.markdown("---")
    st.header("🤖 五、AI診斷")
    api_status = st.secrets.get("GEMINI_API_KEY", "")
    c1, c2 = st.columns([1, 4])

    with c1:
        st.caption("**🟢 已連線**" if api_status else "**🔴 未連線**")
    with c2:
        st.caption("**Gemini 2.5 Flash**")

    if st.button("🚀 啟動 AI 深度診斷", type="primary", use_container_width=True):
        if api_status:
            with st.spinner(f"🤖 AI 分析 {d['name']}..."):
                report = get_ai_analysis_report(d, code_input, api_status)
                st.markdown("### 📋 **AI 終極投資報告**")
                st.markdown("---")
                st.markdown(report)
                st.success("✅ AI 診斷完成！")
        else:
            st.error("請先在 Streamlit Secrets 設定 GEMINI_API_KEY。")

else:
    st.write("✅ 這是 Raymond 的台股深度分析，請輸入股票代碼後點擊左側「開始分析」。")





