import streamlit as st


def render_fundamentals(d):
    st.header("📌 一、基本面：公司賺不賺錢")

    with st.container(border=True):
        st.subheader("盈利能力")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

        gp = d.get("gross_profit", 0) * 100
        gp_text = ":red[偏高⭐️]" if gp > 30 else ":orange[合理🟡]" if gp >= 20 else ":green[偏低⚠️]"
        c1.metric("毛利率", f"{gp:.1f}% ({gp_text})")

        nm = d.get("net_margin", 0) * 100
        nm_text = ":red[偏高⭐️]" if nm > 8 else ":orange[合理🟡]" if nm >= 4 else ":green[偏低⚠️]"
        c2.metric("淨利率", f"{nm:.1f}% ({nm_text})")

        om = d.get("op_margin", 0) * 100
        om_text = ":red[偏高⭐️]" if om > 10 else ":orange[合理🟡]" if om >= 5 else ":green[偏低⚠️]"
        c3.metric("營業利益率", f"{om:.1f}% ({om_text})")

        eps = d.get("eps", 0)
        eps_text = ":red[偏高⭐️]" if eps > 3 else ":orange[合理🟡]" if eps >= 1.5 else ":green[偏低⚠️]"
        c4.metric("EPS", f"{eps:.2f} ({eps_text})")

        roe = d.get("roe", 0) * 100
        roe_text = ":red[偏高⭐️]" if roe > 15 else ":orange[合理🟡]" if roe >= 10 else ":green[偏低⚠️]"
        c5.metric("ROE", f"{roe:.1f}% ({roe_text})")

        roa = d.get("roa", 0) * 100
        roa_text = ":red[偏高⭐️]" if roa > 8 else ":orange[合理🟡]" if roa >= 4 else ":green[偏低⚠️]"
        c6.metric("ROA", f"{roa:.1f}% ({roa_text})")

        eps_growth = d.get("eps_growth", 0) * 100
        eps_growth_text = ":red[偏高⭐️]" if eps_growth > 10 else ":orange[合理🟡]" if eps_growth >= 0 else ":green[偏低⚠️]"
        c7.metric("EPS 成長率", f"{eps_growth:.1f}% ({eps_growth_text})")

        st.subheader("成長性")
        g1, g2, g3, g4, g5, g6, g7 = st.columns(7)

        rev_growth = d.get("rev_growth", 0) * 100
        rev_text = ":red[偏高⭐️]" if rev_growth > 10 else ":orange[合理🟡]" if rev_growth >= 0 else ":green[偏低⚠️]"
        g1.metric("營收成長率", f"{rev_growth:.1f}% ({rev_text})")

        g2.metric("EPS 成長率", f"{eps_growth:.1f}% ({eps_growth_text})")

        net_income_growth = d.get("net_income_growth", 0) * 100
        net_income_text = ":red[偏高⭐️]" if net_income_growth > 10 else ":orange[合理🟡]" if net_income_growth >= 0 else ":green[偏低⚠️]"
        g3.metric("淨利成長率", f"{net_income_growth:.1f}% ({net_income_text})")

        gross_profit_growth = d.get("gross_profit_growth", 0) * 100
        gross_profit_text = ":red[偏高⭐️]" if gross_profit_growth > 10 else ":orange[合理🟡]" if gross_profit_growth >= 0 else ":green[偏低⚠️]"
        g4.metric("毛利成長率", f"{gross_profit_growth:.1f}% ({gross_profit_text})")

        op_income_growth = d.get("operating_income_growth", 0) * 100
        op_income_text = ":red[偏高⭐️]" if op_income_growth > 10 else ":orange[合理🟡]" if op_income_growth >= 0 else ":green[偏低⚠️]"
        g5.metric("營業利益成長率", f"{op_income_growth:.1f}% ({op_income_text})")

        assets_growth = d.get("assets_growth", 0) * 100
        assets_text = ":red[偏高⭐️]" if assets_growth > 5 else ":orange[合理🟡]" if assets_growth >= 0 else ":green[偏低⚠️]"
        g6.metric("資產成長率", f"{assets_growth:.1f}% ({assets_text})")

        equity_growth = d.get("equity_growth", 0) * 100
        equity_text = ":red[偏高⭐️]" if equity_growth > 8 else ":orange[合理🟡]" if equity_growth >= 0 else ":green[偏低⚠️]"
        g7.metric("權益成長率", f"{equity_growth:.1f}% ({equity_text})")

        st.subheader("估值水準")
        v1, v2, v3, v4, v5, v6, v7 = st.columns(7)

        pe = d.get("pe", 0)
        pe_text = ":green[偏高估⚠️]" if pe > 20 else ":orange[合理🟡]" if pe >= 10 else ":red[偏低估⭐️]"
        v1.metric("本益比(P/E)", f"{pe:.1f}x ({pe_text})" if pe == pe else "N/A")

        pb = d.get("pb", 0)
        pb_text = ":green[偏高估⚠️]" if pb > 3 else ":orange[合理🟡]" if pb >= 1 else ":red[偏低估⭐️]"
        v2.metric("股價淨值比(P/B)", f"{pb:.1f}x ({pb_text})" if pb == pb else "N/A")

        peg = d.get("peg", 0)
        peg_text = ":green[偏高估⚠️]" if peg > 1.5 else ":orange[合理🟡]" if peg >= 1.0 else ":red[偏低估⭐️]"
        v3.metric("PEG", f"{peg:.1f} ({peg_text})" if peg == peg else "N/A")

        div_yield = d.get("dividend_yield", 0) * 100
        div_text = ":red[偏高⭐️]" if div_yield > 5 else ":orange[合理🟡]" if div_yield >= 2 else ":green[偏低⚠️]"
        v4.metric("股利殖利率", f"{div_yield:.1f}% ({div_text})")

        payout_ratio = d.get("payout_ratio", 0) * 100
        payout_text = ":red[偏高⭐️]" if payout_ratio > 70 else ":orange[合理🟡]" if payout_ratio >= 30 else ":green[偏低⚠️]"
        v5.metric("盈餘配發率", f"{payout_ratio:.1f}% ({payout_text})")

        cash_dividend_yield = d.get("cash_dividend_yield", 0) * 100
        cd_text = ":red[偏高⭐️]" if cash_dividend_yield > 5 else ":orange[合理🟡]" if cash_dividend_yield >= 2 else ":green[偏低⚠️]"
        v6.metric("現金股利報酬率", f"{cash_dividend_yield:.1f}% ({cd_text})")

        book_value_growth = d.get("book_value_growth", 0) * 100
        bv_text = ":red[偏高⭐️]" if book_value_growth > 8 else ":orange[合理🟡]" if book_value_growth >= 0 else ":green[偏低⚠️]"
        v7.metric("帳面價值成長率", f"{book_value_growth:.1f}% ({bv_text})")


def render_financial_structure(d):
    st.header("🏦 三、財務與資本結構：公司資本是否健康")

    with st.container(border=True):
        f1, f2, f3, f4, f5, f6, f7 = st.columns(7)

        debt_ratio = d.get("debt_ratio", 0) * 100
        debt_text = ":red[低風險⭐️]" if debt_ratio < 50 else ":orange[中等🟡]" if debt_ratio <= 70 else ":green[高風險⚠️]"
        f1.metric("負債比率", f"{debt_ratio:.1f}% ({debt_text})")

        debt_to_equity = d.get("debt_to_equity", 0) * 100
        dte_text = ":red[低風險⭐️]" if debt_to_equity < 50 else ":orange[中等🟡]" if debt_to_equity <= 100 else ":green[高風險⚠️]"
        f2.metric("負債/股東權益", f"{debt_to_equity:.1f}% ({dte_text})")

        current_ratio = d.get("current_ratio", 0)
        current_text = ":red[偏高⭐️]" if current_ratio > 2 else ":orange[合理🟡]" if current_ratio >= 1 else ":green[偏低⚠️]"
        f3.metric("流動比率", f"{current_ratio:.2f} ({current_text})")

        quick_ratio = d.get("quick_ratio", 0)
        quick_text = ":red[偏高⭐️]" if quick_ratio > 1.5 else ":orange[合理🟡]" if quick_ratio >= 0.7 else ":green[偏低⚠️]"
        f4.metric("速動比率", f"{quick_ratio:.2f} ({quick_text})")

        inv_asset_ratio = d.get("inv_asset_ratio", 0)
        inv_text = ":green[偏高⚠️]" if inv_asset_ratio > 0.5 else ":orange[合理🟡]" if inv_asset_ratio >= 0.2 else ":red[偏低⭐️]"
        f5.metric("存貨佔資產比", f"{inv_asset_ratio:.1%} ({inv_text})")

        cash_asset_ratio = d.get("cash_asset_ratio", 0)
        cash_text = ":red[偏高⭐️]" if cash_asset_ratio > 0.1 else ":orange[合理🟡]" if cash_asset_ratio >= 0.05 else ":green[偏低⚠️]"
        f6.metric("現金佔資產比", f"{cash_asset_ratio:.1%} ({cash_text})")

        ncd_liabilities_ratio = d.get("ncd_liabilities_ratio", 0)
        ncd_text = ":green[偏高⚠️]" if ncd_liabilities_ratio > 0.8 else ":orange[合理🟡]" if ncd_liabilities_ratio >= 0.5 else ":red[偏低⭐️]"
        f7.metric("非流動負債占負債比", f"{ncd_liabilities_ratio:.1%} ({ncd_text})")

        st.markdown("---")

        s1, s2, s3, s4 = st.columns(4)
        total_assets = d.get("total_assets", 0)
        total_liabilities = d.get("total_liabilities", 0)
        equity = d.get("equity", 0)
        capex = d.get("capex", 0)

        s1.metric("總資產", f"{total_assets / 1e9:.1f} 億" if total_assets == total_assets else "N/A")
        s2.metric("總負債", f"{total_liabilities / 1e9:.1f} 億" if total_liabilities == total_liabilities else "N/A")
        s3.metric("股東權益", f"{equity / 1e9:.1f} 億" if equity == equity else "N/A")
        s4.metric("資本支出(Capex)", f"{capex / 1e8:.1f} 億" if capex == capex else "N/A")
