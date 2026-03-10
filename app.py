import streamlit as st
import pandas as pd
import numpy as np
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource

# --- 1. 模擬數據 ---
def get_bokeh_data():
    df = pd.DataFrame({
        'date': pd.bdate_range(start='2024-01-01', periods=100),
        'close': (500 + np.random.randn(100).cumsum() * 5).round(1)
    })
    df['open'] = (df['close'] + np.random.uniform(-5, 5, 100)).round(1)
    df['high'] = df[['open', 'close']].max(axis=1) + 3
    df['low'] = df[['open', 'close']].min(axis=1) - 3
    df['color'] = ["#EB3B3B" if c >= o else "#26A69A" for o, c in zip(df['open'], df['close'])]
    return df

df = get_bokeh_data()

# --- 2. 建立 Bokeh 圖表 ---
# 關鍵：tools="" 移除所有工具，這樣使用者完全無法「拖動」或「拉出空白」
# x_range 鎖定在最後 30 筆
start_view = df['date'].iloc[-30]
end_view = df['date'].iloc[-1]

p = figure(x_axis_type="datetime", 
           height=500, 
           title="台股分析終端 (硬鎖定版)",
           x_range=(start_view, end_view), # 物理鎖定視窗
           tools="", # 清空所有工具，徹底防止拖曳出邊界
           toolbar_location=None,
           outline_line_color="#dfdfdf")

# 繪製 K 線
source = ColumnDataSource(df)
p.segment('date', 'high', 'date', 'low', color="black", source=source)
p.vbar('date', pd.Timedelta(hours=12), 'open', 'close', 
       fill_color='color', line_color="black", source=source)

# 加入滑鼠十字線與提示資訊 (Hover)
hover = HoverTool(tooltips=[
    ("日期", "@date{%F}"),
    ("開盤", "@open"),
    ("收盤", "@close"),
    ("最高", "@high"),
    ("最低", "@low")
], formatters={'@date': 'datetime'})
p.add_tools(hover)

# 優化視覺 (大戶投風格)
p.yaxis.fixed_location = 0 # 某些版本可用來固定 y 軸位置
p.grid.grid_line_alpha = 0.3
p.background_fill_color = "#ffffff"

# --- 3. 渲染 ---
st.title("🛡️ 物理邊界：Bokeh 鎖定版")
st.info("此版本已「物理封鎖」拖曳功能。圖表鎖定在最後 30 根 K 線，絕對拉不出空白。")
st.bokeh_chart(p, use_container_width=True)
