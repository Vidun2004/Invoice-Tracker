"""Generate app icon (receipt + check) as PNG + ICO. Run once, committed to assets/."""
from PIL import Image, ImageDraw

SIZE = 256
BG = (17, 28, 51, 255)       # ink navy
ACCENT = (37, 99, 235, 255)  # brand blue
PAPER = (255, 255, 255, 255)
GREEN = (22, 163, 74, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, fill=BG)
# receipt
d.rounded_rectangle([78, 40, 178, 200], radius=10, fill=PAPER)
d.line([96, 78, 160, 78], fill=(203, 213, 225, 255), width=6)
d.line([96, 102, 160, 102], fill=(203, 213, 225, 255), width=6)
d.line([96, 126, 140, 126], fill=(203, 213, 225, 255), width=6)
d.line([78, 40, 178, 40, 178, 62, 78, 62], fill=ACCENT)
# check badge
d.ellipse([140, 150, 216, 226], fill=GREEN, outline=(255, 255, 255, 255), width=6)
d.line([156, 188, 172, 204], fill=(255, 255, 255, 255), width=10, joint="curve")
d.line([172, 204, 200, 168], fill=(255, 255, 255, 255), width=10, joint="curve")

img.save("assets/icon.png")
img.save("assets/icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon OK -> assets/icon.png + assets/icon.ico")
