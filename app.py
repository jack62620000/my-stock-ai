# 請將 AI 區塊簡化成這樣，測試新 Key 是否通暢
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 這是目前全球通用的標準名稱
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("你好，請用五個字自我介紹。")
    st.info(response.text)
except Exception as e:
    st.error(f"連線細節：{str(e)}")
