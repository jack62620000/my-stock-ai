import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.valuation import calc_fair_price, calc_margin_of_safety


def render_overview(d, code_input):
    df = d.get("df", pd.DataFrame())
    price = d.get("price", 0)
    position_52 = d.get("position_52", float("nan"))
    fair_price = calc_fair_price(d)
    margin = calc_margin_of_safety(d)

    # ===== 上方重點指標 =====
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

    # ===== 固定視窗設定 =====
    window_size = st.session_state.get("chart_window_size", 60)

    if "chart_start" not in st.session_state:
        st.session_state["chart_start"] = max(len(df) - window_size, 0)

    max_start = max(len(df) - window_size, 0)

    st.markdown("### 📊 固定視窗 K 線圖")

    btn_left, _, btn_right = st.columns([1.2, 4.6, 1.2])

    with btn_left:
        if st.button("⬅ 往左看更早資料", use_container_width=True):
            st.session_state["chart_start"] = max(
                0,
                st.session_state.get("chart_start", max(len(df) - window_size, 0)) - 10
            )

    with btn_right:
        if st.button("往右看更新資料 ➡", use_container_width=True):
            st.session_state["chart_start"] = min(
                max_start,
                st.session_state.get("chart_start", max(len(df) - window_size, 0)) + 10
            )

    start_idx = min(st.session_state["chart_start"], max_start)
    st.session_state["chart_start"] = start_idx

    visible_df = df.iloc[start_idx:start_idx + window_size].copy()

    if visible_df.empty:
        st.warning("目前視窗內沒有資料")
        return

    # ===== 自動調整Y軸 =====
    visible_high = visible_df["High"].max()
    visible_low = visible_df["Low"].min()
    price_padding = (
        (visible_high - visible_low) * 0.04
        if visible_high != visible_low
        else visible_high * 0.03
    )

    y_min = visible_low - price_padding
    y_max = visible_high + price_padding

    # ===== K線 + 成交量 =====
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.86, 0.14],
    )

    # K線
    fig.add_trace(
        go.Candlestick(
            x=visible_df.index,
            open=visible_df["Open"],
            high=visible_df["High"],
            low=visible_df["Low"],
            close=visible_df["Close"],
            name="K線",
            increasing_line_width=1.5,
            decreasing_line_width=1.5,
        ),
        row=1,
        col=1
    )

    # MA5
    if "ma5" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["ma5"],
                mode="lines",
                name="MA5",
                line=dict(width=2),
            ),
            row=1,
            col=1
        )

    # MA20
    if "ma20" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["ma20"],
                mode="lines",
                name="MA20",
                line=dict(width=2),
            ),
            row=1,
            col=1
        )

    # MA60
    if "ma60" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["ma60"],
                mode="lines",
                name="MA60",
                line=dict(width=2),
            ),
            row=1,
            col=1
        )

    # 成交量
    fig.add_trace(
        go.Bar(
            x=visible_df.index,
            y=visible_df["Volume"],
            name="成交量",
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=None,  # 拿掉圖內標題
        height=640,  # K線放大一些
        xaxis_rangeslider_visible=False,
        dragmode=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=10, r=10, t=20, b=10),
    )

    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)

    # 控制寬度
    chart_left, chart_center, chart_right = st.columns([1.2, 5.6, 1.2])

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

    # ===== 原始財報表 =====
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
