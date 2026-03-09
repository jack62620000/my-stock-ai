import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.valuation import calc_fair_price, calc_margin_of_safety


def _resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    agg_map = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }

    out = df.resample(freq).agg(agg_map)

    for col in ["ma5", "ma10", "ma20", "ma60", "mv5", "mv20"]:
        if col in df.columns:
            out[col] = df[col].resample(freq).last()

    return out.dropna(subset=["Open", "High", "Low", "Close"])


def _fmt_num(v, digits=1, suffix=""):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}{suffix}"


def render_overview(d, code_input):
    df = d.get("df", pd.DataFrame())
    price = d.get("price", 0)
    position_52 = d.get("position_52", float("nan"))
    fair_price = calc_fair_price(d)
    margin = calc_margin_of_safety(d)

    st.markdown(
        """
        <style>
        .quote-card {
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 14px;
        }
        .quote-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #222;
            margin-bottom: 10px;
        }
        .quote-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(90px, 1fr));
            gap: 12px 16px;
            margin-top: 8px;
            margin-bottom: 6px;
        }
        .quote-item {
            padding: 4px 0;
        }
        .quote-label {
            font-size: 0.96rem;
            color: #666;
            margin-bottom: 4px;
        }
        .quote-value {
            font-size: 1.55rem;
            font-weight: 700;
            color: #111;
            line-height: 1.2;
        }
        .ma-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(90px, 1fr));
            gap: 10px 16px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #f0f0f0;
        }
        .ma-item {
            font-size: 1.08rem;
            color: #222;
            line-height: 1.35;
            font-weight: 600;
        }
        .ma-label {
            color: #777;
            font-size: 0.90rem;
            display: block;
            margin-bottom: 2px;
            font-weight: 400;
        }
        .mini-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(90px, 1fr));
            gap: 10px 14px;
            margin-bottom: 14px;
        }
        .mini-card {
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 12px;
            padding: 10px 14px;
        }
        .mini-label {
            font-size: 0.88rem;
            color: #666;
        }
        .mini-value {
            font-size: 1.20rem;
            font-weight: 700;
            color: #111;
            margin-top: 2px;
        }
        .toolbar-wrap {
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 12px;
            padding: 10px 14px 2px 14px;
            margin: 10px 0 14px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ===== 上方摘要小卡 =====
    summary_html = f"""
    <div class="mini-metrics">
        <div class="mini-card">
            <div class="mini-label">即時股價</div>
            <div class="mini-value">{_fmt_num(price, 1)}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">漲跌額</div>
            <div class="mini-value">{_fmt_num(d.get('price_change_amount', 0), 1)}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">漲跌幅</div>
            <div class="mini-value">{_fmt_num(d.get('price_change', 0), 1, '%')}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">52週位置</div>
            <div class="mini-value">{_fmt_num(position_52 * 100, 1, '%') if pd.notna(position_52) else 'N/A'}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">EPS</div>
            <div class="mini-value">{_fmt_num(d.get('eps'), 2)}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">本益比(P/E)</div>
            <div class="mini-value">{_fmt_num(d.get('pe'), 1, 'x')}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">估算合理價</div>
            <div class="mini-value">{_fmt_num(fair_price, 1)}</div>
        </div>
        <div class="mini-card">
            <div class="mini-label">安全邊際</div>
            <div class="mini-value">{_fmt_num(margin * 100, 1, '%') if pd.notna(margin) else 'N/A'}</div>
        </div>
    </div>
    """
    st.markdown(summary_html, unsafe_allow_html=True)

    if df.empty:
        st.warning("沒有K線資料")
        return

    # ===== 切換列（只保留這一組） =====
    toolbar_left, toolbar_right = st.columns([2, 2])

    with toolbar_left:
        period_type = st.radio(
            "K線週期",
            ["日", "週", "月"],
            horizontal=True,
            index=0,
            key=f"period_type_toolbar_{code_input}",
        )

    with toolbar_right:
        window_size = st.radio(
            "顯示根數",
            [30, 60, 120],
            horizontal=True,
            index=1,
            key=f"window_size_toolbar_{code_input}",
        )

    # ===== 週期轉換 =====
    chart_df = df.copy()
    if period_type == "週":
        chart_df = _resample_ohlcv(chart_df, "W")
    elif period_type == "月":
        chart_df = _resample_ohlcv(chart_df, "M")

    if chart_df.empty:
        st.warning("該週期沒有資料")
        return

    session_key = f"chart_start_{code_input}_{period_type}_{window_size}"
    if session_key not in st.session_state:
        st.session_state[session_key] = max(len(chart_df) - window_size, 0)

    max_start = max(len(chart_df) - window_size, 0)
    start_idx = min(st.session_state[session_key], max_start)
    st.session_state[session_key] = start_idx

    visible_df = chart_df.iloc[start_idx:start_idx + window_size].copy()

    if visible_df.empty:
        st.warning("目前視窗內沒有資料")
        return

    # ===== 報價資訊列 =====
    last_row = visible_df.iloc[-1]
    open_p = last_row["Open"]
    high_p = last_row["High"]
    low_p = last_row["Low"]
    close_p = last_row["Close"]
    vol = last_row["Volume"]

    prev_close = visible_df["Close"].iloc[-2] if len(visible_df) >= 2 else close_p
    change = close_p - prev_close

    ma5_val = visible_df["ma5"].iloc[-1] if "ma5" in visible_df.columns else float("nan")
    ma10_val = visible_df["ma10"].iloc[-1] if "ma10" in visible_df.columns else float("nan")
    ma20_val = visible_df["ma20"].iloc[-1] if "ma20" in visible_df.columns else float("nan")
    ma60_val = visible_df["ma60"].iloc[-1] if "ma60" in visible_df.columns else float("nan")
    mv5_val = visible_df["mv5"].iloc[-1] if "mv5" in visible_df.columns else float("nan")
    mv20_val = visible_df["mv20"].iloc[-1] if "mv20" in visible_df.columns else float("nan")

    quote_html = f"""
    <div class="quote-card">
        <div class="quote-title">{d.get('name', code_input)} ({code_input})</div>

        <div class="quote-grid">
            <div class="quote-item">
                <div class="quote-label">日期</div>
                <div class="quote-value">{last_row.name.strftime("%Y/%m/%d")}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">開盤價</div>
                <div class="quote-value">{_fmt_num(open_p, 0)}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">最高價</div>
                <div class="quote-value">{_fmt_num(high_p, 0)}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">最低價</div>
                <div class="quote-value">{_fmt_num(low_p, 0)}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">收盤價</div>
                <div class="quote-value">{_fmt_num(close_p, 0)}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">成交量(股)</div>
                <div class="quote-value">{int(vol):,}</div>
            </div>
            <div class="quote-item">
                <div class="quote-label">漲跌</div>
                <div class="quote-value">{_fmt_num(change, 0)}</div>
            </div>
        </div>

        <div class="ma-grid">
            <div class="ma-item"><span class="ma-label">MA5</span>{_fmt_num(ma5_val, 1)}</div>
            <div class="ma-item"><span class="ma-label">MA10</span>{_fmt_num(ma10_val, 1)}</div>
            <div class="ma-item"><span class="ma-label">MA20</span>{_fmt_num(ma20_val, 1)}</div>
            <div class="ma-item"><span class="ma-label">MA60</span>{_fmt_num(ma60_val, 1)}</div>
            <div class="ma-item"><span class="ma-label">MV5</span>{_fmt_num(mv5_val, 1)}</div>
            <div class="ma-item"><span class="ma-label">MV20</span>{_fmt_num(mv20_val, 1)}</div>
        </div>
    </div>
    """
    st.markdown(quote_html, unsafe_allow_html=True)

    # ===== 自動Y軸 =====
    visible_high = visible_df["High"].max()
    visible_low = visible_df["Low"].min()
    price_padding = (
        (visible_high - visible_low) * 0.04
        if visible_high != visible_low
        else visible_high * 0.03
    )
    y_min = visible_low - price_padding
    y_max = visible_high + price_padding

    # ===== 圖表 =====
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.80, 0.20],
    )

    fig.add_trace(
        go.Candlestick(
            x=visible_df.index,
            open=visible_df["Open"],
            high=visible_df["High"],
            low=visible_df["Low"],
            close=visible_df["Close"],
            name="K線",
            increasing_line_width=1.4,
            decreasing_line_width=1.4,
        ),
        row=1, col=1
    )

    line_map = [
        ("ma5", "MA5"),
        ("ma10", "MA10"),
        ("ma20", "MA20"),
        ("ma60", "MA60"),
    ]

    for col, label in line_map:
        if col in visible_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=visible_df.index,
                    y=visible_df[col],
                    mode="lines",
                    name=label,
                    line=dict(width=1.8),
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

    if "mv5" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["mv5"],
                mode="lines",
                name="MV5",
                line=dict(width=1.2),
            ),
            row=2, col=1
        )

    if "mv20" in visible_df.columns:
        fig.add_trace(
            go.Scatter(
                x=visible_df.index,
                y=visible_df["mv20"],
                mode="lines",
                name="MV20",
                line=dict(width=1.2),
            ),
            row=2, col=1
        )

    fig.update_layout(
        title=None,
        height=720,
        xaxis_rangeslider_visible=False,
        dragmode=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0
        ),
        margin=dict(l=10, r=10, t=10, b=10),
    )

    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)

    # ===== 左右按鈕在圖左右 =====
    wrap_left, wrap_center, wrap_right = st.columns([0.9, 6.2, 0.9])

    with wrap_left:
        st.write("")
        st.write("")
        if st.button("⬅ 更早", use_container_width=True, key=f"left_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = max(
                0,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) - 10
            )
            st.rerun()

    with wrap_center:
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "scrollZoom": False
            }
        )

    with wrap_right:
        st.write("")
        st.write("")
        if st.button("更新 ➡", use_container_width=True, key=f"right_btn_{code_input}_{period_type}_{window_size}"):
            st.session_state[session_key] = min(
                max_start,
                st.session_state.get(session_key, max(len(chart_df) - window_size, 0)) + 10
            )
            st.rerun()

    st.caption(
        f"目前顯示區間：{visible_df.index[0].strftime('%Y-%m-%d')} ～ {visible_df.index[-1].strftime('%Y-%m-%d')}"
    )

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
