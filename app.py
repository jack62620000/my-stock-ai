import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- 1. 模擬數據 (保證這段不報錯) ---
def get_final_data():
    dates = pd.bdate_range(start='2024-01-01', periods=100)
    df = pd.DataFrame({
        'Date': dates,
        'Close': (500 + np.random.randn(100).cumsum() * 5).round(1)
    })
    df['Open'] = (df['Close'] + np.random.uniform(-5, 5, 100)).round(1)
    df['High'] = df[['Open', 'Close']].max(axis=1) + 2
    df['Low'] = df[['Open', 'Close']].min(axis=1) - 2
    # 台股配色邏輯
    df['Color'] = np.where(df['Close'] >= df['Open'], '#EB3B3B', '#26A69A')
    # 只取最後 30 筆數據 (視窗減半)
    return df.tail(30)

try:
    df = get_final_data()

    st.title("🛡️ 最終防線：原生鎖定圖表")
    st.info("這張圖表使用原生 Altair 渲染，已經「物理切除」了所有拖曳與縮放功能，視窗死鎖在最後 30 根 K 線，絕對拉不出空白。")

    # --- 2. 建立 Altair 圖表 ---
    # 設定畫布大小
    base = alt.Chart(df).encode(
        x=alt.X('Date:T', title='', axis=alt.Axis(format='%m/%d', grid=False)),
        color=alt.Color('Color:N', scale=None)
    ).properties(width='container', height=400)

    # 繪製 K 線的影線 (High/Low)
    rule = base.mark_rule().encode(
        y=alt.Y('Low:Q', title='價格', scale=alt.Scale(zero=False)),
        y2='High:Q'
    )

    # 繪製 K 線的實體 (Open/Close)
    bar = base.mark_bar().encode(
        y='Open:Q',
        y2='Close:Q'
    )

    # 組合圖表 (注意：這裡不加上 .interactive()，所以它無法被拖動)
    chart = (rule + bar).configure_view(strokeWidth=0)

    # --- 3. 顯示 ---
    st.altair_chart(chart, use_container_width=True)

except Exception as e:
    st.error(f"發生錯誤：{e}")
    st.write("請確保你的 requirements.txt 包含 streamlit, pandas, numpy")
