# --- 第三部分：Gemini AI 專家點評 (穩定免費版) ---
        st.divider()
        st.subheader("🤖 Gemini AI 專家點評")
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                genai.configure(api_key=api_key.strip())
                
                # 直接指定免費額度最高的 1.5-flash
                # 如果還是報 429，代表妳的 Google 帳號需要等待約 30 分鐘讓額度生效
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"妳是專業分析師。分析台股{d['name']}({code_input})，目前價格{d['p']}，請給出20字建議。"
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.info(response.text)
                else:
                    st.warning("AI 暫時沒有回傳文字，請稍後再試。")
                    
            except Exception as error:
                err_str = str(error)
                if "429" in err_str:
                    st.error("⚠️ 免費額度已達上限或帳號尚未開通。請等待 1 分鐘後再重新整理網頁。")
                else:
                    st.error(f"連線細節：{err_str[:100]}")
        else:
            st.error("🔑 尚未在 Secrets 中設定 GEMINI_API_KEY")
