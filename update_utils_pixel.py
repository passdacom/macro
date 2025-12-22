import sys

with open('c:/cli/macro2/event_utils.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Append pixel utils
new_lines = [
    "\n",
    "import ctypes\n",
    "\n",
    "def get_pixel_color(x, y):\n",
    "    hdc = ctypes.windll.user32.GetDC(0)\n",
    "    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)\n",
    "    ctypes.windll.user32.ReleaseDC(0, hdc)\n",
    "    # Color is BGR in Windows GDI\n",
    "    r = color & 0xFF\n",
    "    g = (color >> 8) & 0xFF\n",
    "    b = (color >> 16) & 0xFF\n",
    "    return (r, g, b)\n",
    "\n",
    "def rgb_to_hex(rgb):\n",
    "    return \"#{:02x}{:02x}{:02x}\".format(rgb[0], rgb[1], rgb[2])\n"
]
lines.extend(new_lines)

with open('c:/cli/macro2/event_utils.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
