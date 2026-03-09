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


def render_overview(d, code_input):
    df = d.get("df", pd.DataFrame())
    price = d.get("price", 0)
    position_52 = d.get("position_52", float("nan"))
    fair_price = calc_fair_price(d)
    margin = calc_margin_of_safety(d)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("即時股價", f"{price:.1f}")
    col2.metric("漲跌額", f"{d.get('price_change_amount', 0):+.1f}")
    col3.metric("漲跌幅", f"{d.get('price_change', 0):+.1f}%")
    col4.metric("52週位置", f"{position_52 * 100:.1f}%" if pd.notna(position_52) else "N/A")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("EPS", f"{d.get('eps', 0):.2f}" if pd.notna(d.get("eps")) else "N/A")
    col6.metric("本益比(P/E)", f"{d.get('pe', 0):.1f}x" if pd.notna(d.get("pe")) else "N/A")
    col7.metric("估算合理價", f"{fair_price:.1f}" if pd.notna(fair_price) else "N/A")
    col8.metric("安全邊際", f"{margin * 100:.1f}%" if pd.notna(margin) else "N/A")

    st.markdown("---")

    if df.empty:
        st.warning("沒有K線資料")
        return

    # ===== 控制列 =====
    ctrl1, ctrl2 = st.columns([2, 2])

    with ctrl1:
        period_type = st.radio(
            "K線週期",
            ["日", "週", "月"],
            horizontal=True,
            index=0,
            key=f"period_type_{code_input}",
        )

    with ctrl2:
        window_size = st.radio(
            "顯示根數",
            [30, 60, 120],
            horizontal=True,
            index=1,
            key=f"window_size_{code_input}",
        )

    # ===== 週期轉換 =====
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

    st.markdown("### 📊 固定視窗 K 線圖")

    btn_left, _, btn_right = st.columns([1.2, 4.6, 1.2])

    with btn_left:
        if st.button("⬅ 往左看更早資料", use_container_width=True, key=f"left_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = max(
                0,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) - 10
            )

    with btn_right:
        if st.button("往右看更新資料 ➡", use_container_width=True, key=f"right_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = min(
                max_start,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) + 10
            )

    start_idx = min(st.session_state[session_key], max_start)
    st.session_state[session_key] = start_idx

    visible_df = chart_df.iloc[start_idx:start_idx + window_size].copy()

    if visible_df.empty:
        st.warning("目前視窗內沒有資料")
        return

    # ===== 上方資訊列 =====
    last_row = visible_df.iloc[-1]
    open_p = last_row["Open"]
    high_p = last_row["High"]
    low_p = last_row["Low"]
    close_p = last_row["Close"]
    vol = last_row["Volume"]

    prev_close = visible_df["Close"].iloc[-2] if len(visible_df) >= 2 else close_p
    change = close_p - prev_close

    st.markdown(f"### {d.get('name', code_input)} ({code_input})")

    i1, i2, i3, i4, i5, i6, i7 = st.columns(7)
    i1.metric("日期", last_row.name.strftime("%Y/%m/%d"))
    i2.metric("開", f"{open_p:.0f}")
    i3.metric("高", f"{high_p:.0f}")
    i4.metric("低", f"{low_p:.0f}")
    i5.metric("收", f"{close_p:.0f}")
    i6.metric("量(張)", f"{int(vol / 1000):,}")
    i7.metric("漲跌", f"{change:+.0f}")

    # ===== 均線說明列 =====
    ma_cols = st.columns(6)
    ma_cols[0].caption(f"MA5：{visible_df['ma5'].iloc[-1]:.1f}" if "ma5" in visible_df.columns and pd.notna(visible_df["ma5"].iloc[-1]) else "MA5：N/A")
    ma_cols[1].caption(f"MA10：{visible_df['ma10'].iloc[-1]:.1f}" if "ma10" in visible_df.columns and pd.notna(visible_df["ma10"].iloc[-1]) else "MA10：N/A")
    ma_cols[2].caption(f"MA20：{visible_df['ma20'].iloc[-1]:.1f}" if "ma20" in visible_df.columns and pd.notna(visible_df["ma20"].iloc[-1]) else "MA20：N/A")
    ma_cols[3].caption(f"MA60：{visible_df['ma60'].iloc[-1]:.1f}" if "ma60" in visible_df.columns and pd.notna(visible_df["ma60"].iloc[-1]) else "MA60：N/A")
    ma_cols[4].caption(f"MV5：{visible_df['mv5'].iloc[-1]:.1f}" if "mv5" in visible_df.columns and pd.notna(visible_df["mv5"].iloc[-1]) else "MV5：N/A")
    ma_cols[5].caption(f"MV20：{visible_df['mv20'].iloc[-1]:.1f}" if "mv20" in visible_df.columns and pd.notna(visible_df["mv20"].iloc[-1]) else "MV20：N/A")

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
        row_heights=[0.78, 0.22],
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
                line=dict(width=1.3),
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
                line=dict(width=1.3),
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
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=10, r=10, t=10, b=10),
    )

    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)

    chart_left, chart_center, chart_right = st.columns([1.0, 6.0, 1.0])

    with chart_center:
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "scrollZoom": False
            }
        )

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
