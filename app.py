if data:
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                try:
                    genai.configure(api_key=api_key.strip())
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 這是餵給 AI 的秘密指令
                    prompt = f"你是台股分析師。分析{data['name']}({code})，現價{data['price']}元，ROE為{round(data['roe']*100,2)}%。請給出一段40字內的投資診斷建議。"
                    
                    response = model.generate_content(prompt)
                    
                    # 顯示結果
                    st.success(f"### 📋 {data['name']} ({code}) 診斷結果")
                    st.info(response.text)
                    
                except Exception as e:
                    # 改成這樣，我們就能看到真正的錯誤原因
                    st.error(f"⚠️ AI 連線細節：{str(e)}")
            else:
                st.error("🔑 請在 Streamlit Cloud 的 Settings > Secrets 設定 GEMINI_API_KEY")
