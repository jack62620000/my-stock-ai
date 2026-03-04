import yfinance as yf
import gspread
import time
import pandas as pd
import google.generativeai as genai  # 導入 Gemini
from google.colab import auth
from google.auth import default
from google.colab import userdata # 建議將 Key 存在 Colab 左側的小鑰匙 (Secrets)

# ==========================================
# 0. 環境設定與 Gemini 配置
# ==========================================
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

# 請確保妳已在 Colab 的 Secrets (左側鑰匙圖標) 設定 GEMINI_API_KEY
try:
    API_KEY = userdata.get('GEMINI_API_KEY')
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    print("⚠️ 未偵測到 Secrets 中的 API Key，請手動輸入或檢查設定")

# 開啟試算表
sh = gc.open("Buffett_Stock_Valuation_Table")
ws_main = sh.worksheet("台股分析")
ws_trend = sh.worksheet("股價走勢分析")
ws_db = sh.worksheet("代碼對照表")

def get_sector_pe(official_ind):
    ind_str = str(official_ind)
    if any(k in ind_str for k in ["半導體", "IC設計"]): return "科技權值", 25
    if any(k in ind_str for k in ["電腦", "電子", "通訊", "伺服器", "散熱"]): return "AI硬體", 20
    if "金融" in ind_str: return "金融產業", 14
    if any(k in ind_str for k in ["鋼鐵", "塑膠", "水泥", "航運"]): return "週期傳產", 10
    return "一般類股", 15

# AI 分析函式
def get_ai_analysis(data_dict, analysis_type="fundamental"):
    try:
        if analysis_type == "fundamental":
            prompt = f"""妳是資深台股分析師。請根據以下數據對 {data_dict['name']}({data_dict['code']}) 進行 40 字內深度點評：
            股價:{data_dict['price']}, ROE:{data_dict['roe']}, 安全邊際:{data_dict['safety']}, 自由現金流:{data_dict['fcf']}。
            請給出具體且毒辣的投資建議。"""
        else:
            prompt = f"""妳是技術面專家。分析 {data_dict['name']} 走勢：
            目前價:{data_dict['price']}, KD:{data_dict['k']}/{data_dict['d']}, RSI:{data_dict['rsi']}, 噴發比:{data_dict['vol_ratio']}。
            請用 30 字分析目前動能並給出策略。"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "AI 分析暫時離線"

# --- 基礎資料準備 ---
db_data = ws_db.get_all_values()
stock_db = {str(row[0]).strip(): (row[1], row[2]) for row in db_data[1:] if len(row) >= 3}

# ==========================================
# 階段 1：【台股分析】 (整合 Gemini)
# ==========================================
main_codes = ws_main.col_values(1)[4:] 
print("🚀 啟動階段 1/2：台股分析 (基本面 + Gemini AI)...")

for i, code in enumerate(main_codes):
    row_idx = i + 5 
    code = str(code).strip()
    if not code: continue
    
    db_name, official_ind = stock_db.get(code, (None, "一般類股"))
    try:
        stock = yf.Ticker(f"{code}.TW")
        info = stock.info
        if not info.get('currentPrice'): 
            stock = yf.Ticker(f"{code}.TWO")
            info = stock.info
        
        # 數據採集
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0) or 0
        eps = info.get('trailingEps', 0)
        fcf_raw = info.get('freeCashflow', 0) or 0
        safety_val = ((eps * get_sector_pe(official_ind)[1]) / price) - 1 if price > 0 else 0
        
        # 呼叫 Gemini AI
        ai_data = {
            "name": db_name or info.get('shortName'),
            "code": code,
            "price": price,
            "roe": f"{round(roe*100,2)}%",
            "safety": f"{round(safety_val*100,2)}%",
            "fcf": f"{round(fcf_raw/100000000, 2)}億"
        }
        insight = get_ai_analysis(ai_data, "fundamental")

        # 寫入 T 欄 (此處簡化寫入邏輯，保留妳原本的所有欄位)
        # 註：妳原本的 row_data 包含 B-S 欄，這裡僅示範 T 欄替換為 AI
        # ... (此處省略中間 B-S 的運算，維持妳原本的邏輯) ...
        # [將妳原本的 row_data 最後一項替換為 insight]
        
        # 快速更新示範 (更新 T 欄)
        ws_main.update(range_name=f"T{row_idx}", values=[[insight]])
        print(f"✅ 台股分析: {code} AI 點評更新成功")
        
    except Exception as e:
        print(f"❌ 台股分析: {code} 錯誤: {e}")
    time.sleep(1.5) # 避開 AI 與 Yahoo 頻率限制

# ==========================================
# 階段 2：【股價走勢分析】 (整合 Gemini)
# ==========================================
trend_codes = ws_trend.col_values(1)[4:] 
print("\n📈 啟動階段 2/2：股價走勢分析 (技術面 + Gemini AI)...")

for i, code in enumerate(trend_codes):
    row_idx = i + 5
    code = str(code).strip()
    if not code: continue
    
    try:
        stock = yf.Ticker(f"{code}.TW")
        df = stock.history(period="60d") # 縮短天數加快速度
        if df.empty:
            stock = yf.Ticker(f"{code}.TWO")
            df = stock.history(period="60d")
        
        cur_p = df['Close'].iloc[-1]
        # (這裡省略妳原本的 KD, RSI 複雜運算公式，維持妳原本的邏輯)
        # 假設妳已經算出 rsi_val, k_val, d_val, vol_ratio...
        
        # 呼叫 Gemini AI (針對技術面)
        tech_data = {
            "name": code,
            "price": cur_p,
            "rsi": 50, # 替換為妳算出的變數
            "k": 60,   # 替換為妳算出的變數
            "d": 40,   # 替換為妳算出的變數
            "vol_ratio": 1.5 # 替換為妳算出的變數
        }
        ai_strategy = get_ai_analysis(tech_data, "technical")
        
        # 更新 W 欄為 AI 建議
        ws_trend.update(range_name=f"W{row_idx}", values=[[ai_strategy]])
        print(f"✅ 走勢分析: {code} AI 策略更新成功")
        
    except Exception as e:
        print(f"❌ 走勢分析: {code} 錯誤: {e}")
    time.sleep(1.5)

print("\n🎉 全自動 AI 投資報表更新完畢！")
