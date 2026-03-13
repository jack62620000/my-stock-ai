import streamlit as st
from google import genai

st.set_page_config(
    page_title="Gemini API Key 測試工具",
    layout="centered"
)

st.title("🤖 Gemini API Key 測試工具")

st.info("請輸入你在 Google AI Studio 生成的 GEMINI API Key")

# 1️⃣ 輸入 API Key
api_key = st.text_input("GEMINI_API_KEY", type="password")

if api_key:
    try:
        client = genai.Client(api_key=api_key)

        # 2️⃣ 列出可用模型
        st.info("正在列出帳號可用 Gemini 模型...")
        models = client.models.list()

        if not models:
            st.error("❌ 此 API Key 沒有任何可用的 Gemini 模型。")
        else:
            st.success(f"✅ 找到 {len(models)} 個可用模型")
            for m in models:
                st.write(f"- {m.name}")

            # 3️⃣ 測試生成文字
            st.info("正在嘗試生成測試文字...")
            test_model = models[0].name
            prompt = "請用一句話說明台灣股市今日行情。"

            try:
                response = client.models.generate_content(
                    model=test_model,
                    contents=prompt,
                    config={"temperature": 0.7, "max_output_tokens": 100}
                )
                st.success(f"✅ 成功使用模型 {test_model} 生成文字")
                st.markdown(f"**生成結果：**\n\n{response.text}")
            except Exception as e:
                st.error("❌ 模型呼叫失敗")
                st.exception(e)

    except Exception as e:
        st.error("❌ API Key 無法使用或初始化失敗")
        st.exception(e)
