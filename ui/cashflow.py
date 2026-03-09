import streamlit as st


def render_cashflow_section(d):
    st.header("💵 四、現金流與股利：現金能不能穩定入袋")

    with st.container(border=True):
        ca1, ca2, ca3, ca4, ca5, ca6, ca7 = st.columns(7)

        ca1.metric("營業現金流", f"{d.get('operating_cashflow', 0) / 1e8:.1f}億" if d.get("operating_cashflow") == d.get("operating_cashflow") else "N/A")
        ca2.metric("自由現金流(FCF)", f"{d.get('free_cashflow', 0) / 1e8:.1f}億" if d.get("free_cashflow") == d.get("free_cashflow") else "N/A")

        cashflow_profit_ratio = d.get("cashflow_profit_ratio", 0)
        cfp_text = ":red[偏高⭐️]" if cashflow_profit_ratio > 1 else ":orange[合理🟡]" if cashflow_profit_ratio >= 0.7 else ":green[偏低⚠️]"
        ca3.metric("現金流/淨利", f"{cashflow_profit_ratio:.2f} ({cfp_text})" if cashflow_profit_ratio == cashflow_profit_ratio else "N/A")

        fcf_revenue_ratio = d.get("fcf_revenue_ratio", 0)
        fcf_rev_text = ":red[偏高⭐️]" if fcf_revenue_ratio > 0.15 else ":orange[合理🟡]" if fcf_revenue_ratio >= 0.05 else ":green[偏低⚠️]"
        ca4.metric("FCF/營收", f"{fcf_revenue_ratio:.1%} ({fcf_rev_text})" if fcf_revenue_ratio == fcf_revenue_ratio else "N/A")

        fcf_price_ratio = d.get("fcf_price_ratio", 0)
        fcf_price_text = ":red[偏高⭐️]" if fcf_price_ratio > 0.05 else ":orange[合理🟡]" if fcf_price_ratio >= 0.01 else ":green[偏低⚠️]"
        ca5.metric("FCF/股價", f"{fcf_price_ratio:.1%} ({fcf_price_text})" if fcf_price_ratio == fcf_price_ratio else "N/A")

        fcf_growth = d.get("fcf_growth", 0) * 100
        fcf_growth_text = ":red[偏高⭐️]" if fcf_growth > 10 else ":orange[合理🟡]" if fcf_growth >= 0 else ":green[偏低⚠️]"
        ca6.metric("FCF 成長率", f"{fcf_growth:.1f}% ({fcf_growth_text})" if fcf_growth == fcf_growth else "N/A")

        capex_to_cashflow = d.get("capex_to_cashflow", 0)
        capex_cf_text = ":red[偏高⭐️]" if capex_to_cashflow > 1.0 else ":orange[合理🟡]" if capex_to_cashflow >= 0.5 else ":green[偏低⚠️]"
        ca7.metric("資本支出/營業現金流", f"{capex_to_cashflow:.2f} ({capex_cf_text})" if capex_to_cashflow == capex_to_cashflow else "N/A")

        st.markdown("---")

        f1, f2, f3, f4 = st.columns(4)

        fcf_revenue_ratio = d.get("fcf_revenue_ratio", 0)
        fcf_revenue_text = ":red[偏高，每單位營收有高現金]" if fcf_revenue_ratio > 0.20 else ":orange[合理]" if fcf_revenue_ratio > 0.05 else ":green[偏低，營收現金化能力較弱]"
        f1.metric("自由現金流/營收", f"{fcf_revenue_ratio:.1%}", help=f"自由現金流佔營收比例：{fcf_revenue_ratio:.1%}，{fcf_revenue_text}")

        fcf_price_ratio = d.get("fcf_price_ratio", 0)
        fcf_price_text = ":red[偏高，股價背後有強現金支撐]" if fcf_price_ratio > 0.08 else ":orange[合理]" if fcf_price_ratio > 0.02 else ":green[偏低，股價現金支撐較弱]"
        f2.metric("自由現金流/股價", f"{fcf_price_ratio:.1%}" if fcf_price_ratio == fcf_price_ratio else "N/A", help=f"自由現金流佔股價比例：{fcf_price_ratio:.1%}，{fcf_price_text}" if fcf_price_ratio == fcf_price_ratio else "N/A")

        fcf_growth = d.get("fcf_growth", 0) * 100
        fcf_growth_text = ":red[高成長]" if fcf_growth > 15 else ":orange[有成長]" if fcf_growth > 0 else ":green[成長偏弱或衰退]"
        f3.metric("FCF成長率", f"{fcf_growth:.1f}%" if fcf_growth == fcf_growth else "N/A", help=f"自由現金流年成長率：{fcf_growth:.1f}%，{fcf_growth_text}" if fcf_growth == fcf_growth else "N/A")

        payout_ratio = d.get("payout_ratio", 0) * 100
        payout_text = ":red[配發偏高，留存較少]" if payout_ratio > 70 else ":orange[配發合理]" if payout_ratio > 30 else ":green[配發偏低，留存較高]"
        f4.metric("盈餘配發率", f"{payout_ratio:.1f}%", help=f"盈餘配發率：{payout_ratio:.1f}%，{payout_text}")

        st.write("說明：")
        st.write("• 若「自由現金流/股價」為正，表示每單位股價背後有實質現金支撐。")
        st.write("• 若「盈餘配發率」接近 100%，代表公司多數盈餘用於配股，現金流留存較少。")
