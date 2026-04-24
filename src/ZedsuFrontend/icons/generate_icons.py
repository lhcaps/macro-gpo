"""Generate 5 state-colored tray icons (16x16 + 32x32 PNG)."""
from PIL import Image, ImageDraw
import os

SIZE = 16
SIZE_32 = 32
STATES = {
    "idle":      (154, 167, 189),   # #9AA7BD
    "running":   (34,  197,  94),   # #22C55E
    "paused":    (59,  130, 246),   # #3B82F6
    "degraded":  (245, 158,  11),   # #F59E0B
    "error":     (239,  68,  68),   # #EF4444
}

icons_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(icons_dir, exist_ok=True)

for state, rgb in STATES.items():
    for size, suffix in [(SIZE, ""), (SIZE_32, "_32")]:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(1, size // 8)
        draw.ellipse(
            [margin, margin, size - margin - 1, size - margin - 1],
            fill=rgb + (255,)
        )
        path = os.path.join(icons_dir, f"tray_{state}{suffix}.png")
        img.save(path)
        print(f"Saved: {path} ({size}x{size})")

print("Done. 10 tray icon files generated.")
