import streamlit as st
import pandas as pd


def render_financial_tables(d):
    st.header("🏦 財報原始表格")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("損益表")
        st.dataframe(
            d.get("financials", pd.DataFrame()),
            use_container_width=True,
            height=500
        )

    with c2:
        st.subheader("資產負債表")
        st.dataframe(
            d.get("balance_sheet", pd.DataFrame()),
            use_container_width=True,
            height=500
        )

    with c3:
        st.subheader("現金流量表")
        st.dataframe(
            d.get("cashflow", pd.DataFrame()),
            use_container_width=True,
            height=500
        )
