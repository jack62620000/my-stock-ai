import streamlit as st


def render_cache_tools():
    with st.sidebar:
        if st.button("🧹 清除快取"):
            st.cache_data.clear()
            st.success("已清除快取")
