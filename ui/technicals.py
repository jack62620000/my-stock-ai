import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.technical_analysis import get_volume_trend


def render_technicals(d):
    st.header("📉 二、技術面：股價趨勢與強度")

    df = d.get("df", pd.DataFrame())
    if df.empty:
        st.warning("沒有技術面資料")
        return

    latest = df.iloc[-1]
    price = d.get("price", 0)

    with st.container(border=True):
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
        ))

        fig.add_trace(go.Scatter(x=df.index, y=df["ma5"], mode="lines", name="MA5"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ma20"], mode="lines", name="MA20"))
        fig.add_trace(go.Scatter(x=df.index, y=df["ma60"], mode="lines", name="MA60"))

        fig.update_layout(height=520, xaxis_rangeslider_visible=False, legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)

        t1, t2, t3, t4 = st.columns(4)

        t1.subheader("趨勢與均線")
        ma5 = latest.get("ma5", price)
        ma20 = latest.get("ma20", price)
        ma60 = latest.get("ma60", price)
        bias = d.get("bias", 0)

        t1.metric("MA5", f"{ma5:.1f} ({':red[多頭]' if price > ma5 else ':green[空頭]'})")
        t1.metric("MA20", f"{ma20:.1f} ({':red[多頭]' if price > ma20 else ':green[空頭]'})")
        t1.metric("MA60", f"{ma60:.1f} ({':red[多頭]' if price > ma60 else ':green[空頭]'})")

        bias_text = ":red[偏離太大⚠️]" if bias > 10 else ":green[偏離太小⭐️]" if bias < -10 else ":orange[合理🟡]"
        t1.metric("乖離率", f"{bias:.1f}% ({bias_text})")

        t2.subheader("動能與強度")
        rsi = d.get("rsi", 50)
        rsi_text = "過熱🔴" if rsi > 70 else "過冷🟢" if rsi < 30 else "中性🟡"

        macd_line = df["macd"].iloc[-1] if "macd" in df.columns else 0.0
        macd_signal = df["macd_signal"].iloc[-1] if "macd_signal" in df.columns else 0.0

        t2.metric("RSI", f"{rsi:.1f} ({rsi_text})")
        t2.metric("MACD 本體", f"{macd_line:+.2f} ({':red[多頭]' if macd_line > macd_signal else ':green[空頭]'})")
        t2.metric("MACD 信號線", f"{macd_signal:+.2f} ({':red[多頭]' if macd_signal > 0 else ':green[空頭]'})")

        t3.subheader("波動與區間")
        bb_upper = d.get("bb_upper", 0)
        bb_mid = d.get("bb_mid", 0)
        bb_lower = d.get("bb_lower", 0)
        high_52 = d.get("high_52", 0)
        low_52 = d.get("low_52", 0)
        std_20 = df["std"].iloc[-1] if "std" in df.columns else 0.0
        atr = d.get("atr", 0)

        t3.metric("布林上軌", f"{bb_upper:.1f}")
        t3.metric("布林中軌", f"{bb_mid:.1f}")
        t3.metric("布林下軌", f"{bb_lower:.1f}")
        t3.metric("52週高價", f"{high_52:.1f}")
        t3.metric("52週低價", f"{low_52:.1f}")
        t3.metric("標準差(20日)", f"{std_20:.2f}")
        t3.metric("ATR(14日)", f"{atr:.2f}")

        t4.subheader("成交量與量價關係")
        volume = latest["Volume"] if "Volume" in latest else 0
        vol_price_text = get_volume_trend(df, d.get("price_change", 0))

        t4.metric("今日成交量", f"{int(volume / 1000):,} 張")
        t4.metric("量價關係", vol_price_text)

        vol_fig = go.Figure()
        vol_fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量"))
        vol_fig.update_layout(height=260, showlegend=False)
        st.plotly_chart(vol_fig, use_container_width=True)
