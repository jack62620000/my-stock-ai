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

    # 固定視窗大小
    window_size = st.session_state.get("chart_window_size", 60)

    st.markdown("### 📊 固定視窗 K 線圖")
    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        if st.button("⬅ 往左看更早資料", use_container_width=True):
            st.session_state["chart_start"] = max(0, st.session_state.get("chart_start", max(len(df) - window_size, 0)) - 10)

    with c3:
        if st.button("往右看更新資料 ➡", use_container_width=True):
            st.session_state["chart_start"] = min(
                max(len(df) - window_size, 0),
                st.session_state.get("chart_start", max(len(df) - window_size, 0)) + 10
            )

    # 初始化起始位置：預設看最近一段
    if "chart_start" not in st.session_state:
        st.session_state["chart_start"] = max(len(df) - window_size, 0)

    max_start = max(len(df) - window_size, 0)

    start_idx = st.slider(
        "移動K線視窗",
        min_value=0,
        max_value=max_start if max_start > 0 else 0,
        value=min(st.session_state["chart_start"], max_start),
        step=1,
    )
    st.session_state["chart_start"] = start_idx

    visible_df = df.iloc[start_idx:start_idx + window_size].copy()

    if visible_df.empty:
        st.warning("目前視窗內沒有資料")
        return

    visible_high = visible_df["High"].max()
    visible_low = visible_df["Low"].min()
    price_padding = (visible_high - visible_low) * 0.04 if visible_high != visible_low else visible_high * 0.03

    y_min = visible_low - price_padding
    y_max = visible_high + price_padding

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.85, 0.15],
    )

    fig.add_trace(
        go.Candlestick(
            increasing_line_width=1.4,
            decreasing_line_width=1.4,
            x=visible_df.index,
            open=visible_df["Open"],
            high=visible_df["High"],
            low=visible_df["Low"],
            close=visible_df["Close"],
            name="K線",
        ),
        row=1, col=1
    )

    if "ma20" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["ma20"],
                mode="lines",
                name="MA20",
                line=dict(width=2)
            ),
            row=1, col=1
        )

    if "ma60" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["ma60"],
                mode="lines",
                name="MA60",
                line=dict(width=2)
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

    fig.update_layout(
        title=f"{d.get('name', code_input)} 固定視窗K線圖",
        height=560,
        xaxis_rangeslider_visible=False,
        dragmode=False,   # 不使用 plotly 自由拖曳
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=60, b=20),
    )

    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)
    fig.update_yaxes(row=2, col=1)

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

