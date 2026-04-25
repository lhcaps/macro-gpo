"""Generate app icons (icon.png, icon.ico) for Tauri build."""
from PIL import Image, ImageDraw
import os

icons_dir = os.path.dirname(os.path.abspath(__file__))

# Create a Zedsu-themed icon: dark background with a glowing "Z" mark
SIZES = [32, 128, 256, 512]

for size in SIZES:
    img = Image.new("RGBA", (size, size), (9, 11, 16, 255))
    draw = ImageDraw.Draw(img)

    # Background glow
    cx, cy = size // 2, size // 2
    r = size // 3
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(103, 232, 249, 40)  # accent color with alpha
    )

    # Main circle
    margin = size // 6
    draw.ellipse(
        [margin, margin, size - margin - 1, size - margin - 1],
        fill=(103, 232, 249, 255)  # #67E8F9
    )

    # Inner dot
    inner_r = size // 8
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r - 1, cy + inner_r - 1],
        fill=(9, 11, 16, 255)
    )

    path = os.path.join(icons_dir, f"icon_{size}.png")
    img.save(path, "PNG")
    print(f"Saved: {path}")

# Create main icon.png (256x256)
img_256 = Image.new("RGBA", (256, 256), (9, 11, 16, 255))
draw = ImageDraw.Draw(img_256)
cx, cy = 128, 128

# Outer glow
r = 90
draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(103, 232, 249, 30))

# Main circle
margin = 30
draw.ellipse([margin, margin, 256 - margin - 1, 256 - margin - 1], fill=(103, 232, 249, 255))

# Inner circle
inner_r = 32
draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r - 1, cy + inner_r - 1], fill=(9, 11, 16, 255))

img_256.save(os.path.join(icons_dir, "icon.png"), "PNG")
print(f"Saved: {icons_dir}/icon.png")

# Create ICO (multi-resolution)
ico_sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
ico_imgs = []
for w, h in ico_sizes:
    img = Image.new("RGBA", (w, h), (9, 11, 16, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2

    # Background glow
    r = max(1, w // 3)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(103, 232, 249, 30))

    # Main circle
    margin = max(2, w // 6)
    draw.ellipse([margin, margin, w - margin - 1, h - margin - 1], fill=(103, 232, 249, 255))

    # Inner dot
    inner_r = max(1, w // 8)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r - 1, cy + inner_r - 1], fill=(9, 11, 16, 255))

    ico_imgs.append(img)

ico_path = os.path.join(icons_dir, "icon.ico")
ico_imgs[0].save(ico_path, format="ICO", append_images=ico_imgs[1:], sizes=[(s[0], s[1]) for s in ico_sizes])
print(f"Saved: {ico_path}")
print("Done. App icons generated.")
