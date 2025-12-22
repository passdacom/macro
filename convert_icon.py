from PIL import Image
import os

try:
    img = Image.open("icon.png")
    img.save("icon.ico", format='ICO', sizes=[(256, 256)])
    print("Successfully converted icon.png to icon.ico")
except Exception as e:
    print(f"Error converting icon: {e}")
