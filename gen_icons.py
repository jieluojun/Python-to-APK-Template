"""
生成 LanPlay Monitor 的 Android 图标素材
- icon.png              主图标 1024x1024
- icon_foreground.png   自适应图标前景 108x108 (透明底)
- icon_background.png   自适应图标背景 108x108 (纯色)
- presplash.png         启动图 1080x1920

运行: python gen_icons.py
依赖: pip install Pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ===== 配色 =====
BG_COLOR      = "#1a1a2e"   # 深蓝黑
ACCENT        = "#4fc3f7"   # 亮蓝
ACCENT_DARK   = "#0277bd"   # 深蓝
TEXT_COLOR    = "#e0e0e0"   # 浅灰白
SHADOW        = "#0d47a1"   # 阴影蓝

def make_round_rect_bg(size, color, radius=24):
    """圆角矩形背景"""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size[0]-1, size[1]-1], radius=radius, fill=color)
    return img

def draw_wifi_icon(draw, cx, cy, size, color):
    """画一个简单的 WiFi / 信号图标(用同心弧线)"""
    # 弧线从大到小
    radii = [size*0.48, size*0.36, size*0.24, size*0.12]
    widths = [size//16, size//16, size//16, size//20]
    for r, w in zip(radii, widths):
        bbox = [cx-r, cy-r*1.15, cx+r, cy+r*1.15]
        # 只画上半圆
        draw.arc(bbox, start=210, end=330, fill=color, width=w)
    # 中心点
    dot_r = size * 0.06
    draw.ellipse([cx-dot_r, cy-dot_r*1.15, cx+dot_r, cy+dot_r*1.15], fill=color)

def make_icon_1024():
    """主图标 1024x1024"""
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角背景
    bg = make_round_rect_bg((size, size), BG_COLOR, radius=200)
    img.paste(bg, (0, 0), bg)

    # WiFi 图标居中偏上
    draw_wifi_icon(draw, size//2, int(size*0.42), size//2, ACCENT)

    # 底部文字 "LP"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size//5)
    except:
        font = ImageFont.load_default()
    text = "LP"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    tx = (size - tw) // 2
    ty = int(size * 0.62)
    # 阴影
    draw.text((tx+3, ty+3), text, fill=SHADOW, font=font)
    draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

    img.save(os.path.join(OUT, "icon.png"), "PNG")
    print(f"✅ icon.png ({size}x{size})")

def make_adaptive_foreground():
    """自适应图标前景 108x108dp(实际 432x432 px @4x)"""
    dp = 108
    px = dp * 4  # 432
    safe = int(px * 0.66)  # 安全区 ~72dp

    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # WiFi 图标在安全区内居中
    draw_wifi_icon(draw, px//2, px//2 - int(px*0.08), safe, ACCENT)

    # 底部小文字
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", px//8)
    except:
        font = ImageFont.load_default()
    text = "LP"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    tx = (px - tw) // 2
    ty = int(px * 0.62)
    draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

    img.save(os.path.join(OUT, "icon_foreground.png"), "PNG")
    print(f"✅ icon_foreground.png ({px}x{px})")

def make_adaptive_background():
    """自适应图标背景 108x108dp @4x = 432x432"""
    dp = 108
    px = dp * 4
    img = Image.new("RGBA", (px, px), BG_COLOR)
    # 加个径向渐变效果(中心稍亮)
    from PIL import ImageFilter
    overlay = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    center = px // 2
    for i in range(60):
        alpha = max(0, 40 - i)
        r = center - i * 3
        odraw.ellipse([center-r, center-r, center+r, center+r],
                      fill=(255, 255, 255, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    img.save(os.path.join(OUT, "icon_background.png"), "PNG")
    print(f"✅ icon_background.png ({px}x{px})")

def make_presplash():
    """启动图 1080x1920"""
    w, h = 1080, 1920
    img = Image.new("RGBA", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 中心 WiFi 图标
    cx, cy = w//2, h//2 - 80
    draw_wifi_icon(draw, cx, cy, 400, ACCENT)

    # 标题
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    except:
        font = ImageFont.load_default()
    text = "LanPlay Monitor"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (w - tw) // 2
    ty = cy + 280
    draw.text((tx+2, ty+2), text, fill=SHADOW, font=font)
    draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

    # 副标题
    try:
        font2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        font2 = ImageFont.load_default()
    sub = "Loading..."
    bbox2 = draw.textbbox((0, 0), sub, font=font2)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((w - tw2)//2, ty + 100), sub, fill=ACCENT, font=font2)

    img.save(os.path.join(OUT, "presplash.png"), "PNG")
    print(f"✅ presplash.png ({w}x{h})")

if __name__ == "__main__":
    make_icon_1024()
    make_adaptive_foreground()
    make_adaptive_background()
    make_presplash()
    print("\n🎉 所有图标素材生成完毕，放在项目根目录即可。")
