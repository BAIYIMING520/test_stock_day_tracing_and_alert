#!/usr/bin/env python3
"""生成Quote/0设备的小字体图片"""

from PIL import Image, ImageDraw, ImageFont
import sys

# Quote/0 屏幕分辨率
WIDTH = 296
HEIGHT = 152

def create_stock_image(stocks_data):
    """创建股票图片
    
    stocks_data: [{"code": "002050", "name": "三花", "price": 48.78, "pct": 2.01, "yesterday": 47.82}, ...]
    """
    img = Image.new('1', (WIDTH, HEIGHT), 1)  # 白色背景
    draw = ImageDraw.Draw(img)
    
    # 尝试使用中文字体
    font_loaded = False
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansMonoCJKsc-Regular.otf", 10)
        font_small = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansMonoCJKsc-Regular.otf", 9)
        font_loaded = True
    except Exception as e:
        print(f"加载OTF字体失败: {e}")
    
    if not font_loaded:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansMonoCJKsc-Regular.ttf", 10)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansMonoCJKsc-Regular.ttf", 9)
            font_loaded = True
        except Exception as e:
            print(f"加载TTF字体失败: {e}")
    
    if not font_loaded:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        print("使用默认字体")
    
    y = 5
    for i, stock in enumerate(stocks_data):
        if y > HEIGHT - 20:
            break
        
        code = stock.get('code', '')
        name = stock.get('name', '')[:4]  # 限制名称长度
        price = stock.get('price', 0)
        pct = stock.get('pct', 0)
        yesterday = stock.get('yesterday', 0)
        
        # 颜色：涨为红(0)，跌为黑(1)
        color = 0 if pct >= 0 else 1
        
        # 第一行：代码+名称
        text1 = f"{code} {name}"
        draw.text((5, y), text1, fill=color, font=font_small)
        
        # 第二行：价格+涨跌幅
        pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        text2 = f"¥{price:.2f} {pct_str} 昨{yesterday:.2f}"
        draw.text((5, y + 12), text2, fill=color, font=font_small)
        
        y += 28
    
    return img

def save_image(filename="stock_card.png"):
    # 测试数据
    stocks = [
        {"code": "002050", "name": "三花智控", "price": 48.78, "pct": 2.01, "yesterday": 47.82},
        {"code": "300308", "name": "中际旭创", "price": 534.8, "pct": -4.19, "yesterday": 558.2},
        {"code": "002281", "name": "光迅科技", "price": 98.82, "pct": 4.82, "yesterday": 94.28},
    ]
    
    img = create_stock_image(stocks)
    img.save(filename, "PNG")
    print(f"图片已保存: {filename}")
    return filename

if __name__ == "__main__":
    save_image()
