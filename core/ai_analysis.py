import streamlit as st
import google.generativeai as genai


@st.cache_data(ttl=86400)
def get_ai_analysis_report(d, code, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-2.5-flash")

        eps = d.get("eps", 0)
        pe = d.get("pe", 0)
        roe = d.get("roe", 0)
        rsi = d.get("rsi", 50)
        price = d.get("price", 0)

        prompt = f"""針對 {d['name']} ({code})：
現價 {round(price, 1)} 元，EPS {round(eps, 2)}，本益比 {round(pe, 1)}，ROE {round(roe*100, 1)}%
RSI {round(rsi, 1)}，技術面多空由 MA5 / MA20 / MA60 趨勢判斷。

請依序回答：
1. 🌍 全球與產業局勢影響
2. 💎 公司護城河與基本面健康度
3. 📉 基本面與技術面綜合判斷
4. 🎯 合理價與目標價區間
5. 📈 投資建議與風險提示
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"⚠️ AI 錯誤：{str(e)[:120]}"
