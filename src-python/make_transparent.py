import os
from PIL import Image, ImageDraw

def make_corners_transparent(image_path):
    print(f"Loading image for transparency conversion: {image_path}")
    if not os.path.exists(image_path):
        print(f"Error: {image_path} does not exist.")
        return False
        
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Flood fill from all 4 corners to clear any white padding outside the squircle
    for corner in [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]:
        r, g, b, a = img.getpixel(corner)
        # Check if the pixel is near-white
        if r > 240 and g > 240 and b > 240 and a > 0:
            ImageDraw.floodfill(img, corner, (0, 0, 0, 0), thresh=40)
            
    img.save(image_path, "PNG")
    print("Successfully converted corners to transparent.")
    return True

if __name__ == "__main__":
    icon_path = "/Users/ashishpaliwal/apps/ErgoLearn AI/src-frontend/app-icon.png"
    make_corners_transparent(icon_path)
