import yfinance as yf
import gspread
import time
import pandas as pd
from google.colab import auth
from google.auth import default

# 1. 認證與連接
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

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

# --- 基礎資料準備 ---
db_data = ws_db.get_all_values()
stock_db = {str(row[0]).strip(): (row[1], row[2]) for row in db_data[1:] if len(row) >= 3}

# ==========================================
# 階段 1：【台股分析】(T 欄全方位洞察升級版)
# ==========================================
main_codes = ws_main.col_values(1)[4:] 
print("🚀 啟動階段 1/2：台股分析 (基本面 + 深度洞察)...")

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
        
        # --- 數據採集 ---
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0) or 0
        debt_ratio = (info.get('debtToEquity', 0) or 0) / 100
        fcf_raw = info.get('freeCashflow', 0) or 0
        qr_raw = info.get('quickRatio') or 0
        cr_raw = info.get('currentRatio') or 0
        eps = info.get('trailingEps', 0)
        rev_growth = info.get('revenueGrowth', 0) or 0
        div_yield = info.get('dividendYield', 0) or 0
        
        # PE 與 52週位階
        raw_market_pe = info.get('trailingPE')
        sector_type, pe_bench = get_sector_pe(official_ind)
        market_pe_display = round(raw_market_pe, 2) if (raw_market_pe and raw_market_pe < 500) else "過高(失真)"
        
        intrinsic = round(eps * pe_bench, 2)
        safety_val = (intrinsic / price) - 1 if price > 0 else 0
        pos_52 = (price - info.get('fiftyTwoWeekLow', 0)) / (info.get('fiftyTwoWeekHigh', 1) - info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekHigh', 0) > 0 else 0.5

        # --- S 欄：五星評等邏輯 ---
        if roe > 0.18 and pos_52 < 0.35 and fcf_raw > 0: rating = "🌟 積極布局"
        elif safety_val > 0.1: rating = "🟢 分批買進"
        elif roe > 0.12 and pos_52 < 0.6: rating = "🟡 持有觀望"
        elif pos_52 > 0.8 or roe < 0.08: rating = "🟠 縮減倉位"
        else: rating = "🚫 暫不考慮"

        # --- 🏆 核心升級：T 欄全方位決策洞察 (多因子聯動) ---
        is_excellent = (roe > 0.18 and fcf_raw > 0 and debt_ratio < 0.5)
        is_cheap = (safety_val > 0.15)
        is_expensive = (safety_val < -0.15)
        is_low_pos = (pos_52 < 0.35)
        
        if is_excellent and is_cheap:
            insight = f"💎【極致價值】體質卓越且定價低估(空間{round(safety_val*100)}%)。此標的具複利成長基因，低位階提供極高安全邊際，為核心首選。"
        elif is_excellent and is_expensive:
            insight = f"📈【優質溢價】績優標的但目前預期透支。雖然ROE亮眼，但高溢價抵銷回報，建議「持股續抱、不加新倉」，靜待回檔合理區。"
        elif not is_excellent and is_cheap and is_low_pos:
            insight = f"🩹【低位修復】體質平庸但股價超跌，具{round(safety_val*100)}%估值修復空間。適合以技術面介入賺取短線反彈，不宜長期重倉。"
        elif fcf_raw <= 0 and is_expensive:
            insight = "🚨【高度警戒】盈餘品質差(現金流負)且股價嚴重過熱。屬題材投機階段，隨時有崩盤回補缺口風險，應逢高減碼、入袋為安。"
        elif div_yield > 0.05 and debt_ratio < 0.4:
            insight = f"💰【防禦收息】高殖利率({round(div_yield*100,1)}%)搭配健康財務，屬波動時期避風港。定價合理，適合長期穩健存股配置。"
        elif rev_growth > 0.2 and roe > 0.12:
            insight = "🚀【成長動能】營收爆發帶動獲利擴張。雖估值不便宜，但動能強勁。應聚焦後續成長延續性，並依技術面找尋攻擊買點。"
        else:
            insight = "⏳【中性觀望】各項財務與估值數據皆處於中庸地帶，市場缺乏明顯驅動力量。建議保留現金彈性，等待下一季財報變數釐清。"

        # --- 數據裝箱 (B 到 T 欄) ---
        row_data = [[
            db_name if db_name else info.get('shortName', '未知'), # B
            price, # C
            f"{round(roe*100, 2)}%", # D
            f"{round(info.get('grossMargins', 0)*100, 2)}%", # E
            f"{round(info.get('operatingMargins', 0)*100, 2)}%", # F
            f"{round(debt_ratio*100, 2)}%", # G
            market_pe_display, # H
            pe_bench, # I
            f"{round(pos_52 * 100, 1)}%", # J
            eps, # K
            intrinsic, # L
            f"{round(fcf_raw / 100000000, 2)} 億", # M
            f"{round(qr_raw * 100, 2)}%" if qr_raw else "－", # N
            f"{round(cr_raw * 100, 2)}%" if cr_raw else "－", # O
            f"{round(info.get('dividendYield', 0)*100, 2)}%", # P
            f"{round(rev_growth*100, 2)}%", # Q
            f"{round(safety_val * 100, 2)}%", # R
            rating, # S
            insight # T: 合併後的深度洞察
        ]]
        
        ws_main.update(range_name=f"B{row_idx}:T{row_idx}", values=row_data, value_input_option='USER_ENTERED')
        print(f"✅ 台股分析: {code} 深度洞察更新完成")
        
    except Exception as e:
        print(f"❌ 台股分析: {code} 錯誤: {e}")
    time.sleep(1.2)

# ==========================================
# 階段 2：【股價走勢分析】(新增技術、籌碼、振幅)
# ==========================================
trend_codes = ws_trend.col_values(1)[4:] 
print("\n📈 啟動階段 2/2：股價走勢分析 (技術/籌碼)...")

for i, code in enumerate(trend_codes):
    row_idx = i + 5
    code = str(code).strip()
    if not code: continue
    
    try:
        stock = yf.Ticker(f"{code}.TW")
        df = stock.history(period="120d")
        if df.empty:
            stock = yf.Ticker(f"{code}.TWO")
            df = stock.history(period="120d")
        
        info = stock.info
        cur_p = df['Close'].iloc[-1]
        
        # 1. 均線與乖離 (G 欄)
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma60 = df['Close'].rolling(60).mean().iloc[-1]
        bias = (cur_p - ma20) / ma20

        # 2. 量能與均量變化 (O, P, Q 欄)
        vol_today = df['Volume'].iloc[-1] / 1000
        avg_vol_5 = df['Volume'].rolling(5).mean().iloc[-1] / 1000
        prev_avg_vol_5 = df['Volume'].rolling(5).mean().iloc[-2] / 1000
        vol_change = avg_vol_5 - prev_avg_vol_5 # 五日均張變化
        vol_ratio = vol_today / avg_vol_5 if avg_vol_5 > 0 else 1 # 量能噴發比

        # 3. 股價振幅 (R 欄)
        amp = (df['High'].iloc[-1] - df['Low'].iloc[-1]) / df['Close'].iloc[-2]

        # 4. 技術指標 (RSI, KD, MACD)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = 100 - (100 / (1 + (gain / loss).iloc[-1]))
        
        low_9, high_9 = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
        rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
        k_val = rsv.ewm(com=2).mean().iloc[-1]
        d_val = pd.Series(rsv.ewm(com=2).mean()).ewm(com=2).mean().iloc[-1]
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd_hist = (ema12 - ema26 - (ema12 - ema26).ewm(span=9, adjust=False).mean()).iloc[-1]

        # 5. 布林通道 (S, T 欄)
        std20 = df['Close'].rolling(20).std().iloc[-1]
        up_b, lo_b = ma20 + (std20 * 2), ma20 - (std20 * 2)

        # 6. 診斷與策略
        diag = []
        if vol_ratio > 2: diag.append("量能爆發")
        if amp > 0.05: diag.append("震幅放大")
        if k_val > d_val and rsv.iloc[-2] <= k_val: diag.append("KD金叉")
        
        strategy = "✅ 趨勢偏多，持股續抱" if cur_p > ma20 else "⏳ 盤整觀察"
        if vol_ratio > 1.8 and k_val < 50 and k_val > d_val: strategy = "🚀 轉強訊號，分批試單"

        # --- 數據裝箱 (B 到 W 欄) ---
        trend_row = [[
            stock_db.get(code, (None, ""))[0], # B
            round(cur_p, 2), # C
            round(ma5, 2), round(ma20, 2), round(ma60, 2), # D, E, F
            round(bias, 4), # G (顯示百分比)
            int(vol_today), # H
            "放量" if vol_ratio > 1.2 else "縮量", # I
            round(rsi_val, 2), # J
            round(k_val, 2), round(d_val, 2), # K, L
            round(macd_hist, 2), # M
            round(info.get('heldPercentInstitutions', 0), 4), # N: 機構持股
            round(vol_change, 1), # O: 均量變化 (純數字)
            int(avg_vol_5), # P: 5日均量
            round(vol_ratio, 2), # Q: 噴發比
            round(amp, 4), # R: 振幅
            round(up_b, 2), round(lo_b, 2), # S, T
            "🌕強勢" if cur_p > ma20 else "🌑弱勢", # U
            "；".join(diag) if diag else "趨勢運行中", # V
            strategy # W
        ]]
        ws_trend.update(range_name=f"B{row_idx}:W{row_idx}", values=trend_row, value_input_option='USER_ENTERED')
        print(f"✅ 走勢分析: {code} 更新成功")
    except Exception as e:
        print(f"❌ 走勢分析: {code} 錯誤: {e}")
    time.sleep(1)

print("\n🎉 所有工作表更新完畢！")
