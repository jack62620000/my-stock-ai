import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai
from datetime import datetime

# ===============================
# 1. 核心設定與 API 初始化
# ===============================
st.set_page_config(page_title="量化數據決策終端", layout="wide")

# 檢查 Secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ 請在 Streamlit Secrets 設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 自動取得可用模型清單
@st.cache_resource
def get_available_models():
    try:
        models = client.models.list()
        # 遍歷模型，篩選出支援生成內容且包含 gemini 字樣的模型
        gemini_models = [m.name for m in models if "gemini" in m.name.lower()]
        # 優先排序 flash 系列
        gemini_models.sort(key=lambda x: ("flash" not in x.lower()))
        return gemini_models
    except:
        # 若自動偵測失敗，提供穩定備案
        return ["gemini-2.0-flash", "gemini-1.5-flash"]

AVAILABLE_MODELS = get_available_models()

# ===============================
# 2. 數據處理模組 (精簡化)
# ===============================
@st.cache_data(ttl=3600)
def get_clean_quant_data(stock_id: str):
    # 自動處理台股後綴
    if not (stock_id.endswith(".TW") or stock_id.endswith(".TWO")):
        ticker_id = f"{stock_id}.TW"
    else:
        ticker_id = stock_id

    try:
        ticker = yf.Ticker(ticker_id)
        df = ticker.history(period="1y")
        if df.empty: return None, None
        
        # 技術指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA20'] = ta.sma(df['Close'], length=20)
        
        info = ticker.info
        
        # 殖利率邏輯修正 (處理百分比單位)
        dy = info.get("dividendYield", 0) or 0
        dy_pct = dy if dy > 1 else dy * 100
        
        # 1. 核心指標 (精簡至小數點後 2 位)
        metrics = {
            "名稱": info.get("shortName", "未知"),
            "現價": round(df['Close'].iloc[-1], 2),
            "本益比 PE": round(info.get("trailingPE", 0) or 0, 2),
            "淨值比 PB": round(info.get("priceToBook", 0) or 0, 2),
            "殖利率 (%)": round(dy_pct, 2),
            "RSI14": round(df['RSI'].iloc[-1], 2) if not df['RSI'].empty else 0,
            "乖離率 (%)": round(((df['Close'].iloc[-1] / df['MA20'].iloc[-1]) - 1) * 100, 2) if not df['MA20'].empty else 0
        }
        
        # 2. 歷史交易明細 (清洗日期與小數點)
        recent_history = df.tail(10).copy()
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        recent_history = recent_history[['Open', 'High', 'Low', 'Close', 'Volume']].round(2)
        
        return metrics, recent_history
    except:
        return None, None

# ===============================
# 3. UI 佈局設計
# ===============================
st.title("🛡️ 量化價值決策核心")

with st.sidebar:
    st.header("數據檢索參數")
    stock_input = st.text_input("輸入台股代號 (例: 2330)", value="2330")
    
    if AVAILABLE_MODELS:
        default_model = st.selectbox("首選 AI 模型", AVAILABLE_MODELS)
    
    run_btn = st.button("啟動量化分析", type="primary")
    st.divider()
    st.caption("開發者備註：本系統僅供參考，投資請謹慎評估。")

if run_btn:
    data, history = get_clean_quant_data(stock_input)
    
    if data:
        # A. 核心指標看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("目前股價", f"{data['現價']}")
        c2.metric("本益比 PE", f"{data['本益比 PE']}")
        c3.metric("淨值比 PB", f"{data['淨值比 PB']}")
        c4.metric("殖利率 (%)", f"{data['殖利率 (%)']}%")

        st.divider()

        # B. AI 首席決策總結 (優先呈現)
        st.subheader("🤖 AI 首席決策總結")
        
        prompt = f"""
        你是精通價值投資的量化專家。分析台股 {data['名稱']}({stock_input}):
        現價: {data['現價']}, PE: {data['本益比 PE']}, PB: {data['淨值比 PB']}, 
        殖利率: {data['殖利率 (%)']}%, RSI14: {data['RSI14']}。
        請給出明確結論：1. 投資評等(買進/觀望/賣出) 2. 核心分析理由 3. 操作建議區間。
        """

        summary_placeholder = st.empty()
        summary_placeholder.info("⏳ AI 正在計算安全邊際並生成報告...")

        # 模型輪詢邏輯
        success = False
        try_models = [default_model] + [m for m in AVAILABLE_MODELS if m != default_model]
        
        for m_name in try_models:
            try:
                response = client.models.generate_content(model=m_name, contents=prompt)
                summary_placeholder.success(f"【推薦建議 - 由 {m_name} 生成】\n\n{response.text}")
                success = True
                break
            except Exception as e:
                if "429" in str(e): continue # 額度耗盡則試下一個
                continue
        
        if not success:
            summary_placeholder.error("❌ 目前所有 AI 模型額度皆已耗盡，請一分鐘後再試。")

        st.divider()

        # C. 精簡數據表格
        col_metrics, col_history = st.columns([1, 2])
        
        with col_metrics:
            st.subheader("📋 詳細指標")
            # 轉換為簡潔的垂直表格
            metrics_df = pd.DataFrame([data]).T.rename(columns={0: "數值"})
            st.table(metrics_df)
            
        with col_history:
            st.subheader("📅 近 10 日交易明細")
            # 格式化 Volume 加上千分位，提高閱讀性
            st.dataframe(history.style.format({
                'Open': '{:.2f}', 'High': '{:.2f}', 'Low': '{:.2f}', 
                'Close': '{:.2f}', 'Volume': '{:,.0f}'
            }), use_container_width=True)
            
    else:
        st.error("❌ 抓取不到數據。請確認代號（例：2330 或 2356）是否正確。")
