import streamlit as st

from core.data_fetcher import get_all_names, get_deep_analysis_data
from core.ai_analysis import get_ai_analysis_report
from ui.overview import render_overview
from ui.fundamentals import render_fundamentals, render_financial_structure
from ui.technicals import render_technicals
from ui.cashflow import render_cashflow_section


st.set_page_config(
    page_title="台股深度分析",
    layout="wide",
    page_icon="📈",
)

st.markdown("""
<style>
h1 {
    color: #34495E !important;
    font-size: 1.9rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.4rem !important;
    margin-top: 0.1rem !important;
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    letter-spacing: -0.02em !important;
}
h2 {
    color: #0095FF !important;
    font-size: 1.7rem !important;
    font-weight: 600 !important;
    margin-top: 0.7rem !important;
    margin-bottom: 0.3rem !important;
    padding-top: 0.2rem !important;
    padding-bottom: 0.2rem !important;
}
h3 {
    color: #E67E22 !important;
    font-size: 1.35rem !important;
    font-weight: 500 !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.2rem !important;
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
    border-left: 4px solid #E67E22 !important;
    padding-left: 0.5rem !important;
}
.element-container p {
    color: #333333 !important;
    font-size: 0.95rem !important;
    line-height: 1.4 !important;
    margin: 0.2rem 0 !important;
}
</style>
""", unsafe_allow_html=True)

name_map = get_all_names()

st.sidebar.markdown("### 📈 **台股深度分析**")
st.sidebar.markdown("---")
code_input = st.sidebar.text_input("🔍 輸入台股代碼", placeholder="2330").strip().upper()

with st.sidebar:
    st.caption("資料來源：Yahoo Finance / 台灣證交所 ISIN")
    if st.button("🧹 清除快取"):
        st.cache_data.clear()
        st.success("已清除快取，請重新輸入股票代碼。")

if code_input:
    with st.spinner(f"🔄 分析 {code_input} 資料中..."):
        d = get_deep_analysis_data(code_input, name_map)

    if d:
        st.title(f"📊 {d.get('name', code_input)} ({code_input})")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 總覽",
    "📌 基本面",
    "📉 技術面",
    "🏦 財報表",
    "💵 現金流 / 股利",
    "🤖 AI診斷",
])

        with tab1:
            render_overview(d, code_input)

        with tab2:
            render_fundamentals(d)
            st.divider()
            render_financial_structure(d)

        with tab3:
            render_technicals(d)

        with tab4:
            render_cashflow_section(d)

        with tab5:
            st.header("🤖 五、AI診斷")
            api_status = st.secrets.get("GEMINI_API_KEY", "")
            col1, col2 = st.columns([1, 4])

            with col1:
                status_icon = "🟢 已連線" if api_status else "🔴 未連線"
                st.caption(f"**{status_icon}**")

            with col2:
                st.caption("**Gemini 2.5 Flash**")

            if st.button("🚀 啟動 AI 深度診斷", type="primary", use_container_width=True):
                if api_status:
                    with st.spinner(f"🤖 AI 分析 {d['name']}..."):
                        report = get_ai_analysis_report(d, code_input, api_status)
                        st.markdown("### 📋 **AI 終極投資報告**")
                        st.markdown("---")
                        st.markdown(report)
                        st.balloons()
                        st.success("✅ AI 診斷完成！")
                else:
                    st.error("🔧 請先在 Streamlit Cloud 設定 Secrets：App Settings → Secrets → GEMINI_API_KEY")
    else:
        st.warning("找不到該股票資料，請確認股票代碼是否正確。")
else:
    st.info("✅ 這是 Raymond 的台股深度分析，請輸入正確的股票代碼。")

