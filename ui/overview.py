import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

    if not df.empty:
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
        ))

        if "ma20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], mode="lines", name="MA20"))
        if "ma60" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ma60"], mode="lines", name="MA60"))

        fig.update_layout(
            title=f"{d.get('name', code_input)} 近一年K線圖",
            height=520,
            xaxis_rangeslider_visible=False,
            legend_orientation="h",
        )

        st.plotly_chart(fig, use_container_width=True)

        vol_fig = go.Figure()
        vol_fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量"))
        vol_fig.update_layout(height=260, title="成交量", showlegend=False)
        st.plotly_chart(vol_fig, use_container_width=True)

    with st.expander("查看原始財報表"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("損益表")
            st.dataframe(d.get("financials", pd.DataFrame()), use_container_width=True)
        with c2:
            st.caption("資產負債表")
            st.dataframe(d.get("balance_sheet", pd.DataFrame()), use_container_width=True)
        with c3:
            st.caption("現金流量表")
            st.dataframe(d.get("cashflow", pd.DataFrame()), use_container_width=True)
