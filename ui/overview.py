import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.valuation import calc_fair_price, calc_margin_of_safety


def _resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    agg_map = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }

    out = df.resample(freq).agg(agg_map)

    for col in ["ma5", "ma10", "ma20", "ma60", "mv5", "mv20"]:
        if col in df.columns:
            out[col] = df[col].resample(freq).last()

    return out.dropna(subset=["Open", "High", "Low", "Close"])


def _fmt_num(v, digits=1, suffix=""):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}{suffix}"


def render_overview(d, code_input):
    df = d.get("df", pd.DataFrame())
    price = d.get("price", 0)
    position_52 = d.get("position_52", float("nan"))
    fair_price = calc_fair_price(d)
    margin = calc_margin_of_safety(d)

    if df.empty:
        st.warning("沒有K線資料")
        return

    # ===== 上方摘要 =====
    top1, top2, top3, top4 = st.columns(4)
    top1.metric("即時股價", f"{price:.1f}")
    top2.metric("漲跌額", f"{d.get('price_change_amount', 0):+.1f}")
    top3.metric("漲跌幅", f"{d.get('price_change', 0):+.1f}%")
    top4.metric("52週位置", f"{position_52 * 100:.1f}%" if pd.notna(position_52) else "N/A")

    top5, top6, top7, top8 = st.columns(4)
    top5.metric("EPS", _fmt_num(d.get("eps"), 2))
    top6.metric("本益比(P/E)", _fmt_num(d.get("pe"), 1, "x"))
    top7.metric("估算合理價", _fmt_num(fair_price, 1))
    top8.metric("安全邊際", _fmt_num(margin * 100, 1, "%") if pd.notna(margin) else "N/A")

    st.divider()

    # ===== 切換列 =====
    ctl1, ctl2 = st.columns(2)
    with ctl1:
        period_type = st.radio(
            "K線週期",
            ["日", "週", "月"],
            horizontal=True,
            key=f"period_type_{code_input}",
        )

    with ctl2:
        window_size = st.radio(
            "顯示根數",
            [30, 60, 120],
            horizontal=True,
            index=1,
            key=f"window_size_{code_input}",
        )

    chart_df = df.copy()
    if period_type == "週":
        chart_df = _resample_ohlcv(chart_df, "W")
    elif period_type == "月":
        chart_df = _resample_ohlcv(chart_df, "M")

    if chart_df.empty:
        st.warning("該週期沒有資料")
        return

    session_key = f"chart_start_{code_input}_{period_type}_{window_size}"
    if session_key not in st.session_state:
        st.session_state[session_key] = max(len(chart_df) - window_size, 0)

    max_start = max(len(chart_df) - window_size, 0)
    start_idx = min(st.session_state[session_key], max_start)
    st.session_state[session_key] = start_idx

    visible_df = chart_df.iloc[start_idx:start_idx + window_size].copy()

    if visible_df.empty:
        st.warning("目前視窗內沒有資料")
        return

    # ===== 報價資訊 =====
    last_row = visible_df.iloc[-1]
    open_p = last_row["Open"]
    high_p = last_row["High"]
    low_p = last_row["Low"]
    close_p = last_row["Close"]
    vol = last_row["Volume"]

    prev_close = visible_df["Close"].iloc[-2] if len(visible_df) >= 2 else close_p
    change = close_p - prev_close

    ma5_val = visible_df["ma5"].iloc[-1] if "ma5" in visible_df.columns else float("nan")
    ma10_val = visible_df["ma10"].iloc[-1] if "ma10" in visible_df.columns else float("nan")
    ma20_val = visible_df["ma20"].iloc[-1] if "ma20" in visible_df.columns else float("nan")
    ma60_val = visible_df["ma60"].iloc[-1] if "ma60" in visible_df.columns else float("nan")
    mv5_val = visible_df["mv5"].iloc[-1] if "mv5" in visible_df.columns else float("nan")
    mv20_val = visible_df["mv20"].iloc[-1] if "mv20" in visible_df.columns else float("nan")

    with st.container(border=True):
        st.subheader(f"{d.get('name', code_input)} ({code_input})")

        q1, q2, q3, q4, q5, q6, q7 = st.columns(7)
        q1.metric("日期", last_row.name.strftime("%Y/%m/%d"))
        q2.metric("開盤價", _fmt_num(open_p, 0))
        q3.metric("最高價", _fmt_num(high_p, 0))
        q4.metric("最低價", _fmt_num(low_p, 0))
        q5.metric("收盤價", _fmt_num(close_p, 0))
        q6.metric("成交量(股)", f"{int(vol):,}")
        q7.metric("漲跌", _fmt_num(change, 0))

        st.markdown("##### 均線 / 均量")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("MA5", _fmt_num(ma5_val, 1))
        m2.metric("MA10", _fmt_num(ma10_val, 1))
        m3.metric("MA20", _fmt_num(ma20_val, 1))
        m4.metric("MA60", _fmt_num(ma60_val, 1))
        m5.metric("MV5", _fmt_num(mv5_val, 1))
        m6.metric("MV20", _fmt_num(mv20_val, 1))

    st.markdown("")

    # ===== 自動Y軸 =====
    visible_high = visible_df["High"].max()
    visible_low = visible_df["Low"].min()
    price_padding = (
        (visible_high - visible_low) * 0.04
        if visible_high != visible_low
        else visible_high * 0.03
    )
    y_min = visible_low - price_padding
    y_max = visible_high + price_padding

    # ===== 圖表 =====
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.80, 0.20],
    )

    fig.add_trace(
        go.Candlestick(
            x=visible_df.index,
            open=visible_df["Open"],
            high=visible_df["High"],
            low=visible_df["Low"],
            close=visible_df["Close"],
            name="K線",
            increasing_line_width=1.4,
            decreasing_line_width=1.4,
        ),
        row=1, col=1
    )

    line_map = [
        ("ma5", "MA5"),
        ("ma10", "MA10"),
        ("ma20", "MA20"),
        ("ma60", "MA60"),
    ]

    for col, label in line_map:
        if col in visible_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=visible_df.index,
                    y=visible_df[col],
                    mode="lines",
                    name=label,
                    line=dict(width=1.8),
                ),
                row=1, col=1
            )

    fig.add_trace(
        go.Bar(
            x=visible_df.index,
            y=visible_df["Volume"],
            name="成交量",
        ),
        row=2, col=1
    )

    if "mv5" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["mv5"],
                mode="lines",
                name="MV5",
                line=dict(width=1.2),
            ),
            row=2, col=1
        )

    if "mv20" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["mv20"],
                mode="lines",
                name="MV20",
                line=dict(width=1.2),
            ),
            row=2, col=1
        )

    fig.update_layout(
        title=None,
        height=720,
        xaxis_rangeslider_visible=False,
        dragmode=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0
        ),
        margin=dict(l=10, r=10, t=10, b=10),
    )

    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)

    # ===== 左右按鈕 =====
    wrap_left, wrap_center, wrap_right = st.columns([0.8, 6.4, 0.8])

    with wrap_left:
        st.write("")
        st.write("")
        if st.button("⬅", use_container_width=True, key=f"left_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = max(
                0,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) - 10
            )
            st.rerun()

    with wrap_center:
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "scrollZoom": False
            }
        )

    with wrap_right:
        st.write("")
        st.write("")
        if st.button("➡", use_container_width=True, key=f"right_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = min(
                max_start,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) + 10
            )
            st.rerun()

    st.caption(
        f"目前顯示區間：{visible_df.index[0].strftime('%Y-%m-%d')} ～ {visible_df.index[-1].strftime('%Y-%m-%d')}"
    )

    with st.expander("查看原始財報表", expanded=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.caption("損益表")
            st.dataframe(
                d.get("financials", pd.DataFrame()),
                use_container_width=True,
                height=320
            )

        with c2:
            st.caption("資產負債表")
            st.dataframe(
                d.get("balance_sheet", pd.DataFrame()),
                use_container_width=True,
                height=320
            )

        with c3:
            st.caption("現金流量表")
            st.dataframe(
                d.get("cashflow", pd.DataFrame()),
                use_container_width=True,
                height=320
            )
