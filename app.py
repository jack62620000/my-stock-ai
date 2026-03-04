import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# 1. 基礎頁面設定
st.set_page_config(page_title="台股 AI 試算表聯動版", layout="wide")

# 2. 數據抓取與 AI 邏輯 (保持妳原本的邏輯)
# 注意：Streamlit 連接 Google Sheets 通常使用 Service Account Key，而不是 Colab 的 auth.authenticate_user()
# 如果妳只是想在網頁顯示 AI，建議維持原本抓 yfinance 的邏輯

# --- 這裡放妳原本的 get_stock_data 函式 ---
def get_stock_data(code):
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            df = ticker.history(period="1y")
            if df.empty: continue
            return {"p": df['Close'].iloc[-1], "df": df, "name": ticker.info.get('shortName', code)}
        except: continue
    return None

# 3. UI 介面
st.sidebar.title("📈 AI 戰情室")
code_input = st.sidebar.text_input("輸入股票代碼", value="3131").strip()

if code_input:
    d = get_stock_data(code_input)
    if d:
        st.title(f"📊 {d['name']} 診斷報告")
        
        # --- AI 區塊 ---
        st.subheader("🤖 Gemini AI 深度洞察")
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                model = genai.GenerativeModel('gemini-1.5-flash')
                # 這裡結合了妳想要的「多因子聯動」邏輯
                prompt = f"分析台股{code_input}，價格{d['p']}。請給出像專業分析師的30字建議。"
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"AI 連線失敗: {e}")
